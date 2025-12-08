import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from database.schema import Fight


def load_fight_details(details_path: str) -> Dict[str, dict]:
    """Load fight_details.json and index by fight_id."""
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


def compare_fight_to_json(fight: Fight, details: dict) -> Optional[dict]:
    """
    Compare a DB Fight row to its fight_details.json entry.

    Returns a dict describing any mismatch, or None if everything looks consistent.
    """
    db_f1 = fight.fighter_1.name if fight.fighter_1 else None
    db_f2 = fight.fighter_2.name if fight.fighter_2 else None

    json_f1 = details.get("fighter_1_name")
    json_f2 = details.get("fighter_2_name")
    json_winner_key = details.get("winner")  # 'fighter_1' or 'fighter_2' or None

    # Determine mapping between JSON fighter_1/2 and DB fighter_1/2
    if db_f1 == json_f1 and db_f2 == json_f2:
        name_alignment = "same_order"
        json_f1_maps_to_db = "fighter_1"
        json_f2_maps_to_db = "fighter_2"
    elif db_f1 == json_f2 and db_f2 == json_f1:
        name_alignment = "swapped_order"
        json_f1_maps_to_db = "fighter_2"
        json_f2_maps_to_db = "fighter_1"
    else:
        # Names don't match cleanly; flag but don't try to infer correctness
        return {
            "fight_id": fight.fight_id,
            "event_date": fight.event.date if fight.event else None,
            "db_f1": db_f1,
            "db_f2": db_f2,
            "json_f1": json_f1,
            "json_f2": json_f2,
            "name_alignment": "name_mismatch",
            "db_result": fight.result,
            "db_winner_id": fight.winner_id,
            "expected_db_result": None,
            "expected_winner_side": None,
            "issue": "Name mismatch between DB and JSON",
        }

    # Determine expected winner in DB terms, based on JSON winner key and alignment
    expected_db_result: Optional[str] = None
    expected_winner_side: Optional[str] = None

    if json_winner_key in ("fighter_1", "fighter_2"):
        # Map JSON winner side to DB side
        if json_winner_key == "fighter_1":
            expected_db_result = json_f1_maps_to_db
        else:
            expected_db_result = json_f2_maps_to_db
        expected_winner_side = expected_db_result

    # If JSON has no winner (draw/NC), expected_db_result stays None

    # Now compare with DB
    issues: List[str] = []

    # 1) Check that DB result matches expected_db_result when there is one
    if expected_db_result is not None:
        if fight.result != expected_db_result:
            issues.append(
                f"DB result '{fight.result}' != expected '{expected_db_result}' "
                f"(alignment={name_alignment})"
            )

        # 2) Check winner_id vs expected side
        if expected_winner_side == "fighter_1" and fight.winner_id != fight.fighter_1_id:
            issues.append("winner_id should be fighter_1_id based on JSON winner")
        elif expected_winner_side == "fighter_2" and fight.winner_id != fight.fighter_2_id:
            issues.append("winner_id should be fighter_2_id based on JSON winner")

    # If JSON winner is None, but DB has a fighter_1/fighter_2 result, that's suspicious too
    else:
        if fight.result in ("fighter_1", "fighter_2"):
            issues.append(
                "JSON has no explicit winner, but DB result is a winner (fighter_1/fighter_2)"
            )

    if not issues:
        return None

    return {
        "fight_id": fight.fight_id,
        "event_date": fight.event.date if fight.event else None,
        "db_f1": db_f1,
        "db_f2": db_f2,
        "json_f1": json_f1,
        "json_f2": json_f2,
        "name_alignment": name_alignment,
        "db_result": fight.result,
        "db_winner_id": fight.winner_id,
        "expected_db_result": expected_db_result,
        "expected_winner_side": expected_winner_side,
        "issue": " | ".join(issues),
    }


def validate_fights_against_json(
    config_path: str,
    fight_details_path: str,
    limit: Optional[int] = None,
) -> None:
    """Validate DB Fight records against fight_details.json."""
    db = DatabaseManager(config_path)
    session = db.get_session()

    details_by_id = load_fight_details(fight_details_path)

    try:
        query = session.query(Fight)
        if limit:
            query = query.limit(limit)
        fights = query.all()

        logger.info(f"Validating up to {len(fights)} fights against {fight_details_path}...")

        mismatches: List[dict] = []

        for fight in fights:
            if not fight.fight_id:
                continue
            details = details_by_id.get(fight.fight_id)
            if not details:
                continue

            result = compare_fight_to_json(fight, details)
            if result is not None:
                mismatches.append(result)

        if not mismatches:
            logger.success("No mismatches found between DB fights and fight_details.json (for sampled fights).")
            return

        df = pd.DataFrame(mismatches)
        logger.warning(f"Found {len(df)} mismatched fights (sampled).")
        logger.info("Sample of mismatches (up to 20 rows):")
        logger.info("\n" + df.head(20).to_string(index=False))

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Validate DB Fight records against fight_details.json"
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
        "--limit",
        type=int,
        default=500,
        help="Max number of fights to validate (for speed); 0 means all",
    )

    args = parser.parse_args()
    limit = args.limit if args.limit and args.limit > 0 else None

    validate_fights_against_json(
        config_path=args.config_path,
        fight_details_path=args.fight_details_path,
        limit=limit,
    )


if __name__ == "__main__":
    main()


