#!/usr/bin/env python3
"""
Compare two evaluation runs (backing CSVs used by the HTML reports).

This script matches the HTML report's accuracy logic:
- Filter to event_year >= min_year
- Deduplicate fights (each fight appears twice in eval_data_*.csv, once per perspective)
  by creating a stable key based on event_id + sorted fighter IDs
- Evaluate correctness on the winner-perspective row (target=1) using:
    correct = (model_prob_f1 >= 0.5)

It then reports which fights flipped from correct->wrong (and vice versa), and writes a
full diff CSV for deeper inspection.

Example:
  python3 scripts/compare_eval_reports.py \
    --old reports/eval_data_20251213_073515.csv \
    --new reports2/eval_data_20251215_091129.csv \
    --out reports2/diff_20251213_073515_vs_20251215_091129.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import pandas as pd


def _dedup_for_html(df: pd.DataFrame, min_year: int) -> pd.DataFrame:
    """Match `evaluation/generate_html_report.py` fight dedupe behavior."""
    df = df[df["event_year"] >= min_year].copy()

    if "fighter_1_id" not in df.columns or "fighter_2_id" not in df.columns:
        raise ValueError("Expected fighter_1_id and fighter_2_id columns in eval CSV.")

    df["fight_key_html"] = df.apply(
        lambda r: f"{int(r['event_id'])}_{min(int(r['fighter_1_id']), int(r['fighter_2_id']))}_{max(int(r['fighter_1_id']), int(r['fighter_2_id']))}",
        axis=1,
    )

    # Winner perspective row first (target=1), then keep one row per fight
    df = df.sort_values("target", ascending=False)
    df = df.drop_duplicates(subset=["fight_key_html"], keep="first")

    # HTML correctness
    df["model_pick"] = (df["model_prob_f1"] >= 0.5).astype(int)
    df["correct"] = (df["model_pick"] == df["target"]).astype(int)

    return df


def _summarize(df: pd.DataFrame) -> Tuple[int, int, float]:
    total = int(len(df))
    correct = int(df["correct"].sum())
    acc = float(correct / total) if total else float("nan")
    return total, correct, acc


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two UFC eval_data CSVs.")
    parser.add_argument("--old", type=str, required=True, help="Path to old eval_data_*.csv")
    parser.add_argument("--new", type=str, required=True, help="Path to new eval_data_*.csv")
    parser.add_argument("--min-year", type=int, default=2025, help="Minimum event year to include (default: 2025)")
    parser.add_argument("--out", type=str, default="", help="Optional output path for full diff CSV")
    args = parser.parse_args()

    old_path = Path(args.old)
    new_path = Path(args.new)
    if not old_path.exists():
        raise FileNotFoundError(old_path)
    if not new_path.exists():
        raise FileNotFoundError(new_path)

    old_raw = pd.read_csv(old_path)
    new_raw = pd.read_csv(new_path)

    old = _dedup_for_html(old_raw, min_year=args.min_year)
    new = _dedup_for_html(new_raw, min_year=args.min_year)

    old_total, old_correct, old_acc = _summarize(old)
    new_total, new_correct, new_acc = _summarize(new)

    print(f"[OLD] fights={old_total} correct={old_correct} accuracy={old_acc:.3%}  ({old_path})")
    print(f"[NEW] fights={new_total} correct={new_correct} accuracy={new_acc:.3%}  ({new_path})")
    print(f"[Δ]   accuracy={(new_acc - old_acc):+.3%}  (net correct change: {new_correct - old_correct:+d})")

    merged = old.merge(new, on="fight_key_html", suffixes=("_old", "_new"), how="inner")
    if merged.empty:
        raise ValueError("No overlapping fights between the two runs after dedupe.")

    # Winner-perspective rows should be target=1 in both runs (by construction)
    merged["old_correct"] = (merged["model_prob_f1_old"] >= 0.5).astype(int)
    merged["new_correct"] = (merged["model_prob_f1_new"] >= 0.5).astype(int)
    merged["delta_prob"] = merged["model_prob_f1_new"] - merged["model_prob_f1_old"]

    merged["predicted_winner_old"] = merged.apply(
        lambda r: r["f1_name_old"] if r["model_prob_f1_old"] >= 0.5 else r["f2_name_old"], axis=1
    )
    merged["predicted_winner_new"] = merged.apply(
        lambda r: r["f1_name_new"] if r["model_prob_f1_new"] >= 0.5 else r["f2_name_new"], axis=1
    )

    lost = merged[(merged["old_correct"] == 1) & (merged["new_correct"] == 0)].copy()
    gained = merged[(merged["old_correct"] == 0) & (merged["new_correct"] == 1)].copy()

    print(f"\nLost (correct→wrong): {len(lost)} fights")
    print(f"Gained (wrong→correct): {len(gained)} fights")

    def _print_flips(title: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df = df.sort_values("delta_prob", ascending=(title.startswith("Lost")))
        cols = [
            "event_date_old",
            "fight_key_html",
            "f1_name_old",
            "f2_name_old",
            "model_prob_f1_old",
            "model_prob_f1_new",
            "delta_prob",
            "predicted_winner_old",
            "predicted_winner_new",
            "fighter1_odds_old",
            "fighter2_odds_old",
        ]
        cols = [c for c in cols if c in df.columns]
        print(f"\n=== {title} ===")
        print(df[cols].to_string(index=False))

    _print_flips("Lost", lost)
    _print_flips("Gained", gained)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        merged.sort_values(["old_correct", "new_correct", "delta_prob"]).to_csv(out_path, index=False)
        print(f"\nWrote diff CSV: {out_path}")


if __name__ == "__main__":
    main()


