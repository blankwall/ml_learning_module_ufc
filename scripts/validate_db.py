import argparse
import sys
from pathlib import Path
from typing import Optional, List

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

# Ensure project root is on sys.path so we can import project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight
from features.fighter_features import FighterFeatureExtractor


def compute_record_from_history(history: pd.DataFrame) -> dict:
    """Compute wins/losses/draws/no_contests from a fighter's fight history DataFrame."""
    if history.empty:
        return {"wins": 0, "losses": 0, "draws": 0, "no_contests": 0, "total_fights": 0}

    wins = (history["result"] == "win").sum()
    losses = (history["result"] == "loss").sum()
    draws = (history["result"] == "draw").sum()
    ncs = (history["result"] == "nc").sum()
    total = len(history)

    return {
        "wins": int(wins),
        "losses": int(losses),
        "draws": int(draws),
        "no_contests": int(ncs),
        "total_fights": int(total),
    }


def validate_fighter_records(session: Session, limit: int = 50, min_fights: int = 1) -> None:
    """
    Validate Fighter.wins/losses/draws/no_contests against fight history derived from Fight rows.

    Prints any fighters where the derived record does not match the stored record.
    """
    extractor = FighterFeatureExtractor(session)

    fighters: List[Fighter] = (
        session.query(Fighter)
        .order_by(Fighter.id)
        .limit(limit)
        .all()
    )

    logger.info(f"Validating basic records for up to {len(fighters)} fighters...")

    mismatches = []

    for fighter in fighters:
        history = extractor._get_fight_history(fighter.id, as_of_date=None)
        if len(history) < min_fights:
            continue

        derived = compute_record_from_history(history)

        stored_total = (fighter.wins or 0) + (fighter.losses or 0) + (fighter.draws or 0) + (fighter.no_contests or 0)

        delta = {
            "id": fighter.id,
            "name": fighter.name,
            "stored_wins": fighter.wins or 0,
            "stored_losses": fighter.losses or 0,
            "stored_draws": fighter.draws or 0,
            "stored_no_contests": fighter.no_contests or 0,
            "stored_total": stored_total,
            "derived_wins": derived["wins"],
            "derived_losses": derived["losses"],
            "derived_draws": derived["draws"],
            "derived_no_contests": derived["no_contests"],
            "derived_total": derived["total_fights"],
        }

        if (
            delta["stored_wins"] != delta["derived_wins"]
            or delta["stored_losses"] != delta["derived_losses"]
            or delta["stored_draws"] != delta["derived_draws"]
            or delta["stored_no_contests"] != delta["derived_no_contests"]
        ):
            mismatches.append(delta)

    if not mismatches:
        logger.success("No record mismatches found for sampled fighters.")
        return

    logger.warning(f"Found {len(mismatches)} fighters with record mismatches (sampled).")
    df = pd.DataFrame(mismatches)
    logger.info("Sample of mismatches (up to 20 rows):")
    logger.info("\n" + df.head(20).to_string(index=False))


def validate_fight_results(session: Session, limit: int = 50) -> None:
    """
    Basic sanity check on Fight.result vs winner_id.

    Ensures that when result == 'fighter_1' / 'fighter_2', winner_id matches the corresponding fighter.
    """
    fights: List[Fight] = (
        session.query(Fight)
        .order_by(Fight.id)
        .limit(limit)
        .all()
    )

    logger.info(f"Validating fight results for up to {len(fights)} fights...")
    issues = []

    for fight in fights:
        if fight.result not in ("fighter_1", "fighter_2", "draw", "no_contest"):
            issues.append(
                {
                    "fight_id": fight.id,
                    "fight_str": repr(fight),
                    "issue": f"Unexpected result value: {fight.result}",
                }
            )
            continue

        if fight.result == "fighter_1" and fight.winner_id != fight.fighter_1_id:
            issues.append(
                {
                    "fight_id": fight.id,
                    "fight_str": repr(fight),
                    "issue": "result == 'fighter_1' but winner_id != fighter_1_id",
                }
            )
        elif fight.result == "fighter_2" and fight.winner_id != fight.fighter_2_id:
            issues.append(
                {
                    "fight_id": fight.id,
                    "fight_str": repr(fight),
                    "issue": "result == 'fighter_2' but winner_id != fighter_2_id",
                }
            )

    if not issues:
        logger.success("No fight result inconsistencies found for sampled fights.")
        return

    logger.warning(f"Found {len(issues)} potential fight result issues (sampled).")
    df = pd.DataFrame(issues)
    logger.info("Sample of issues (up to 20 rows):")
    logger.info("\n" + df.head(20).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Validate fighter and fight data in the database")
    parser.add_argument(
        "--config-path",
        type=str,
        default="config/config.yaml",
        help="Path to config file used by DatabaseManager",
    )
    parser.add_argument(
        "--fighter-limit",
        type=int,
        default=50,
        help="Max number of fighters to validate",
    )
    parser.add_argument(
        "--fighter-min-fights",
        type=int,
        default=1,
        help="Minimum number of fights for a fighter to be included in validation",
    )
    parser.add_argument(
        "--fight-limit",
        type=int,
        default=50,
        help="Max number of fights to validate",
    )

    args = parser.parse_args()

    db = DatabaseManager(args.config_path)
    session = db.get_session()

    try:
        validate_fighter_records(
            session,
            limit=args.fighter_limit,
            min_fights=args.fighter_min_fights,
        )

        validate_fight_results(
            session,
            limit=args.fight_limit,
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()


