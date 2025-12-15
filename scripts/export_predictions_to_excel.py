#!/usr/bin/env python3
"""
Export Model vs Market Odds to Excel

Minimal pipeline:
- You maintain an Excel sheet of upcoming fights + odds.
- This script adds model probabilities, implied probabilities, and simple edges,
  and writes out a new Excel file you can use for betting decisions.

Input template (Excel or CSV):
    data/predictions/upcoming_fights.xlsx

Required columns:
    - event              (str)  e.g. "UFC 320"
    - fight_date         (str)  optional, free-form date
    - fighter_1_name     (str)  e.g. "Edson Barboza"
    - fighter_2_name     (str)  e.g. "Jalin Turner"
    - fighter_1_odds     (int)  American odds, e.g. +200, -150
    - fighter_2_odds     (int)
    - is_title_fight     (bool/int, optional)  1 if 5-round title fight

Output:
    An Excel file with the same rows plus:
        - model_p_f1, model_p_f2
        - implied_p_f1, implied_p_f2
        - edge_f1, edge_f2
        - ev_f1, ev_f2                (expected value per $1 stake)
        - recommended_bet             ("fighter_1", "fighter_2", "none")
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Tuple, Optional

import pandas as pd
from loguru import logger

from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.matchup_features import MatchupFeatureExtractor
from features.feature_pipeline import FeaturePipeline
from models.xgboost_model import XGBoostModel


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability (without vig adjustment)."""
    if odds is None:
        return 0.0
    try:
        odds = int(odds)
    except (TypeError, ValueError):
        return 0.0

    if odds < 0:
        return (-odds) / ((-odds) + 100)
    else:
        return 100 / (odds + 100)


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds is None:
        return 0.0
    odds = int(odds)
    if odds < 0:
        return 1.0 + (100.0 / abs(odds))
    else:
        return 1.0 + (odds / 100.0)


def expected_value_per_dollar(prob: float, odds: int) -> float:
    """
    Expected value per $1 bet given model probability and American odds.

    EV = p * (decimal_odds - 1) - (1 - p)
    """
    if odds is None:
        return 0.0
    dec = american_to_decimal(odds)
    edge = prob * (dec - 1.0) - (1.0 - prob)
    return float(edge)


def load_input(path: Path) -> pd.DataFrame:
    """Load Excel or CSV with upcoming fights + odds."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    return df


def resolve_fighter(session, name: str) -> Fighter:
    """Simple name lookup with ILIKE match."""
    fighter = (
        session.query(Fighter)
        .filter(Fighter.name.ilike(f"%{name}%"))
        .first()
    )
    if not fighter:
        raise ValueError(f"Fighter not found in DB: {name}")
    return fighter


def _detect_risk_notes(
    features: dict,
    side: Optional[str],
    f1_name: str,
    f2_name: str,
) -> str:
    """
    Detect high-level risk patterns that should trigger a "no bet" recommendation
    even when the raw edge is positive.

    Initial rules (can be extended later):
      - If the would-be bet side has:
          * no wins in their last 3 fights (with at least 3 total fights), AND
          * no win in the last 2+ years,
        AND their opponent profiles as a heavy KO finisher,
        then flag this as a "NO BET" with an explanatory note.
      - If the opponent appears to be a debutant / very low-sample fighter
        (no fight history or very few total fights), flag as "NO BET" due to
        high uncertainty and limited data.
    """
    if side not in ("fighter_1", "fighter_2"):
        return ""

    if side == "fighter_1":
        pfx = "f1_"
        opp_pfx = "f2_"
        name_side = f1_name
        name_opp = f2_name
    else:
        pfx = "f2_"
        opp_pfx = "f1_"
        name_side = f2_name
        name_opp = f1_name

    total_fights = int(features.get(f"{pfx}total_fights", 0) or 0)
    win_rate_last_3 = float(features.get(f"{pfx}win_rate_last_3", 0.0) or 0.0)
    years_since_last_win = float(features.get(f"{pfx}years_since_last_win", 0.0) or 0.0)

    # Slump conditions for the would-be bet side
    no_wins_last_3 = total_fights >= 3 and win_rate_last_3 == 0.0
    no_win_2plus_years = years_since_last_win >= 2.0

    # Opponent KO / early-finish profile
    opp_ko_rate = float(features.get(f"{opp_pfx}ko_rate", 0.0) or 0.0)
    opp_first_round_ko_rate = float(features.get(f"{opp_pfx}first_round_ko_rate", 0.0) or 0.0)
    opp_early_finish_rate_last_3 = float(features.get(f"{opp_pfx}early_finish_rate_last_3", 0.0) or 0.0)

    # Heuristic: heavy KO/finisher if any of these are large.
    opp_power = max(opp_ko_rate, opp_first_round_ko_rate, opp_early_finish_rate_last_3)
    heavy_ko = opp_power >= 0.4

    # 1) Aging/slumping fighter vs heavy KO opponent (Cejudo-style case)
    if no_wins_last_3 and no_win_2plus_years and heavy_ko:
        return (
            f"NO BET: {name_side} has not won in the last 3 fights and over 2 years, "
            f"while opponent {name_opp} profiles as a heavy KO finisher."
        )

    # 2) Avoid betting AGAINST a clear heavy KO finisher when they have much more power
    side_ko_rate = float(features.get(f"{pfx}ko_rate", 0.0) or 0.0)
    side_first_round_ko_rate = float(features.get(f"{pfx}first_round_ko_rate", 0.0) or 0.0)
    side_early_finish_rate_last_3 = float(features.get(f"{pfx}early_finish_rate_last_3", 0.0) or 0.0)
    side_power = max(side_ko_rate, side_first_round_ko_rate, side_early_finish_rate_last_3)

    # If opponent has clearly higher KO/early-finish power, don't fade them blindly.
    if heavy_ko and (opp_power - side_power) >= 0.2:
        return (
            f"NO BET: Opponent {name_opp} has significantly higher KO/early-finish power "
            f"than {name_side}. Avoid betting against a proven heavy finisher in this spot."
        )

    # 3) Debut / very low-sample opponent: avoid overconfident bets against unknowns.
    opp_total_fights = int(features.get(f"{opp_pfx}total_fights", 0) or 0)
    opp_has_history = int(features.get(f"{opp_pfx}has_fight_history", 0) or 0)
    if opp_has_history == 0 or opp_total_fights < 3:
        return (
            f"NO BET: Opponent {name_opp} has very limited or no recorded fight history "
            f"(debut / low sample size). Avoid high-confidence bets in this matchup."
        )

    return ""

def dump_feature_names(prefix, feature_vector):
    sorted_names = sorted(feature_vector.keys())
    print(f"\n[{prefix}] Feature count: {len(sorted_names)}")
    for name in sorted_names:
        print(name)
    print("\n")


def add_model_predictions(df: pd.DataFrame, model_name: str = "xgboost_model") -> pd.DataFrame:
    """
    For each row in the input DataFrame, add model probabilities and edges
    vs. the provided American odds.
    
    Args:
        df: DataFrame with upcoming fights and odds
        model_name: Name of the model to use (default: "xgboost_model")
    """
    # Load model + feature pipeline once
    logger.info(f"Loading XGBoost model '{model_name}' and feature pipeline...")
    xgb_model = XGBoostModel()
    xgb_model.load_model(model_name)

    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline(model_name=model_name)

    # DB + feature extractor
    db = DatabaseManager()
    session = db.get_session()
    matchup_extractor = MatchupFeatureExtractor(session)

    results = []

    required_cols = [
        "event",
        "fighter_1_name",
        "fighter_2_name",
        "fighter_1_odds",
        "fighter_2_odds",
    ]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column in input: '{col}'")

    for idx, row in df.iterrows():
        try:
            event = row.get("event", "")
            fight_date = row.get("fight_date", "")
            f1_name = str(row["fighter_1_name"]).strip()
            f2_name = str(row["fighter_2_name"]).strip()
            f1_odds = int(row["fighter_1_odds"])
            f2_odds = int(row["fighter_2_odds"])
            is_title = bool(row.get("is_title_fight", False))

            # Resolve fighters
            f1 = resolve_fighter(session, f1_name)
            f2 = resolve_fighter(session, f2_name)

            # Build features
            # NOTE: as_of_date=None (default) uses ALL available data up to today.
            # This is correct for upcoming predictions. Point-in-time filtering
            # (as_of_date != None) is only used for historical training data.
            features = matchup_extractor.extract_matchup_features(f1.id, f2.id)
            features["is_title_fight"] = 1 if is_title else 0

            X_df = pd.DataFrame([features])
            X_scaled, _ = pipeline.prepare_features(X_df, fit_scaler=False)
            
            proba = xgb_model.predict(X_scaled, use_calibrated=False)
            p_f1 = float(proba[0])
            p_f2 = 1.0 - p_f1

            # Implied probs from market odds
            imp_f1 = american_to_implied_prob(f1_odds)
            imp_f2 = american_to_implied_prob(f2_odds)

            # Edges (model vs market)
            edge_f1 = p_f1 - imp_f1
            edge_f2 = p_f2 - imp_f2

            # EV per $1
            ev_f1 = expected_value_per_dollar(p_f1, f1_odds)
            ev_f2 = expected_value_per_dollar(p_f2, f2_odds)

            # Rounded versions (nicer to read in Excel)
            p_f1_r = round(p_f1, 4)
            p_f2_r = round(p_f2, 4)
            imp_f1_r = round(imp_f1, 4)
            imp_f2_r = round(imp_f2, 4)
            edge_f1_r = round(edge_f1, 4)
            edge_f2_r = round(edge_f2, 4)
            ev_f1_r = round(ev_f1, 4)
            ev_f2_r = round(ev_f2, 4)

            # Percentage view (for quick eyeballing in Excel)
            p_f1_pct = round(p_f1 * 100.0, 1)
            p_f2_pct = round(p_f2 * 100.0, 1)
            imp_f1_pct = round(imp_f1 * 100.0, 1)
            imp_f2_pct = round(imp_f2 * 100.0, 1)
            edge_f1_pct = round(edge_f1 * 100.0, 1)
            edge_f2_pct = round(edge_f2 * 100.0, 1)

            # Simple recommended bet rule (can tweak later)
            threshold = 0.05  # 5% edge
            side = None
            if edge_f1 >= threshold and ev_f1 > 0:
                side = "fighter_1"
            elif edge_f2 >= threshold and ev_f2 > 0:
                side = "fighter_2"

            # Determine favourite by market / model, using actual names
            if imp_f1_r > imp_f2_r:
                market_fav = f1.name
            elif imp_f2_r > imp_f1_r:
                market_fav = f2.name
            else:
                market_fav = "even"

            if p_f1_r > p_f2_r:
                model_fav = f1.name
            elif p_f2_r > p_f1_r:
                model_fav = f2.name
            else:
                model_fav = "even"

            # Decide bet amount using 1/2 Kelly on a notional $10k bankroll
            bet_amount = 0
            profit_if_win = 0.0
            payout_if_win = 0.0
            recommended_label = "none"

            def kelly_fraction(prob: float, odds: int) -> float:
                """
                Standard Kelly fraction for a single outcome, returning the
                optimal fraction of bankroll to bet. We then use 1/2 Kelly.
                """
                dec = american_to_decimal(odds)
                b = dec - 1.0
                p = prob
                q = 1.0 - p
                k = (b * p - q) / b
                return max(k, 0.0)

            # Determine which side (if any) has sufficient edge and apply risk notes
            risk_notes = ""
            edge_pct_side = 0.0
            prob_side = 0.0
            name_side = ""

            if side == "fighter_1":
                edge_pct_side = edge_f1_pct
                prob_side = p_f1
                name_side = f1.name
            elif side == "fighter_2":
                edge_pct_side = edge_f2_pct
                prob_side = p_f2
                name_side = f2.name

            # Compute risk notes if there's a candidate side
            if side is not None:
                risk_notes = _detect_risk_notes(features, side, f1.name, f2.name)

            # Only size a bet if we have edge, no major risk flags, and sufficient margin
            if side is not None and edge_pct_side >= 5.0 and not risk_notes:
                bankroll = 1_000.0
                odds_side = f1_odds if side == "fighter_1" else f2_odds
                k = kelly_fraction(prob_side, odds_side)
                half_k = 0.5 * k
                bet_amount = round(bankroll * half_k, 2)

                if bet_amount > 0:
                    # Label very large edges (big disagreement) with "??"
                    if edge_pct_side > 20.0:
                        recommended_label = f"?? {name_side}"
                    else:
                        recommended_label = name_side

                    dec_side = american_to_decimal(odds_side)
                    profit_if_win = round(bet_amount * (dec_side - 1.0), 2)
                    payout_if_win = round(bet_amount + profit_if_win, 2)
                else:
                    recommended_label = "none"
                    profit_if_win = 0.0
                    payout_if_win = 0.0

            results.append(
                {
                    "event": event,
                    "fight_date": fight_date,
                    "fighter_1_name": f1.name,
                    "fighter_2_name": f2.name,
                    "fighter_1_odds": f1_odds,
                    "fighter_2_odds": f2_odds,
                    "is_title_fight": int(is_title),
                    # High-level percentages (keep these for readability)
                    "model_p_f1_pct": p_f1_pct,
                    "model_p_f2_pct": p_f2_pct,
                    "implied_p_f1_pct": imp_f1_pct,
                    "implied_p_f2_pct": imp_f2_pct,
                    "edge_f1_pct": edge_f1_pct,
                    "edge_f2_pct": edge_f2_pct,
                    "market_favorite": market_fav,
                    "model_favorite": model_fav,
                    "recommended_bet": recommended_label,
                    "bet_amount": bet_amount,
                    "risk_notes": risk_notes,
                    # Single-bet outcome if this one wins
                    "profit_if_win": profit_if_win,
                    "payout_if_win": payout_if_win,
                    # For CLV tracking – you can fill these in later by hand
                    "fighter_1_closing_odds": None,
                    "fighter_2_closing_odds": None,
                }
            )

        except Exception as e:
            logger.error(
                f"Error processing row {idx} "
                f"({row.get('fighter_1_name')} vs {row.get('fighter_2_name')}): {e}"
            )
            continue

    session.close()

    return pd.DataFrame(results)


def export_to_excel(
    input_path: str = "data/predictions/upcoming_fights.xlsx",
    output_path: str = "data/predictions/model_vs_market.xlsx",
    model_name: str = "xgboost_model",
) -> Tuple[Path, int]:
    """
    High-level helper: read fights+odds, add model info, write Excel.
    
    Args:
        input_path: Path to input Excel/CSV with fights and odds
        output_path: Path to output Excel file
        model_name: Name of the model to use (default: "xgboost_model")
    
    Returns:
        Tuple of (output_path, number_of_rows_written)
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading upcoming fights from {in_path} ...")
    df_in = load_input(in_path)

    logger.info(f"Adding model probabilities and edges using '{model_name}'...")
    df_out = add_model_predictions(df_in, model_name=model_name)

    # Cap total exposure across all fights to a maximum stake (e.g. $500)
    max_total_stake = 500.0
    total_stake = float(df_out.get("bet_amount", []).sum()) if "bet_amount" in df_out.columns else 0.0

    if total_stake > max_total_stake and total_stake > 0:
        scale = max_total_stake / total_stake
        logger.info(
            f"Scaling bet amounts by factor {scale:.3f} to cap total stake "
            f"at ${max_total_stake:.2f} (was ${total_stake:.2f})"
        )

        scaled_bets = []
        scaled_profit = []
        scaled_payout = []

        for _, row in df_out.iterrows():
            bet = float(row.get("bet_amount", 0.0))
            label = str(row.get("recommended_bet", "") or "")

            if bet <= 0.0 or not label:
                scaled_bets.append(0.0)
                scaled_profit.append(0.0)
                scaled_payout.append(0.0)
                continue

            new_bet = round(bet * scale, 2)

            # Determine which side this bet is on to get correct odds
            clean_label = label.replace("??", "").strip()
            odds_side = None
            if clean_label == str(row.get("fighter_1_name", "")).strip():
                odds_side = int(row.get("fighter_1_odds", 0))
            elif clean_label == str(row.get("fighter_2_name", "")).strip():
                odds_side = int(row.get("fighter_2_odds", 0))

            if new_bet > 0 and odds_side is not None:
                dec_side = american_to_decimal(odds_side)
                prof = round(new_bet * (dec_side - 1.0), 2)
                pay = round(new_bet + prof, 2)
            else:
                prof = 0.0
                pay = 0.0

            scaled_bets.append(new_bet)
            scaled_profit.append(prof)
            scaled_payout.append(pay)

        df_out["bet_amount"] = scaled_bets
        df_out["profit_if_win"] = scaled_profit
        df_out["payout_if_win"] = scaled_payout

    logger.info(f"Writing Excel to {out_path} ...")
    df_out.to_excel(out_path, index=False)

    logger.success(f"Saved {len(df_out)} fights to {out_path}")
    return out_path, len(df_out)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Export model vs market odds to Excel"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/predictions/upcoming_fights.xlsx",
        help="Path to input Excel/CSV with fights and odds",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/predictions/model_vs_market.xlsx",
        help="Path to output Excel file",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="xgboost_model",
        help="Model name to use (default: xgboost_model, e.g., xgboost_model_with_2025)",
    )

    args = parser.parse_args()
    export_to_excel(args.input, args.output, model_name=args.model_name)


if __name__ == "__main__":
    main()


