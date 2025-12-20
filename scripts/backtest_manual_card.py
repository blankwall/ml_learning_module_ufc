#!/usr/bin/env python3
"""
Backtest a small manually-entered card (your format) using the model.

Input CSV columns:
  - event
  - fight_date
  - fighter_1_name
  - fighter_2_name
  - fighter_1_odds  (American)
  - fighter_2_odds  (American)
  - F1 Wins         (optional: 1 if fighter_1 won, 0 if fighter_1 lost)

What it does:
  1) Runs model predictions for each row (via existing add_model_predictions)
  2) Computes EV for betting fighter_1 vs fighter_2
  3) Places at most ONE bet per fight (the side with higher EV) if EV > min_ev
  4) If results are present, computes realized ROI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Ensure project root on sys.path so `scripts.*` imports work when run as a file.
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.export_predictions_to_excel import add_model_predictions  # type: ignore


def american_payout_per_unit(odds: float) -> float:
    o = float(odds)
    if o == 0:
        return float("nan")
    if o > 0:
        return o / 100.0
    return 100.0 / (-o)


def expected_profit_per_unit(p_win: float, odds: float) -> float:
    b = american_payout_per_unit(odds)
    if not np.isfinite(b):
        return float("nan")
    p = float(p_win)
    return p * b - (1.0 - p)

def american_to_implied_prob(odds: float) -> float:
    o = float(odds)
    if o == 0:
        return float("nan")
    if o < 0:
        return (-o) / ((-o) + 100.0)
    return 100.0 / (o + 100.0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest a manually-entered card CSV")
    ap.add_argument("--input", required=True, help="Path to manual card CSV")
    ap.add_argument("--model-name", default="xgboost_model", help="Model name (default: xgboost_model)")
    ap.add_argument(
        "--strategy",
        type=str,
        default="best_ev",
        choices=["best_ev", "winner", "winner_underdog_only"],
        help=(
            "Betting rule: "
            "best_ev = bet the side with higher EV if EV > min_ev; "
            "winner = bet the model-predicted winner (p>=0.5) regardless of EV; "
            "winner_underdog_only = only bet when the model-predicted winner is also the underdog."
        ),
    )
    ap.add_argument("--min-ev", type=float, default=0.08, help="Only bet if best-side EV per 1 unit > this")
    ap.add_argument("--flat-stake", type=float, default=1.0, help="Stake per bet (units)")
    ap.add_argument(
        "--output-csv",
        default="",
        help="Optional: write enriched rows (model probs, EVs, bet decision, profit) to CSV",
    )
    args = ap.parse_args()

    in_path = Path(args.input)
    df_in = pd.read_csv(in_path)
    # Preserve results column if present; add_model_predictions drops extra cols.
    f1_wins_series = df_in["F1 Wins"] if "F1 Wins" in df_in.columns else None

    # Add model probs + edges (already implemented in repo)
    df = add_model_predictions(df_in, model_name=args.model_name)

    # add_model_predictions outputs model_p_f1_pct / model_p_f2_pct
    if "model_p_f1_pct" not in df.columns:
        raise ValueError("Expected add_model_predictions to output 'model_p_f1_pct'")

    if f1_wins_series is not None and "F1 Wins" not in df.columns:
        df["F1 Wins"] = f1_wins_series.values

    df["p_f1"] = df["model_p_f1_pct"].astype(float) / 100.0
    df["p_f2"] = df["model_p_f2_pct"].astype(float) / 100.0

    df["ev_f1"] = df.apply(lambda r: expected_profit_per_unit(r["p_f1"], r["fighter_1_odds"]), axis=1)
    df["ev_f2"] = df.apply(lambda r: expected_profit_per_unit(r["p_f2"], r["fighter_2_odds"]), axis=1)

    strategy = str(args.strategy).strip().lower()

    if strategy == "best_ev":
        df["bet_side"] = np.where(df["ev_f1"] >= df["ev_f2"], "fighter_1", "fighter_2")
        df["bet_ev"] = np.where(df["bet_side"].eq("fighter_1"), df["ev_f1"], df["ev_f2"])
        df["place_bet"] = df["bet_ev"] > float(args.min_ev)
    elif strategy in {"winner", "winner_underdog_only"}:
        df["bet_side"] = np.where(df["p_f1"] >= 0.5, "fighter_1", "fighter_2")
        df["bet_ev"] = np.where(df["bet_side"].eq("fighter_1"), df["ev_f1"], df["ev_f2"])
        df["place_bet"] = True

        if strategy == "winner_underdog_only":
            imp1 = df["fighter_1_odds"].astype(float).apply(american_to_implied_prob)
            imp2 = df["fighter_2_odds"].astype(float).apply(american_to_implied_prob)
            # Underdog = lower implied probability
            f1_is_underdog = imp1 < imp2
            winner_is_underdog = np.where(df["bet_side"].eq("fighter_1"), f1_is_underdog, ~f1_is_underdog)
            df["place_bet"] = winner_is_underdog.astype(bool)
    else:
        raise ValueError(f"Unknown strategy: {args.strategy}")

    df["bet_name"] = np.where(df["bet_side"].eq("fighter_1"), df["fighter_1_name"], df["fighter_2_name"])
    df["bet_odds"] = np.where(df["bet_side"].eq("fighter_1"), df["fighter_1_odds"], df["fighter_2_odds"])
    df["bet_p"] = np.where(df["bet_side"].eq("fighter_1"), df["p_f1"], df["p_f2"])

    df["stake"] = np.where(df["place_bet"], float(args.flat_stake), 0.0)

    # Realized P/L if results are present
    profit = np.full(len(df), np.nan, dtype=float)
    if "F1 Wins" in df.columns:
        # bet wins if:
        # - betting fighter_1 and F1 Wins == 1
        # - betting fighter_2 and F1 Wins == 0
        f1_wins = pd.to_numeric(df["F1 Wins"], errors="coerce")
        has_result = f1_wins.isin([0, 1])

        payout = df["bet_odds"].astype(float).apply(american_payout_per_unit).values
        won = (
            (df["bet_side"].eq("fighter_1") & (f1_wins == 1))
            | (df["bet_side"].eq("fighter_2") & (f1_wins == 0))
        )

        stake = df["stake"].astype(float).values
        profit_calc = np.where(won, stake * payout, -stake)
        profit = np.where(has_result, profit_calc, np.nan)

    df["profit"] = profit

    # Summary
    bets = df[df["place_bet"]].copy()
    print("\n" + "=" * 80)
    if strategy == "best_ev":
        rule = f"best_ev (min_ev={args.min_ev:.3f})"
    elif strategy == "winner":
        rule = "winner (bet predicted winner)"
    else:
        rule = "winner_underdog_only (predicted winner + underdog)"
    print(f"MANUAL CARD BACKTEST | model={args.model_name} | strategy={rule} | stake={args.flat_stake:g}u")
    print("=" * 80)
    print(f"rows:      {len(df)}")
    print(f"bets:      {len(bets)}")

    if len(bets):
        show_cols = [
            "fighter_1_name",
            "fighter_2_name",
            "fighter_1_odds",
            "fighter_2_odds",
            "model_p_f1_pct",
            "model_p_f2_pct",
            "ev_f1",
            "ev_f2",
            "bet_name",
            "bet_side",
            "bet_ev",
        ]
        if "F1 Wins" in df.columns:
            show_cols.append("profit")
        print(bets[show_cols].to_string(index=False))

    if "F1 Wins" in df.columns:
        realized = bets.dropna(subset=["profit"])
        staked = float(realized["stake"].sum()) if len(realized) else 0.0
        prof = float(realized["profit"].sum()) if len(realized) else 0.0
        roi = (prof / staked) if staked else float("nan")
        print("\nRealized:")
        print(f"  staked:  {staked:.3f}u")
        print(f"  profit:  {prof:.3f}u")
        print(f"  ROI:     {roi:.3%}" if np.isfinite(roi) else "  ROI:     N/A")

    if args.output_csv:
        out_path = Path(args.output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main()


