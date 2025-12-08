#!/usr/bin/env python3
"""
Fix Fight Results - Correct the Fight.result and winner_id fields using fight_details.json

The original event scraper could mark all fights as fighter_1 wins. This script uses
fight_details.json (which has the true winner) and robust name alignment to fix it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from loguru import logger

from database.db_manager import DatabaseManager
from database.schema import Fight


def _load_fight_details(path: str = "data/processed/fight_details.json"):
    """Load fight_details.json indexed by fight_id."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"fight_details file not found: {path}")
    with p.open("r") as f:
        data = json.load(f)
    details_by_id = {d.get("fight_id"): d for d in data if d.get("fight_id")}
    logger.info(f"Loaded {len(details_by_id)} fight_details entries from {path}")
    return details_by_id


def _determine_expected_from_details(fight: Fight, details: dict):
    """
    Given a DB Fight and matching fight_details entry, determine:
      - how names align (same_order / swapped_order)
      - what Fight.result and winner_id *should* be

    Returns dict with keys: alignment, expected_result, expected_winner_id
    or None if ambiguous.
    """
    db_f1 = fight.fighter_1.name if fight.fighter_1 else None
    db_f2 = fight.fighter_2.name if fight.fighter_2 else None

    json_f1 = details.get("fighter_1_name")
    json_f2 = details.get("fighter_2_name")
    json_r1 = details.get("fighter_1_result")
    json_r2 = details.get("fighter_2_result")

    # Determine alignment between JSON and DB fighters
    if db_f1 == json_f1 and db_f2 == json_f2:
        alignment = "same_order"
        json_to_db = {"fighter_1": "fighter_1", "fighter_2": "fighter_2"}
    elif db_f1 == json_f2 and db_f2 == json_f1:
        alignment = "swapped_order"
        json_to_db = {"fighter_1": "fighter_2", "fighter_2": "fighter_1"}
    else:
        # Names don't map cleanly, skip this fight
        logger.debug(
            f"Name mismatch for fight_id={fight.fight_id}: "
            f"DB=({db_f1} vs {db_f2}), JSON=({json_f1} vs {json_f2})"
        )
        return None

    expected_result = None
    expected_winner_id = None

    # Infer from fighter_1_result / fighter_2_result.
    # We explicitly IGNORE the 'winner' field in JSON because it may be unreliable.
    if json_r1 == "W":
        db_side = json_to_db["fighter_1"]
        expected_result = db_side
        expected_winner_id = fight.fighter_1_id if db_side == "fighter_1" else fight.fighter_2_id
    elif json_r2 == "W":
        db_side = json_to_db["fighter_2"]
        expected_result = db_side
        expected_winner_id = fight.fighter_1_id if db_side == "fighter_1" else fight.fighter_2_id
    elif json_r1 == "D" or json_r2 == "D":
        expected_result = "draw"
        expected_winner_id = None
    elif json_r1 in ("NC", "N/C") or json_r2 in ("NC", "N/C"):
        expected_result = "no_contest"
        expected_winner_id = None

    if expected_result is None:
        return None

    return {
        "alignment": alignment,
        "expected_result": expected_result,
        "expected_winner_id": expected_winner_id,
    }


def fix_fight_results():
    """Fix fight results in database using fight_details.json with robust alignment."""
    logger.info("Loading fight details...")
    details_by_id = _load_fight_details("data/processed/fight_details.json")

    logger.info("Connecting to database...")
    db = DatabaseManager()
    session = db.get_session()

    try:
        fights = session.query(Fight).filter(Fight.fight_id.isnot(None)).all()
        logger.info(f"Found {len(fights)} fights in database")

        fixed_count = 0
        fighter_1_wins = 0
        fighter_2_wins = 0

        for i, fight in enumerate(fights, 1):
            if i % 100 == 0:
                logger.info(f"Processing fight {i}/{len(fights)}")

            details = details_by_id.get(fight.fight_id)
            if not details:
                continue

            expected = _determine_expected_from_details(fight, details)
            if expected is None:
                continue

            exp_result = expected["expected_result"]
            exp_winner_id = expected["expected_winner_id"]

            if fight.result != exp_result or fight.winner_id != exp_winner_id:
                old_result = fight.result
                old_winner = fight.winner_id
                fight.result = exp_result
                fight.winner_id = exp_winner_id
                fixed_count += 1
                logger.debug(
                    f"Fixed fight {fight.fight_id}: "
                    f"result {old_result} -> {exp_result}, "
                    f"winner_id {old_winner} -> {exp_winner_id}"
                )

            # Count wins based on updated result
            if fight.result == "fighter_1":
                fighter_1_wins += 1
            elif fight.result == "fighter_2":
                fighter_2_wins += 1

        session.commit()

        logger.success(f"\n{'='*60}")
        logger.success("FIGHT RESULTS FIXED!")
        logger.success(f"{'='*60}")
        logger.success(f"Total fights processed: {len(fights)}")
        logger.success(f"Fights fixed: {fixed_count}")
        logger.success(f"Fighter 1 wins: {fighter_1_wins}")
        logger.success(f"Fighter 2 wins: {fighter_2_wins}")
        logger.success(f"{'='*60}")

    finally:
        session.close()


if __name__ == '__main__':
    fix_fight_results()

