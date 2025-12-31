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
    - risk_notes                  (warnings about limited history)
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

EDGE = 3.0


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
    Detect limited history warnings.
    
    Only checks for limited fight history - no other risk factors.
    """
    if side not in ("fighter_1", "fighter_2"):
        return ""

    if side == "fighter_1":
        pfx = "f1_"
        name_side = f1_name
    else:
        pfx = "f2_"
        name_side = f2_name

    total_fights = int(features.get(f"{pfx}total_fights", 0) or 0)
    has_history = int(features.get(f"{pfx}has_fight_history", 0) or 0)
    
    # Check for limited history
    MIN_FIGHTS_REQUIRED = 3
    if has_history == 0 or total_fights < MIN_FIGHTS_REQUIRED:
        return (
            f"Limited history: {name_side} has {int(total_fights)} fights "
            f"(minimum {MIN_FIGHTS_REQUIRED} recommended for reliable predictions)."
        )

    return ""

def dump_feature_names(prefix, feature_vector):
    sorted_names = sorted(feature_vector.keys())
    print(f"\n[{prefix}] Feature count: {len(sorted_names)}")
    for name in sorted_names:
        print(name)
    print("\n")


def add_model_predictions(
    df: pd.DataFrame,
    model_name: str = "xgboost_model",
    *,
    symmetric: bool = False,
) -> pd.DataFrame:
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
            p_f1_raw = float(proba[0])
            p_f2_raw = 1.0 - p_f1_raw

            if symmetric:
                # Compute swapped orientation and build a symmetric probability for fighter_1:
                #   p_sym(f1 beats f2) = 0.5 * ( p(f1,f2) + (1 - p(f2,f1)) )
                features_swap = matchup_extractor.extract_matchup_features(f2.id, f1.id)
                features_swap["is_title_fight"] = 1 if is_title else 0
                X_df_swap = pd.DataFrame([features_swap])
                X_scaled_swap, _ = pipeline.prepare_features(X_df_swap, fit_scaler=False)
                proba_swap = xgb_model.predict(X_scaled_swap, use_calibrated=False)
                p_f2_as_f1 = float(proba_swap[0])  # P(original f2 wins | f2,f1)

                p_f1_sym = 0.5 * (p_f1_raw + (1.0 - p_f2_as_f1))
                p_f1 = max(0.0, min(1.0, p_f1_sym))
                p_f2 = 1.0 - p_f1
            else:
                p_f1 = p_f1_raw
                p_f2 = p_f2_raw

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
            p_f1_raw_pct = round(p_f1_raw * 100.0, 1)
            p_f2_raw_pct = round(p_f2_raw * 100.0, 1)
            imp_f1_pct = round(imp_f1 * 100.0, 1)
            imp_f2_pct = round(imp_f2 * 100.0, 1)
            edge_f1_pct = round(edge_f1 * 100.0, 1)
            edge_f2_pct = round(edge_f2 * 100.0, 1)

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

            # Check for limited history warnings (for both fighters)
            risk_notes = ""
            f1_total_fights = int(features.get("f1_total_fights", 0) or 0)
            f2_total_fights = int(features.get("f2_total_fights", 0) or 0)
            f1_has_history = int(features.get("f1_has_fight_history", 0) or 0)
            f2_has_history = int(features.get("f2_has_fight_history", 0) or 0)
            
            MIN_FIGHTS_REQUIRED = 3
            warnings = []
            
            if f1_has_history == 0 or f1_total_fights < MIN_FIGHTS_REQUIRED:
                warnings.append(f"{f1.name} has limited history ({int(f1_total_fights)} fights)")
            
            if f2_has_history == 0 or f2_total_fights < MIN_FIGHTS_REQUIRED:
                warnings.append(f"{f2.name} has limited history ({int(f2_total_fights)} fights)")
            
            if warnings:
                risk_notes = "; ".join(warnings)

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
                    "model_p_f1_raw_pct": p_f1_raw_pct,
                    "model_p_f2_raw_pct": p_f2_raw_pct,
                    "symmetric_mode": int(bool(symmetric)),
                    "implied_p_f1_pct": imp_f1_pct,
                    "implied_p_f2_pct": imp_f2_pct,
                    "edge_f1_pct": edge_f1_pct,
                    "edge_f2_pct": edge_f2_pct,
                    "market_favorite": market_fav,
                    "model_favorite": model_fav,
                    "risk_notes": risk_notes,
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
    symmetric: bool = False,
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
    df_out = add_model_predictions(df_in, model_name=model_name, symmetric=symmetric)


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
    parser.add_argument(
        "--symmetric",
        action="store_true",
        help=(
            "Compute probabilities in both fighter orders and use a symmetric probability for EV/edges. "
            "Adds model_p_*_raw_pct columns for debugging."
        ),
    )

    args = parser.parse_args()
    export_to_excel(args.input, args.output, model_name=args.model_name, symmetric=bool(args.symmetric))


if __name__ == "__main__":
    main()


