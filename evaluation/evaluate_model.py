#!/usr/bin/env python3
"""
Model-vs-Market Evaluation for UFC Fights
----------------------------------------

Phase 4 from `todo_1.md`:
  - Load a holdout set of fights (e.g. all 2025 events)
  - Generate / load features using the schema builder
  - Compare model probabilities vs betting market
  - Track:
      * Brier score
      * Log-loss
      * Calibration curves
      * Win / loss edges
      * Expected value vs closing lines
      * ROI vs Kelly / flat stakes
  - Save results into:
      reports/model_eval_<timestamp>.json
      reports/calibration_<timestamp>.png
      reports/roc_<timestamp>.png
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

from database.db_manager import DatabaseManager
from database.schema import Fighter, Event
from features.feature_pipeline import FeaturePipeline
from models.xgboost_model import XGBoostModel


def normalize_name(name: str) -> str:
    """Simple name normalizer for joining odds to DB fighter names."""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    # Remove punctuation and extra whitespace
    name = re.sub(r"[^a-z0-9\s]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def american_to_prob(odds: float) -> float:
    """Convert American odds to implied probability (no vig removal)."""
    try:
        o = float(odds)
    except (TypeError, ValueError):
        return np.nan
    if o == 0:
        return np.nan
    if o < 0:
        return (-o) / ((-o) + 100.0)
    else:
        return 100.0 / (o + 100.0)


def build_odds_index(odds_path: Path, date_tolerance_days: int = 0) -> pd.DataFrame:
    """
    Load odds CSV and build normalized keys for joining.

    Expected columns:
      - date (parseable to datetime)
      - fighter1
      - fighter2
      - fighter1_odds
      - fighter2_odds
    """
    df = pd.read_csv(odds_path)

    if "date" not in df.columns:
        raise ValueError("Odds file must have a 'date' column.")

    df["event_date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["event_date"])

    df["f1_name_norm"] = df["fighter1"].apply(normalize_name)
    df["f2_name_norm"] = df["fighter2"].apply(normalize_name)

    # Sorted name pair so we can join irrespective of ordering
    def _sorted_pair(row) -> Tuple[str, str]:
        n1, n2 = row["f1_name_norm"], row["f2_name_norm"]
        return tuple(sorted([n1, n2]))

    df[["name_a", "name_b"]] = df.apply(
        lambda r: pd.Series(_sorted_pair(r)), axis=1
    )

    # Normalize to midnight so we can safely shift by whole days if needed
    df["event_day"] = df["event_date"].dt.normalize()

    # Optional tolerance: if odds dates are off by +/- 1 day (common timezone issue),
    # we can expand each odds row to multiple candidate event days.
    try:
        date_tolerance_days = int(date_tolerance_days)
    except (TypeError, ValueError):
        date_tolerance_days = 0

    if date_tolerance_days > 0:
        expanded = []
        for delta in range(-date_tolerance_days, date_tolerance_days + 1):
            tmp = df.copy()
            tmp["event_day"] = tmp["event_day"] + pd.Timedelta(days=delta)
            tmp["odds_date_shift_days"] = delta
            expanded.append(tmp)
        df = pd.concat(expanded, ignore_index=True)
    else:
        df["odds_date_shift_days"] = 0

    # Key: YYYY-MM-DD | name_a | name_b
    df["fight_key"] = df.apply(
        lambda r: f"{r['event_day'].date()}|{r['name_a']}|{r['name_b']}", axis=1
    )

    # Precompute implied probabilities
    df["fighter1_prob"] = df["fighter1_odds"].apply(american_to_prob)
    df["fighter2_prob"] = df["fighter2_odds"].apply(american_to_prob)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate model vs betting market on holdout fights"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="xgboost_model",
        help=(
            "Saved XGBoost model name in models/saved/ (default: xgboost_model). "
            "Tip: keep a dedicated pre-2025 snapshot (e.g. xgboost_model_pre2025) "
            "so evaluation on 2025+ is stable and reproducible."
        ),
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/processed/training_data.csv",
        help="Path to full training dataset (with all fights)",
    )
    parser.add_argument(
        "--odds-path",
        type=str,
        default="ufc_2025_odds.csv",
        help="Path to odds CSV (American odds, one row per fight)",
    )
    parser.add_argument(
        "--odds-date-tolerance-days",
        type=int,
        default=0,
        help=(
            "Allow matching odds rows to events even if the odds 'date' is off by +/- N days "
            "(e.g., timezone mismatch where UFCStats shows Jan 18 but odds file uses Jan 19). "
            "Default: 0 (exact date match)."
        ),
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2025,
        help="Minimum event year to include in evaluation (e.g. 2025)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to save evaluation reports/plots",
    )
    parser.add_argument(
        "--strict-point-in-time",
        action="store_true",
        help=(
            "Leakage-audit mode: zero out base striking/grappling features that are sourced from "
            "current fighter profile stats and/or unfiltered fight relationships (not point-in-time safe). "
            "This helps quantify how much optimistic lift those features provide in backtests."
        ),
    )
    parser.add_argument(
        "--symmetric",
        action="store_true",
        default=True,
        help=(
            "Use symmetric probabilities by averaging both fighter orders (DEFAULT: True). "
            "Makes prediction order-invariant (flipping fighters gives same result). "
            "This matches the behavior of xgboost_predict.py with --symmetric flag."
        ),
    )
    parser.add_argument(
        "--no-symmetric",
        dest="symmetric",
        action="store_false",
        help="Disable symmetric mode (use raw prediction from single fighter order).",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_short = datetime.now().strftime("%Y%m%d")

    # ------------------------------------------------------------------
    # 1) Load odds and build index
    # ------------------------------------------------------------------
    logger.info(f"Loading odds from {args.odds_path}...")
    odds_df = build_odds_index(
        Path(args.odds_path),
        date_tolerance_days=args.odds_date_tolerance_days,
    )

    logger.info(f"Loaded {len(odds_df)} odds rows.")

    # ------------------------------------------------------------------
    # 2) Load dataset and restrict to holdout year (e.g. 2025)
    # ------------------------------------------------------------------
    logger.info(f"Loading dataset from {args.data_path}...")
    raw_df = pd.read_csv(args.data_path)

    if "event_id" not in raw_df.columns or "fighter_1_id" not in raw_df.columns:
        raise ValueError(
            "Dataset must contain 'event_id', 'fighter_1_id', and 'fighter_2_id' columns."
        )

    # Map event_id -> date, fighter_id -> name
    db = DatabaseManager()
    session = db.get_session()
    try:
        event_ids = (
            raw_df["event_id"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        events = (
            session.query(Event)
            .filter(Event.id.in_(event_ids))
            .all()
        )
        id_to_date = {e.id: e.date for e in events}

        fighter_ids = pd.concat(
            [raw_df["fighter_1_id"], raw_df["fighter_2_id"]]
        ).dropna().astype(int).unique().tolist()

        fighters = (
            session.query(Fighter)
            .filter(Fighter.id.in_(fighter_ids))
            .all()
        )
        id_to_name = {f.id: f.name for f in fighters}
    finally:
        session.close()

    raw_df["event_date"] = pd.to_datetime(
        raw_df["event_id"].map(id_to_date), errors="coerce"
    )
    raw_df["event_year"] = raw_df["event_date"].dt.year
    raw_df["event_day"] = raw_df["event_date"].dt.date

    # Restrict to holdout year+
    eval_df = raw_df[raw_df["event_year"] >= args.min_year].copy()
    logger.info(
        f"Holdout selection: {len(eval_df)} rows with event_year >= {args.min_year}."
    )

    if eval_df.empty:
        logger.warning("No evaluation rows found for specified year range.")
        return

    # Attach fighter names (normalized) for joining to odds
    eval_df["f1_name"] = eval_df["fighter_1_id"].map(id_to_name)
    eval_df["f2_name"] = eval_df["fighter_2_id"].map(id_to_name)
    eval_df["f1_name_norm"] = eval_df["f1_name"].apply(normalize_name)
    eval_df["f2_name_norm"] = eval_df["f2_name"].apply(normalize_name)

    def _sorted_pair_eval(row) -> Tuple[str, str]:
        n1, n2 = row["f1_name_norm"], row["f2_name_norm"]
        return tuple(sorted([n1, n2]))

    eval_df[["name_a", "name_b"]] = eval_df.apply(
        lambda r: pd.Series(_sorted_pair_eval(r)), axis=1
    )

    eval_df["fight_key"] = eval_df.apply(
        lambda r: f"{r['event_day']}|{r['name_a']}|{r['name_b']}", axis=1
    )

    # ------------------------------------------------------------------
    # 3) Join evaluation rows to odds
    # ------------------------------------------------------------------
    merged = eval_df.merge(
        odds_df[
            [
                "fight_key",
                "fighter1",
                "fighter2",
                "fighter1_odds",
                "fighter2_odds",
                "fighter1_prob",
                "fighter2_prob",
                "event_date",
            ]
        ],
        on="fight_key",
        how="inner",
        suffixes=("", "_odds"),
    )

    logger.info(
        f"Matched {len(merged)} evaluation rows to odds "
        f"(out of {len(eval_df)} potential rows)."
    )

    if merged.empty:
        logger.warning("No evaluation rows matched to odds; nothing to do.")
        return

    # Determine which side of the odds corresponds to this row's fighter_1
    merged["fighter1_norm_odds"] = merged["fighter1"].apply(normalize_name)
    merged["fighter2_norm_odds"] = merged["fighter2"].apply(normalize_name)

    def _pick_market_prob(row) -> float:
        f1_norm = row["f1_name_norm"]
        if f1_norm == row["fighter1_norm_odds"]:
            return row["fighter1_prob"]
        elif f1_norm == row["fighter2_norm_odds"]:
            return row["fighter2_prob"]
        else:
            # Name mismatch – we will drop this row later
            return np.nan

    merged["market_prob_f1"] = merged.apply(_pick_market_prob, axis=1)
    before_drop = len(merged)
    merged = merged.dropna(subset=["market_prob_f1"])
    logger.info(
        f"Dropped {before_drop - len(merged)} rows due to name mismatch between DB and odds."
    )

    if merged.empty:
        logger.warning("After name alignment, no rows remain; nothing to evaluate.")
        return

    # ------------------------------------------------------------------
    # Optional leakage-audit: remove non-point-in-time-safe feature groups
    # ------------------------------------------------------------------
    if args.strict_point_in_time:
        # These are the feature keys produced by the base "striking" and base "grappling" groups.
        # We keep *recent_* FightStats-derived features (they already use fight_history filtered by as_of_date).
        base_striking_keys = [
            "sig_strikes_landed_per_min",
            "striking_accuracy",
            "striking_defense",
            "striking_differential",
            "defensive_efficiency",
            "striking_volume_control",
            "distance_accuracy_last_3",
            "clinch_accuracy_last_3",
            "ground_output_per_min_last_3",
            "leg_strike_rate_last_3",
            "knockdowns_last_3",
            "striking_accuracy_last_3",
            "sig_strikes_landed_per_min_last_3",
            "head_strike_rate_last_3",
            "body_strike_rate_last_3",
            "ground_strike_rate_last_3",
            "distance_strike_rate_last_3",
            "distance_accuracy_lifetime",
            "clinch_accuracy_lifetime",
            "ground_output_per_min_lifetime",
            "leg_strike_rate_lifetime",
            "knockdowns_lifetime",
            "head_strike_rate_lifetime",
            "body_strike_rate_lifetime",
            "ground_strike_rate_lifetime",
            "distance_strike_rate_lifetime",
            "sig_strikes_landed_per_min_lifetime",
            "striking_accuracy_lifetime",
        ]
        base_grappling_keys = [
            "takedown_avg_per_15min",
            "takedown_accuracy",
            "takedown_defense",
            "submission_avg_per_15min",
        ]

        cols_to_zero = []
        for prefix in ("f1_", "f2_"):
            for k in base_striking_keys + base_grappling_keys:
                c = f"{prefix}{k}"
                if c in merged.columns:
                    cols_to_zero.append(c)

        if cols_to_zero:
            merged.loc[:, cols_to_zero] = 0.0
            logger.warning(
                f"[strict-point-in-time] Zeroed {len(cols_to_zero)} base striking/grappling columns "
                f"to reduce leakage risk for backtests."
            )
        else:
            logger.warning(
                "[strict-point-in-time] No matching striking/grappling columns found to zero; "
                "check feature schema or dataset columns."
            )

    # ------------------------------------------------------------------
    # 4) Prepare features (using saved pipeline) and get model predictions
    # ------------------------------------------------------------------
    logger.info("Loading feature pipeline and model...")
    model_name = args.model_name
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline(model_name=model_name)

    xgb_model = XGBoostModel()
    xgb_model.load_model(model_name)

    # Prepare features for evaluation (inference mode: fit_scaler=False)
    X_eval, y_eval = pipeline.prepare_features(merged, fit_scaler=False)

    logger.info(f"Prepared evaluation features: {X_eval.shape[0]} rows, {X_eval.shape[1]} cols.")

    # Predict probabilities for fighter_1 in each row
    model_probs = xgb_model.predict(X_eval, use_calibrated=False)

    merged["model_prob_f1"] = model_probs
    merged["model_name"] = model_name
    merged["target"] = merged.get("target", y_eval)

    # ------------------------------------------------------------------
    # 4b) Apply symmetric averaging if requested (matches xgboost_predict.py behavior)
    # ------------------------------------------------------------------
    if args.symmetric:
        logger.info("Applying symmetric probability averaging (matching xgboost_predict.py --symmetric)...")
        # For each unique fight (identified by fight_key), we have 2 rows (both perspectives)
        # We need to compute symmetric probability: p_f1 = 0.5 * (p_f1_raw + (1.0 - p_f2_raw))
        
        # Create a symmetric probability column
        merged["model_prob_f1_symmetric"] = np.nan
        
        # Group by fight_key to get both perspectives of the same fight
        for fight_key, group in merged.groupby("fight_key"):
            if len(group) < 2:
                # Only one perspective available, use raw prediction
                merged.loc[group.index, "model_prob_f1_symmetric"] = group["model_prob_f1"].values
                continue
            
            # Get both rows - they should be the two perspectives (f1, f2) and (f2, f1)
            if len(group) != 2:
                # Unexpected number of rows, use raw predictions
                merged.loc[group.index, "model_prob_f1_symmetric"] = group["model_prob_f1"].values
                continue
            
            # Get the two rows as Series
            idx_list = list(group.index)
            row1_idx = idx_list[0]
            row2_idx = idx_list[1]
            row1 = group.loc[row1_idx]
            row2 = group.loc[row2_idx]
            
            # Verify these are the two perspectives of the same fight
            # (fighter_1_id and fighter_2_id should be swapped)
            f1_id_1 = int(row1["fighter_1_id"]) if "fighter_1_id" in row1 else None
            f2_id_1 = int(row1["fighter_2_id"]) if "fighter_2_id" in row1 else None
            f1_id_2 = int(row2["fighter_1_id"]) if "fighter_1_id" in row2 else None
            f2_id_2 = int(row2["fighter_2_id"]) if "fighter_2_id" in row2 else None
            
            if (f1_id_1 is not None and f2_id_1 is not None and 
                f1_id_2 is not None and f2_id_2 is not None and
                f1_id_1 == f2_id_2 and f2_id_1 == f1_id_2):
                # These are the two perspectives: (f1, f2) and (f2, f1)
                p_f1_raw = float(row1["model_prob_f1"])  # P(f1 wins | f1, f2)
                p_f2_raw = float(row2["model_prob_f1"])  # P(f2 wins | f2, f1)
                
                # Symmetric probability for fighter_1 (from row1's perspective)
                p_f1_symmetric = 0.5 * (p_f1_raw + (1.0 - p_f2_raw))
                p_f2_symmetric = 1.0 - p_f1_symmetric
                
                # Apply to both rows
                merged.loc[row1_idx, "model_prob_f1_symmetric"] = p_f1_symmetric
                merged.loc[row2_idx, "model_prob_f1_symmetric"] = p_f2_symmetric
            else:
                # Not matching perspectives, use raw predictions
                merged.loc[group.index, "model_prob_f1_symmetric"] = group["model_prob_f1"].values
        
        # Use symmetric probabilities if available, otherwise fall back to raw
        merged["model_prob_f1"] = merged["model_prob_f1_symmetric"].fillna(merged["model_prob_f1"])
        logger.info("Applied symmetric probability averaging.")
    else:
        logger.info("Using raw predictions (symmetric mode disabled).")

    # ------------------------------------------------------------------
    # 5) Compute metrics vs market
    # ------------------------------------------------------------------
    y_true = merged["target"].astype(int).values
    p_model = merged["model_prob_f1"].values
    p_market = merged["market_prob_f1"].values

    # Core metrics
    # Clip probabilities to avoid log(0) without relying on sklearn's deprecated eps arg
    p_model_clipped = np.clip(p_model, 1e-15, 1 - 1e-15)
    brier = brier_score_loss(y_true, p_model_clipped)
    ll = log_loss(y_true, p_model_clipped)
    try:
        auc = roc_auc_score(y_true, p_model)
    except ValueError:
        auc = float("nan")

    # Edge and simple ROI (flat 1-unit stakes, bet if edge > 0)
    edge = p_model - p_market
    merged["edge"] = edge

    # Flat betting: 1 unit on fighter_1 whenever edge > 0
    bets_mask = edge > 0
    n_bets = bets_mask.sum()
    if n_bets > 0:
        # Determine actual price you would get for fighter_1 in each row
        def _pick_price(row) -> float:
            f1_norm = row["f1_name_norm"]
            if f1_norm == row["fighter1_norm_odds"]:
                return row["fighter1_odds"]
            else:
                return row["fighter2_odds"]

        merged["price_f1"] = merged.apply(_pick_price, axis=1)

        prices = merged.loc[bets_mask, "price_f1"].values
        outcomes = y_true[bets_mask]

        # Profit per bet in units
        profits = []
        for o, price in zip(outcomes, prices):
            if price > 0:
                payout = price / 100.0  # profit on 1 unit stake if win
            else:
                payout = 100.0 / (-price)
            profits.append(payout if o == 1 else -1.0)

        profits = np.array(profits)
        roi_flat = profits.mean()
    else:
        roi_flat = float("nan")

    # ------------------------------------------------------------------
    # 5b) Simple winner/loser accuracy statistics
    # ------------------------------------------------------------------
    # Fighter-row accuracy: does model_prob_f1 > 0.5 agree with target?
    row_preds = (p_model >= 0.5).astype(int)
    row_correct = (row_preds == y_true).sum()
    row_total = len(y_true)
    row_acc = row_correct / row_total if row_total > 0 else float("nan")

    print("\n" + "=" * 80)
    print("Fighter-row prediction accuracy (model_prob_f1 >= 0.5 as pick):")
    print(f"  Correct rows: {row_correct}/{row_total}  (accuracy={row_acc:.3f})")

    # ------------------------------------------------------------------
    # 6) Human-readable diagnostics: fight-level top/bottom edges
    # ------------------------------------------------------------------
    # Collapse to one row per fight_key:
    #   - winner / loser names
    #   - model & market probs for each side
    #   - edge_best: max(edge_winner, edge_loser)
    #   - edge_worst: min(edge_winner, edge_loser)
    fight_rows = []
    for fk, g in merged.groupby("fight_key"):
        if g.empty:
            continue

        # Sort so winner row (target==1) comes first if present
        g_sorted = g.sort_values("target", ascending=False)
        winner_row = g_sorted.iloc[0]
        loser_row = g_sorted.iloc[1] if len(g_sorted) > 1 else None

        event_date_fight = pd.to_datetime(
            winner_row.get("event_date"), errors="coerce"
        ).date()

        winner_name = winner_row.get("f1_name")
        winner_model_prob = winner_row.get("model_prob_f1")
        winner_market_prob = winner_row.get("market_prob_f1")
        winner_edge = winner_row.get("edge")

        if loser_row is not None:
            loser_name = loser_row.get("f1_name")
            loser_model_prob = loser_row.get("model_prob_f1")
            loser_market_prob = loser_row.get("market_prob_f1")
            loser_edge = loser_row.get("edge")
        else:
            # Fallback if we only have one row for some reason
            loser_name = winner_row.get("f2_name")
            loser_model_prob = np.nan
            loser_market_prob = np.nan
            loser_edge = np.nan

        edges = [
            e for e in [winner_edge, loser_edge] if isinstance(e, (int, float, np.floating))
        ]
        edge_best = max(edges) if edges else np.nan
        edge_worst = min(edges) if edges else np.nan

        fight_rows.append(
            {
                "fight_key": fk,
                "event_date": event_date_fight,
                "fighter_winner": winner_name if winner_row.get("target", 0) == 1 else loser_name,
                "fighter_loser": loser_name if winner_row.get("target", 0) == 1 else winner_name,
                "winner_model_prob": winner_model_prob,
                "winner_market_prob": winner_market_prob,
                "loser_model_prob": loser_model_prob,
                "loser_market_prob": loser_market_prob,
                "edge_winner": winner_edge,
                "edge_loser": loser_edge,
                "edge_best": edge_best,
                "edge_worst": edge_worst,
            }
        )

    fight_df = pd.DataFrame(fight_rows)

    def _print_fight_table(df: pd.DataFrame, title: str) -> None:
        if df.empty:
            return
        
        # Create a simplified dataframe focused on the winner
        display_df = df.copy()
        
        # Calculate edge as percentage difference (model - market)
        display_df["edge_pct"] = (
            (display_df["winner_model_prob"] - display_df["winner_market_prob"]) * 100
        )
        
        # Format probabilities as percentages
        display_df["model_pct"] = (display_df["winner_model_prob"] * 100).round(1)
        display_df["market_pct"] = (display_df["winner_market_prob"] * 100).round(1)
        display_df["edge_pct"] = display_df["edge_pct"].round(1)
        
        # Select only the columns we want to show
        cols = [
            "event_date",
            "fighter_winner",
            "model_pct",
            "market_pct",
            "edge_pct",
        ]
        safe_cols = [c for c in cols if c in display_df.columns]
        
        # Rename columns for better display
        display_df = display_df[safe_cols].copy()
        display_df.columns = [
            "Date",
            "Winner",
            "Model %",
            "Market %",
            "Edge %",
        ]
        
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
        print(display_df.to_string(index=False))

    if not fight_df.empty:
        # Top 10 fights where the best side (by edge) looks most underpriced
        top_fights = fight_df.sort_values("edge_best", ascending=False).head(10)
        _print_fight_table(
            top_fights,
            "Top 10 fights by max positive edge (edge_best)",
        )

        # Bottom 10 fights where even the best side has the most negative edge
        bottom_fights = fight_df.sort_values("edge_best", ascending=True).head(10)
        _print_fight_table(
            bottom_fights,
            "Bottom 10 fights by max edge (most negative edge_best)",
        )

        # Fights where the model gave higher probability to the loser than the winner
        wrong_mask = (
            fight_df["loser_model_prob"].notna()
            & fight_df["winner_model_prob"].notna()
            & (fight_df["loser_model_prob"] > fight_df["winner_model_prob"])
        )
        wrong_fights = fight_df[wrong_mask].copy()
        if not wrong_fights.empty:
            wrong_fights["prob_diff"] = (
                wrong_fights["loser_model_prob"] - wrong_fights["winner_model_prob"]
            )
            worst_misranked = wrong_fights.sort_values(
                "prob_diff", ascending=False
            ).head(10)
            _print_fight_table(
                worst_misranked,
                "Top 10 fights where model favored the LOSER over the WINNER "
                "(loser_model_prob > winner_model_prob)",
            )

            # Fight-level accuracy: did the model give higher prob to the winner?
            valid_mask = (
                fight_df["winner_model_prob"].notna()
                & fight_df["loser_model_prob"].notna()
            )
            valid_fights = fight_df[valid_mask].copy()
            n_fights_total = len(valid_fights)
            if n_fights_total > 0:
                correct_mask = (
                    valid_fights["winner_model_prob"]
                    > valid_fights["loser_model_prob"]
                )
                n_correct = int(correct_mask.sum())
                n_incorrect = int(n_fights_total - n_correct)
                fight_acc = n_correct / n_fights_total

                print("\n" + "=" * 80)
                print("Fight-level accuracy (winner_model_prob > loser_model_prob):")
                print(
                    f"  Correct fights: {n_correct}/{n_fights_total}  "
                    f"(accuracy={fight_acc:.3f})"
                )

    # ------------------------------------------------------------------
    # 6b) Print specific fighter matchup: Jalin Turner vs Edson Barboza
    # ------------------------------------------------------------------
    target_fighters = ["Jack Della Maddalena", "Belal Muhammed"]
    target_fighters_norm = [normalize_name(f) for f in target_fighters]
    
    # Search in merged dataframe for rows containing these fighters
    fighter_mask = (
        merged["f1_name_norm"].isin(target_fighters_norm)
        | merged["f2_name_norm"].isin(target_fighters_norm)
    )
    target_rows = merged[fighter_mask].copy()
    
    if not target_rows.empty:
        # Further filter to only rows where BOTH fighters are in the target list
        both_fighters_mask = (
            target_rows["f1_name_norm"].isin(target_fighters_norm)
            & target_rows["f2_name_norm"].isin(target_fighters_norm)
        )
        target_fight = target_rows[both_fighters_mask]
        
        if not target_fight.empty:
            # Take the first matching row
            row = target_fight.iloc[0]
            
            # Determine which fighter is which
            f1_name = row["f1_name"]
            f2_name = row["f2_name"]
            f1_model_prob = row["model_prob_f1"]
            f2_model_prob = 1.0 - f1_model_prob
            f1_market_prob = row["market_prob_f1"]
            
            # Get market prob for fighter_2
            f1_norm = row["f1_name_norm"]
            if f1_norm == row["fighter1_norm_odds"]:
                f2_market_prob = row["fighter2_prob"]
            else:
                f2_market_prob = row["fighter1_prob"]
            
            f1_edge = row["edge"]
            f2_edge = f2_model_prob - f2_market_prob
            
            event_date_str = pd.to_datetime(row.get("event_date"), errors="coerce")
            event_date_display = event_date_str.strftime("%Y-%m-%d") if pd.notna(event_date_str) else "Unknown"
            
            print("\n" + "=" * 80)
            print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
            print("=" * 80)
            print(f"Event Date: {event_date_display}")
            print(f"\n{f1_name}:")
            print(f"  Model Probability: {f1_model_prob:.1%}")
            print(f"  Market Probability: {f1_market_prob:.1%}")
            print(f"  Edge: {f1_edge:+.1%}")
            print(f"\n{f2_name}:")
            print(f"  Model Probability: {f2_model_prob:.1%}")
            print(f"  Market Probability: {f2_market_prob:.1%}")
            print(f"  Edge: {f2_edge:+.1%}")
            
            # Get odds
            if f1_norm == row["fighter1_norm_odds"]:
                f1_odds = row["fighter1_odds"]
                f2_odds = row["fighter2_odds"]
            else:
                f1_odds = row["fighter2_odds"]
                f2_odds = row["fighter1_odds"]
            
            print(f"\nMarket Odds:")
            print(f"  {f1_name}: {f1_odds:+.0f}")
            print(f"  {f2_name}: {f2_odds:+.0f}")
            
            # Determine recommended bet based on edge
            if f1_edge > 0.05:  # 5% edge threshold
                print(f"\n⭐ Recommended Bet: {f1_name} (edge: {f1_edge:+.1%})")
            elif f2_edge > 0.05:
                print(f"\n⭐ Recommended Bet: {f2_name} (edge: {f2_edge:+.1%})")
            else:
                print(f"\n⚠️  No strong edge detected (both edges < 5%)")
        else:
            # Check if fight exists in odds but not in evaluation data (future fight)
            odds_fighter_mask = (
                odds_df["fighter1"].str.contains("Turner|Barboza", case=False, na=False)
                | odds_df["fighter2"].str.contains("Turner|Barboza", case=False, na=False)
            )
            odds_match = odds_df[odds_fighter_mask]
            
            if not odds_match.empty:
                # Check if both fighters are present
                both_in_odds = odds_match.apply(
                    lambda r: (
                        normalize_name(str(r["fighter1"])) in target_fighters_norm
                        and normalize_name(str(r["fighter2"])) in target_fighters_norm
                    ),
                    axis=1
                )
                odds_fight = odds_match[both_in_odds]
                
                if not odds_fight.empty:
                    row = odds_fight.iloc[0]
                    event_date_str = pd.to_datetime(row.get("event_date"), errors="coerce")
                    event_date_display = event_date_str.strftime("%Y-%m-%d") if pd.notna(event_date_str) else "Unknown"
                    
                    print("\n" + "=" * 80)
                    print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
                    print("=" * 80)
                    print(f"Event Date: {event_date_display}")
                    print("\n⚠️  Fight found in odds file but not in evaluation data (likely future fight)")
                    print(f"\nMarket Odds:")
                    print(f"  {row['fighter1']}: {row['fighter1_odds']:+.0f} (implied prob: {row['fighter1_prob']:.1%})")
                    print(f"  {row['fighter2']}: {row['fighter2_odds']:+.0f} (implied prob: {row['fighter2_prob']:.1%})")
                    print("\n⚠️  Model prediction not available (fight not in training data)")
                else:
                    print("\n" + "=" * 80)
                    print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
                    print("=" * 80)
                    print("⚠️  Fight not found in evaluation data or odds file")
            else:
                print("\n" + "=" * 80)
                print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
                print("=" * 80)
                print("⚠️  Fight not found in evaluation data or odds file")
    else:
        # Check odds file directly
        odds_fighter_mask = (
            odds_df["fighter1"].str.contains("Turner|Barboza", case=False, na=False)
            | odds_df["fighter2"].str.contains("Turner|Barboza", case=False, na=False)
        )
        odds_match = odds_df[odds_fighter_mask]
        
        if not odds_match.empty:
            both_in_odds = odds_match.apply(
                lambda r: (
                    normalize_name(str(r["fighter1"])) in target_fighters_norm
                    and normalize_name(str(r["fighter2"])) in target_fighters_norm
                ),
                axis=1
            )
            odds_fight = odds_match[both_in_odds]
            
            if not odds_fight.empty:
                row = odds_fight.iloc[0]
                event_date_str = pd.to_datetime(row.get("event_date"), errors="coerce")
                event_date_display = event_date_str.strftime("%Y-%m-%d") if pd.notna(event_date_str) else "Unknown"
                
                print("\n" + "=" * 80)
                print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
                print("=" * 80)
                print(f"Event Date: {event_date_display}")
                print("\n⚠️  Fight found in odds file but not in evaluation data (likely future fight)")
                print(f"\nMarket Odds:")
                print(f"  {row['fighter1']}: {row['fighter1_odds']:+.0f} (implied prob: {row['fighter1_prob']:.1%})")
                print(f"  {row['fighter2']}: {row['fighter2_odds']:+.0f} (implied prob: {row['fighter2_prob']:.1%})")
                print("\n⚠️  Model prediction not available (fight not in training data)")
            else:
                print("\n" + "=" * 80)
                print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
                print("=" * 80)
                print("⚠️  Fight not found in evaluation data or odds file")
        else:
            print("\n" + "=" * 80)
            print("SPECIFIC FIGHT: Jalin Turner vs Edson Barboza")
            print("=" * 80)
            print("⚠️  Fight not found in evaluation data or odds file")

    # ------------------------------------------------------------------
    # 6c) Save evaluation data for deep analysis
    # ------------------------------------------------------------------
    eval_data_path = output_dir / f"eval_data_{timestamp}.csv"
    merged.to_csv(eval_data_path, index=False)
    logger.success(f"Saved evaluation data to {eval_data_path}")
    
    # Generate HTML report
    logger.info("Generating interactive HTML report...")
    try:
        from evaluation.generate_html_report import generate_html_report
        html_path = output_dir / f"model_evaluation_{timestamp}.html"
        generate_html_report(eval_data_path, html_path, min_year=args.min_year)
        logger.success(f"✓ Open report in browser: file://{html_path.absolute()}")
    except Exception as e:
        logger.warning(f"Failed to generate HTML report: {e}")

    # ------------------------------------------------------------------
    # 7) Compute curves and save JSON report / plots
    # ------------------------------------------------------------------
    # Calibration curve (for plotting)
    frac_pos, mean_pred = calibration_curve(y_true, p_model, n_bins=10)

    # ROC curve
    fpr, tpr, _ = roc_curve(y_true, p_model)

    # ------------------------------------------------------------------
    # Save JSON report and plots
    # ------------------------------------------------------------------
    
    # Calculate accuracy metrics
    row_preds = (p_model >= 0.5).astype(int)
    row_correct = (row_preds == y_true).sum()
    row_total = len(y_true)
    overall_accuracy = row_correct / row_total if row_total > 0 else float("nan")
    
    # Calculate accuracy by favorites/underdogs
    # Determine if fighter_1 is favorite based on market odds
    merged["is_favorite"] = merged["market_prob_f1"] >= 0.5
    merged["prediction_correct"] = (row_preds == y_true)
    
    favorites_mask = merged["is_favorite"]
    underdogs_mask = ~favorites_mask
    
    favorites_correct = merged.loc[favorites_mask, "prediction_correct"].sum()
    favorites_total = favorites_mask.sum()
    favorites_accuracy = favorites_correct / favorites_total if favorites_total > 0 else float("nan")
    
    underdogs_correct = merged.loc[underdogs_mask, "prediction_correct"].sum()
    underdogs_total = underdogs_mask.sum()
    underdogs_accuracy = underdogs_correct / underdogs_total if underdogs_total > 0 else float("nan")
    
    # Calculate accuracy by confidence buckets (percentile-based)
    # Base confidence: abs(model_prob_f1 - 0.5) * 2, which maps [0.5, 1.0] -> [0, 1]
    # This measures distance from 50/50 (larger = more confident)
    base_conf = np.abs(p_model - 0.5) * 2  # [0, 1]
    
    # Odds-aware confidence adjustment (for ranking only, not for training)
    adjusted_conf = np.full_like(base_conf, np.nan)
    p_market = merged["market_prob_f1"].values
    
    # Calculate finish rate for volatility gate
    # Check if either fighter has high finish rate (> 0.55)
    high_finish_rate = np.zeros(len(merged), dtype=bool)
    if "f1_finish_rate" in merged.columns and "f2_finish_rate" in merged.columns:
        f1_fr = merged["f1_finish_rate"].fillna(0).values
        f2_fr = merged["f2_finish_rate"].fillna(0).values
        # High finish rate if either fighter has > 0.55
        high_finish_rate = (f1_fr > 0.55) | (f2_fr > 0.55)
    elif "finish_rate_diff" in merged.columns:
        # Fallback: use finish_rate_diff if individual rates not available
        # This is less precise but better than nothing
        finish_rate_abs = np.abs(merged["finish_rate_diff"].fillna(0).values)
        high_finish_rate = finish_rate_abs > 0.3  # Threshold for high finish rate differential
    # If no finish rate data available, high_finish_rate remains False
    
    for i in range(len(merged)):
        if pd.notna(p_market[i]):
            # Odds available: calculate market confidence and edge
            market_conf = np.abs(p_market[i] - 0.5) * 2  # [0, 1]
            market_edge = base_conf[i] - market_conf
            
            # Penalize ONLY when model is more confident than market
            if market_edge > 0:
                # Penalty: reduce confidence when model is overconfident vs market
                # Cap penalty at 0.6 (60% reduction max)
                penalty = min(market_edge * 1.5, 0.6)
                adjusted_conf[i] = base_conf[i] * (1.0 - penalty)
            else:
                # Model is less confident than market: no penalty
                adjusted_conf[i] = base_conf[i]
        else:
            # No odds available: use base confidence
            adjusted_conf[i] = base_conf[i]
        
        # Volatility gate: penalize high-confidence predictions in high-finish-rate matchups
        # This accounts for increased volatility/uncertainty in finisher vs finisher fights
        if adjusted_conf[i] > 0.7 and high_finish_rate[i]:
            adjusted_conf[i] *= 0.85  # Reduce by 15% (was 0.75 = 25% reduction)
    
    # For top 10%: use base confidence (no odds adjustment)
    top_10_threshold = np.percentile(base_conf, 90)  # Top 10% = 90th percentile
    top_10_mask = base_conf >= top_10_threshold
    
    # For top 25%: use odds-adjusted confidence (if available)
    # This identifies predictions where model is both confident AND agrees with market
    # Filter out NaN values for percentile calculation
    valid_adjusted_conf = adjusted_conf[~np.isnan(adjusted_conf)]
    if len(valid_adjusted_conf) > 0:
        top_25_threshold = np.percentile(valid_adjusted_conf, 75)  # Top 25% = 75th percentile
        top_25_mask = adjusted_conf >= top_25_threshold
    else:
        # Fallback to base confidence if no valid adjusted confidence
        top_25_threshold = np.percentile(base_conf, 75)
        top_25_mask = base_conf >= top_25_threshold
    
    by_confidence = {}
    
    # Top 10% bucket
    if top_10_mask.sum() > 0:
        top_10_correct = (row_preds[top_10_mask] == y_true[top_10_mask]).sum()
        top_10_total = top_10_mask.sum()
        top_10_accuracy = top_10_correct / top_10_total if top_10_total > 0 else None
        by_confidence["top_10_pct"] = {
            "min_p": round(float(top_10_threshold), 4),
            "accuracy": round(top_10_accuracy, 4) if top_10_accuracy is not None else None,
            "n": int(top_10_total)
        }
    else:
        by_confidence["top_10_pct"] = {
            "min_p": None,
            "accuracy": None,
            "n": 0
        }
    
    # Top 25% bucket
    if top_25_mask.sum() > 0:
        top_25_correct = (row_preds[top_25_mask] == y_true[top_25_mask]).sum()
        top_25_total = top_25_mask.sum()
        top_25_accuracy = top_25_correct / top_25_total if top_25_total > 0 else None
        by_confidence["top_25_pct"] = {
            "min_p": round(float(top_25_threshold), 4),
            "accuracy": round(top_25_accuracy, 4) if top_25_accuracy is not None else None,
            "n": int(top_25_total)
        }
        
        # Export detailed top 25% predictions for investigation
        top_25_df = merged[top_25_mask].copy()
        top_25_df["base_confidence"] = base_conf[top_25_mask]
        top_25_df["adjusted_confidence"] = adjusted_conf[top_25_mask]
        top_25_df["prediction_correct"] = (row_preds[top_25_mask] == y_true[top_25_mask])
        top_25_df["model_prob_f1"] = p_model[top_25_mask]
        top_25_df["model_prob_f2"] = 1.0 - p_model[top_25_mask]
        
        # Get top 3 features for f1 and f2 from feature importance
        try:
            feature_importance = xgb_model.get_feature_importance(importance_type='weight', top_n=None)
            # Get top 3 f1_ features
            f1_features = feature_importance[feature_importance['feature'].str.startswith('f1_')].head(3)
            f2_features = feature_importance[feature_importance['feature'].str.startswith('f2_')].head(3)
            
            # Add top 3 feature values for f1
            for rank, (_, row) in enumerate(f1_features.iterrows(), 1):
                feat_name = row['feature']
                if feat_name in top_25_df.columns:
                    feat_short_name = feat_name.replace('f1_', '')
                    top_25_df[f"f1_top{rank}_{feat_short_name}"] = top_25_df[feat_name]
            
            # Add top 3 feature values for f2
            for rank, (_, row) in enumerate(f2_features.iterrows(), 1):
                feat_name = row['feature']
                if feat_name in top_25_df.columns:
                    feat_short_name = feat_name.replace('f2_', '')
                    top_25_df[f"f2_top{rank}_{feat_short_name}"] = top_25_df[feat_name]
        except Exception as e:
            logger.warning(f"Could not extract top features: {e}")
        
        # Select relevant columns for investigation (excluding removed columns)
        investigation_cols = [
            "event_date", "f1_name", "f2_name", "weight_class",
            "model_prob_f1", "model_prob_f2", "base_confidence", "adjusted_confidence",
            "prediction_correct", "market_prob_f2", "fighter1_odds", "fighter2_odds",
            "is_favorite"
        ]
        
        # Add top feature columns if they exist
        top_feature_cols = [col for col in top_25_df.columns if col.startswith('f1_top') or col.startswith('f2_top')]
        investigation_cols.extend(top_feature_cols)
        
        # Only include columns that exist
        available_cols = [col for col in investigation_cols if col in top_25_df.columns]
        top_25_export = top_25_df[available_cols].copy()
        
        # Deduplicate: keep only one row per fight (f1 vs f2, not f2 vs f1)
        # Create a canonical fight key from sorted fighter names
        top_25_export["canonical_fight_key"] = top_25_export.apply(
            lambda row: "|".join(sorted([str(row.get("f1_name", "")), str(row.get("f2_name", ""))])),
            axis=1
        )
        
        # Keep only rows where f1_name < f2_name (alphabetically) to avoid duplicates
        # This ensures we keep (A vs B) but not (B vs A)
        def _should_keep(row):
            f1 = str(row.get("f1_name", ""))
            f2 = str(row.get("f2_name", ""))
            try:
                return f1 < f2
            except:
                # If comparison fails, keep the row (better than dropping)
                return True
        
        keep_mask = top_25_export.apply(_should_keep, axis=1)
        top_25_export = top_25_export[keep_mask].copy()
        
        # Also drop duplicates by canonical key (in case there are still duplicates)
        top_25_export = top_25_export.drop_duplicates(subset=["canonical_fight_key"], keep="first")
        
        # Drop the canonical key column (it was just for deduplication)
        if "canonical_fight_key" in top_25_export.columns:
            top_25_export = top_25_export.drop(columns=["canonical_fight_key"])
        
        # Sort by adjusted confidence (highest first) then by correctness (wrong predictions first)
        top_25_export = top_25_export.sort_values(
            ["prediction_correct", "adjusted_confidence"],
            ascending=[True, False]  # Wrong predictions first, then by adjusted confidence descending
        )
        
        # Save to CSV
        top_25_export_path = output_dir / f"top_25_pct_investigation_{timestamp}.csv"
        top_25_export.to_csv(top_25_export_path, index=False)
        logger.success(f"Saved top 25% confidence bucket details to {top_25_export_path}")
        logger.info(f"  Total predictions in top 25%: {top_25_total}")
        logger.info(f"  After deduplication: {len(top_25_export)}")
        logger.info(f"  Correct: {top_25_correct} ({top_25_accuracy:.1%})")
        logger.info(f"  Incorrect: {top_25_total - top_25_correct} ({1.0 - top_25_accuracy:.1%})")
        logger.info(f"  Confidence threshold: {top_25_threshold:.4f}")
    else:
        by_confidence["top_25_pct"] = {
            "min_p": None,
            "accuracy": None,
            "n": 0
        }
    
    # Build comprehensive report
    report = {
        "model_name": model_name,
        "holdout_from_year": args.min_year,
        "timestamp": timestamp_short,
        "overall": {
            "accuracy": round(overall_accuracy, 4) if not np.isnan(overall_accuracy) else None,
            "n_correct": int(row_correct),
            "n_total": int(row_total),
            "brier": round(float(brier), 4) if not np.isnan(brier) else None,
            "auc": round(float(auc), 4) if not np.isnan(auc) else None,
            "log_loss": round(float(ll), 4) if not np.isnan(ll) else None,
        },
        "by_bucket": {
            "favorites": {
                "accuracy": round(favorites_accuracy, 4) if not np.isnan(favorites_accuracy) else None,
                "n": int(favorites_total)
            },
            "underdogs": {
                "accuracy": round(underdogs_accuracy, 4) if not np.isnan(underdogs_accuracy) else None,
                "n": int(underdogs_total)
            }
        },
        "by_confidence": by_confidence,
        # Additional metrics for backward compatibility
        "n_eval_rows": int(len(merged)),
        "n_odds_rows": int(len(odds_df)),
        "n_bets_edge_gt_0": int(n_bets),
        "roi_flat_edge_gt_0": round(float(roi_flat), 4) if not np.isnan(roi_flat) else None,
    }

    report_path = output_dir / f"model_eval_{timestamp}.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2, allow_nan=False)

    logger.success(f"Saved evaluation report to {report_path}")

    # Calibration plot
    plt.figure(figsize=(8, 6))
    plt.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    plt.plot(mean_pred, frac_pos, "s-", label="Model")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed frequency")
    plt.title("Calibration Curve (holdout)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    calib_path = output_dir / f"calibration_{timestamp}.png"
    plt.tight_layout()
    plt.savefig(calib_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.success(f"Saved calibration plot to {calib_path}")

    # ROC plot
    plt.figure(figsize=(8, 6))
    plt.plot([0, 1], [0, 1], "k--", label="Random")
    plt.plot(fpr, tpr, label=f"Model (AUC={auc:.3f})")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve (holdout)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    roc_path = output_dir / f"roc_{timestamp}.png"
    plt.tight_layout()
    plt.savefig(roc_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.success(f"Saved ROC plot to {roc_path}")


if __name__ == "__main__":
    main()


