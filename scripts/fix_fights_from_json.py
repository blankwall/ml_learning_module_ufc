import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from database.schema import Fight


def load_fight_details(details_path: str) -> Dict[str, dict]:
    """Load fight_details.json indexed by fight_id."""
    path = Path(details_path)
    if not path.exists():
        raise FileNotFoundError(f"fight_details file not found: {details_path}")

    with path.open("r") as f:
        data = json.load(f)

    indexed: Dict[str, dict] = {}
    for d in data:
        fid = d.get("fight_id")
        if not fid:
            continue
        indexed[fid] = d
    logger.info(f"Loaded {len(indexed)} fight_details entries from {details_path}")
    return indexed


def determine_alignment_and_expected_result(
    fight: Fight, details: dict
) -> Optional[dict]:
    """
    Given a DB Fight and its JSON details, determine:
      - how fighter_1/fighter_2 line up (same_order / swapped)
      - what the DB result and winner_id *should* be.

    Returns a dict with keys:
      alignment, expected_result, expected_winner_id
    or None if we can't safely determine it.
    """
    db_f1 = fight.fighter_1.name if fight.fighter_1 else None
    db_f2 = fight.fighter_2.name if fight.fighter_2 else None

    json_f1 = details.get("fighter_1_name")
    json_f2 = details.get("fighter_2_name")
    json_winner = details.get("winner")  # 'fighter_1', 'fighter_2', or maybe None
    json_r1 = details.get("fighter_1_result")
    json_r2 = details.get("fighter_2_result")

    # Determine name alignment
    if db_f1 == json_f1 and db_f2 == json_f2:
        alignment = "same_order"
        json_to_db = {"fighter_1": "fighter_1", "fighter_2": "fighter_2"}
    elif db_f1 == json_f2 and db_f2 == json_f1:
        alignment = "swapped_order"
        json_to_db = {"fighter_1": "fighter_2", "fighter_2": "fighter_1"}
    else:
        # Names don't match cleanly; don't try to fix automatically
        return None

    expected_result: Optional[str] = None
    expected_winner_id: Optional[int] = None

    # Case 1: JSON explicitly has a winner side
    if json_winner in ("fighter_1", "fighter_2"):
        db_side = json_to_db[json_winner]
        expected_result = db_side
        if db_side == "fighter_1":
            expected_winner_id = fight.fighter_1_id
        else:
            expected_winner_id = fight.fighter_2_id
        return {
            "alignment": alignment,
            "expected_result": expected_result,
            "expected_winner_id": expected_winner_id,
        }

    # Case 2: No explicit winner; infer draw / no-contest if both results match
    if json_r1 and json_r2 and json_r1 == json_r2:
        res = json_r1.upper()
        if res in ("D", "DRAW"):
            expected_result = "draw"
            expected_winner_id = None
        elif res in ("NC", "NO CONTEST"):
            expected_result = "no_contest"
            expected_winner_id = None
        # If something else, we don't know how to map

    if expected_result is None:
        return None

    return {
        "alignment": alignment,
        "expected_result": expected_result,
        "expected_winner_id": expected_winner_id,
    }


def fix_fights_from_json(
    config_path: str,
    fight_details_path: str,
    dry_run: bool = True,
) -> None:
    """
    Use fight_details.json as ground truth to fix Fight.result and Fight.winner_id
    for fights where the DB disagrees but we can confidently align names.
    """
    db = DatabaseManager(config_path)
    session = db.get_session()

    details_by_id = load_fight_details(fight_details_path)

    try:
        fights = session.query(Fight).all()
        logger.info(f"Loaded {len(fights)} fights from DB")

        num_checked = 0
        num_fixed = 0
        num_skipped_no_details = 0
        num_skipped_ambiguous = 0

        for fight in fights:
            if not fight.fight_id:
                num_skipped_no_details += 1
                continue

            details = details_by_id.get(fight.fight_id)
            if not details:
                num_skipped_no_details += 1
                continue

            num_checked += 1

            expected = determine_alignment_and_expected_result(fight, details)
            if expected is None:
                num_skipped_ambiguous += 1
                continue

            exp_result = expected["expected_result"]
            exp_winner_id = expected["expected_winner_id"]

            # If DB already matches expected, nothing to do
            if fight.result == exp_result and fight.winner_id == exp_winner_id:
                continue

            num_fixed += 1
            logger.debug(
                f"Fixing fight {fight.fight_id}: "
                f"{fight.fighter_1.name if fight.fighter_1 else '?'} vs "
                f"{fight.fighter_2.name if fight.fighter_2 else '?'} | "
                f"old result={fight.result}, old winner_id={fight.winner_id} "
                f"-> new result={exp_result}, new winner_id={exp_winner_id}"
            )

            if not dry_run:
                fight.result = exp_result
                fight.winner_id = exp_winner_id

        if not dry_run:
            session.commit()

        logger.info(f"Checked {num_checked} fights with fight_details entries.")
        logger.info(f"Fixed {num_fixed} fights (dry_run={dry_run}).")
        logger.info(f"Skipped (no details / no fight_id): {num_skipped_no_details}")
        logger.info(f"Skipped (ambiguous alignment/outcome): {num_skipped_ambiguous}")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fix Fight.result and winner_id using fight_details.json as ground truth"
    )
    parser.add_argument(
        "--config-path",
        type=str,
        default="config/config.yaml",
        help="Path to config file used by DatabaseManager",
    )
    parser.add_argument(
        "--fight-details-path",
        type=str,
        default="data/processed/fight_details.json",
        help="Path to fight_details.json",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply fixes (otherwise run in dry-run mode)",
    )

    args = parser.parse_args()
    fix_fights_from_json(
        config_path=args.config_path,
        fight_details_path=args.fight_details_path,
        dry_run=not args.apply,
    )


if __name__ == "__main__":
    main()


