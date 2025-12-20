#!/usr/bin/env python3
"""
Compare two fighters' stats from the database.

This is a debugging / analysis utility to help design and interpret features.
Given two fighter names, it:
  - Finds the best matching fighters in the DB.
  - Shows basic physical and record info.
  - Shows a curated set of per-fighter features from FighterFeatureExtractor.
  - Prints the difference (fighter_1 - fighter_2) for those features.
"""

import sys
from pathlib import Path

# Ensure project root is on the path (same pattern as xgboost_predict.py)
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from typing import Optional, Dict, List

from loguru import logger

from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.fighter_features import FighterFeatureExtractor


def _find_fighter_by_name(session, name: str) -> Optional[Fighter]:
    """
    Find a fighter by (partial, case-insensitive) name.
    Returns the first match, logging if multiple are found.
    """
    query = session.query(Fighter).filter(Fighter.name.ilike(f"%{name}%"))
    matches: List[Fighter] = query.all()

    if not matches:
        logger.error(f"No fighter found matching name: '{name}'")
        return None

    if len(matches) > 1:
        logger.warning(
            f"Multiple fighters matched '{name}'; using the first. "
            f"Candidates: {[f.name for f in matches[:5]]}"
        )

    return matches[0]


def _print_basic_info(f1: Fighter, f2: Fighter) -> None:
    """Print basic physical and record info side-by-side."""
    header = f"{'Attribute':30} | {f1.name:25} | {f2.name:25}"
    print("\n" + "=" * len(header))
    print("BASIC FIGHTER INFO")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    def rec(f: Fighter) -> str:
        return f"{(f.wins or 0)}-{(f.losses or 0)}-{(f.draws or 0)}"

    rows = [
        ("Age", f1.age, f2.age),
        ("Height (cm)", f1.height_cm, f2.height_cm),
        ("Reach (in)", f1.reach_inches, f2.reach_inches),
        ("Weight (lbs)", f1.weight_lbs, f2.weight_lbs),
        ("Stance", f1.stance, f2.stance),
        ("Official record (W-L-D)", rec(f1), rec(f2)),
        ("Sig. strikes landed / min", f1.sig_strikes_landed_per_min, f2.sig_strikes_landed_per_min),
        ("Sig. strikes absorbed / min", f1.sig_strikes_absorbed_per_min, f2.sig_strikes_absorbed_per_min),
        ("Striking defense", f1.striking_defense, f2.striking_defense),
        ("Takedown avg / 15 min", f1.takedown_avg_per_15min, f2.takedown_avg_per_15min),
        ("Takedown defense", f1.takedown_defense, f2.takedown_defense),
        ("Submission avg / 15 min", f1.submission_avg_per_15min, f2.submission_avg_per_15min),
    ]

    for label, v1, v2 in rows:
        print(f"{label:30} | {str(v1):25} | {str(v2):25}")


def _print_feature_comparison(
    f1_name: str,
    f2_name: str,
    f1_feats: Dict,
    f2_feats: Dict,
) -> None:
    """
    Print a curated subset of per-fighter features and their differences.
    """
    # Keys to highlight – focused on form, decline, and schedule.
    feature_keys = [
        # Volume / summary
        "total_fights",
        "wins",
        "losses",
        "draws",
        # Recency + momentum
        "win_rate_last_3",
        "win_rate_last_5",
        "finish_rate_last_3",
        "finish_rate_last_5",
        "current_win_streak",
        "current_loss_streak",
        "fights_in_last_year",
        "days_since_last_fight",
        # Decline / slump specific
        "fights_since_last_win",
        "years_since_last_win",
        "has_ever_won",
        "losses_since_last_win",
        "decision_losses_since_last_win",
        "finish_losses_since_last_win",
        "recent_vs_career_win_rate",
        # Recent detailed stats
        "recent_sig_strike_diff_last_3",
        "recent_knockdown_diff_last_3",
        "recent_control_time_diff_last_3",
        # Opponent quality
        "avg_opponent_win_rate",
        "avg_beaten_opponent_win_rate",
        "avg_lost_to_opponent_win_rate",
        "opponent_quality_score",
    ]

    header = f"{'Feature':35} | {f1_name:15} | {f2_name:15} | {'(f1 - f2)':>10}"
    print("\n" + "=" * len(header))
    print("DERIVED FIGHTER FEATURES (CURATED)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for key in feature_keys:
        v1 = f1_feats.get(key, 0)
        v2 = f2_feats.get(key, 0)

        # Try numeric diff where possible
        diff: Optional[float]
        try:
            diff = float(v1) - float(v2)
        except (TypeError, ValueError):
            diff = None

        diff_str = f"{diff:.3f}" if diff is not None else "-"
        print(
            f"{key:35} | {str(v1):15} | {str(v2):15} | {diff_str:>10}"
        )


def compare_fighters(fighter_1_name: str, fighter_2_name: str) -> None:
    """Main comparison routine."""
    db = DatabaseManager()
    session = db.get_session()

    try:
        f1 = _find_fighter_by_name(session, fighter_1_name)
        f2 = _find_fighter_by_name(session, fighter_2_name)

        if not f1 or not f2:
            return

        logger.info(f"Matched fighters: '{f1.name}' (id={f1.id}) vs '{f2.name}' (id={f2.id})")

        # Print raw / basic info
        _print_basic_info(f1, f2)

        # Extract derived per-fighter features as of "now"
        extractor = FighterFeatureExtractor(session)
        f1_features = extractor.extract_features(f1.id)
        f2_features = extractor.extract_features(f2.id)

        _print_feature_comparison(f1.name, f2.name, f1_features, f2_features)

        print("\nDone.\n")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Compare two fighters' stats and derived features from the database."
    )
    parser.add_argument("--fighter-1", type=str, required=True, help="First fighter name")
    parser.add_argument("--fighter-2", type=str, required=True, help="Second fighter name")

    args = parser.parse_args()
    compare_fighters(args.fighter_1, args.fighter_2)


if __name__ == "__main__":
    main()


