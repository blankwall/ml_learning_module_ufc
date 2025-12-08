"""
new_validate_fight_details_results.py
-------------------------------------

Lightweight validator focused ONLY on the internal consistency of
``data/processed/fight_details.json``.

Goal
----
- For every fight where a winner is specified as ``"fighter_1"`` or
  ``"fighter_2"``, ensure:
  - The winner's ``fighter_X_result`` is a win.
  - The loser's ``fighter_X_result`` is a loss.

Draws, no-contests and other special outcomes are ignored by this script to
avoid noisy failures; the intent is a clean, targeted sanity check that
winner/loser flags line up with the declared winner.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_FIGHT_DETAILS_PATH = Path("data/processed/fight_details.json")


def load_json_array(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected top-level JSON array in {path}, got {type(data)!r}")
    return data


def normalize_result_flag(raw: str | None) -> str:
    """Normalize fighter_1_result / fighter_2_result flags."""
    if raw is None:
        return "unknown"
    text = raw.strip().upper()
    if text in {"W", "WIN"}:
        return "win"
    if text in {"L", "LOSS"}:
        return "loss"
    if text in {"D", "DRAW"}:
        return "draw"
    if text.startswith("N"):  # "NC", "N/C", etc.
        return "nc"
    return "unknown"


def normalize_winner(raw: str | None) -> str:
    """Normalize winner field from fight_details."""
    if raw is None:
        return "unknown"
    text = raw.strip().lower()
    if text == "fighter_1":
        return "fighter_1"
    if text == "fighter_2":
        return "fighter_2"
    if text in {"draw", "d"}:
        return "draw"
    if text in {"nc", "n/c", "no contest", "no-contest"}:
        return "nc"
    return "unknown"


def validate_fight_details(path: Path) -> bool:
    """Validate winner/loser flags inside fight_details.json."""
    if not path.exists():
        print(f"[ERROR] fight_details file does not exist: {path}")
        return False

    fights: List[Dict[str, Any]] = list(load_json_array(path))
    total_checked = 0
    errors = 0

    for fight in fights:
        fight_id = fight.get("fight_id", "<unknown>")
        event_name = fight.get("event_name", "<unknown event>")
        f1_name = fight.get("fighter_1_name", "<unknown>")
        f2_name = fight.get("fighter_2_name", "<unknown>")

        winner_flag = normalize_winner(fight.get("winner"))
        f1_result = normalize_result_flag(fight.get("fighter_1_result"))
        f2_result = normalize_result_flag(fight.get("fighter_2_result"))

        # Only validate bouts where a winner is explicitly specified.
        if winner_flag not in {"fighter_1", "fighter_2"}:
            continue

        total_checked += 1

        if winner_flag == "fighter_1":
            expected_f1 = "win"
            expected_f2 = "loss"
        else:  # winner_flag == "fighter_2"
            expected_f1 = "loss"
            expected_f2 = "win"

        if f1_result != expected_f1 or f2_result != expected_f2:
            print(
                f"[ERROR] Inconsistent results for fight_id={fight_id!r} "
                f"({event_name}): "
                f"winner={winner_flag!r}, "
                f"fighter_1_name={f1_name!r}, fighter_1_result={fight.get('fighter_1_result')!r}, "
                f"fighter_2_name={f2_name!r}, fighter_2_result={fight.get('fighter_2_result')!r}."
            )
            errors += 1

    print(
        f"[SUMMARY] Checked {total_checked} fights with explicit winners in "
        f"{path}. Errors: {errors}."
    )

    if errors == 0:
        print("[DONE] fight_details winner/loser flags are internally consistent.")
        return True

    print("[DONE] Inconsistencies found in fight_details winner/loser flags.")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that winner / loser flags inside data/processed/fight_details.json "
            "are internally consistent."
        ),
    )
    parser.add_argument(
        "--fight-details-path",
        type=Path,
        default=DEFAULT_FIGHT_DETAILS_PATH,
        help="Path to fight_details.json (default: data/processed/fight_details.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ok = validate_fight_details(args.fight_details_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()


