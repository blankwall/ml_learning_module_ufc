#!/usr/bin/env python3
"""
Build upcoming_fights CSV from a raw odds JSON file (e.g. UFC 323).

Usage example:

    python scripts/build_upcoming_from_raw_odds.py \
        --raw-file data/raw/ufc323.json \
        --output data/predictions/upcoming_fights_ufc323.csv

The output CSV is compatible with `export_predictions_to_excel.py`:
  - event
  - fight_date
  - fighter_1_name
  - fighter_2_name
  - fighter_1_odds
  - fighter_2_odds
  - is_title_fight
"""

import json
from pathlib import Path
from typing import List, Dict

import pandas as pd
from loguru import logger


def parse_event_odd_file(raw_path: Path) -> pd.DataFrame:
    """Parse the raw JSON odds file and return a fights DataFrame."""
    with raw_path.open("r") as f:
        data = json.load(f)

    event_node = data.get("data", {}).get("eventOfferTable", {})
    event_name = event_node.get("name", "Unknown Event")

    fights_node = event_node.get("fightOffers", {})
    edges: List[Dict] = fights_node.get("edges", [])

    rows: List[Dict] = []

    for edge in edges:
        node = edge.get("node", {})
        if not node or node.get("isCancelled"):
            continue

        f1 = node.get("fighter1", {}) or {}
        f2 = node.get("fighter2", {}) or {}

        f1_name = f"{f1.get('firstName', '').strip()} {f1.get('lastName', '').strip()}".strip()
        f2_name = f"{f2.get('firstName', '').strip()} {f2.get('lastName', '').strip()}".strip()

        # Use bestOdds1 / bestOdds2 as simple representative odds
        f1_odds = node.get("bestOdds1", None)
        f2_odds = node.get("bestOdds2", None)

        if not f1_name or not f2_name:
            logger.warning(f"Skipping fight with missing names: {node.get('slug')}")
            continue

        rows.append(
            {
                "event": event_name,
                "fight_date": "",  # can be filled manually in Excel
                "fighter_1_name": f1_name,
                "fighter_2_name": f2_name,
                "fighter_1_odds": f1_odds,
                "fighter_2_odds": f2_odds,
                # Title-fight flag can be edited manually later if needed
                "is_title_fight": 0,
            }
        )

    df = pd.DataFrame(rows)
    return df


def build_upcoming_csv(
    raw_file: str = "data/raw/ufc323.json",
    output: str = "data/predictions/upcoming_fights_ufc323.csv",
) -> Path:
    """High-level helper: read raw odds JSON and write an upcoming_fights CSV."""
    raw_path = Path(raw_file)
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw odds file not found: {raw_path}")

    logger.info(f"Parsing raw odds from {raw_path} ...")
    df = parse_event_odd_file(raw_path)

    logger.info(f"Writing {len(df)} fights to {out_path} ...")
    df.to_csv(out_path, index=False)
    logger.success(f"Wrote upcoming fights CSV to {out_path}")
    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Build upcoming_fights CSV from raw odds JSON"
    )
    parser.add_argument(
        "--raw-file",
        type=str,
        default="data/raw/ufc323.json",
        help="Path to raw odds JSON (e.g. data/raw/ufc323.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/predictions/upcoming_fights_ufc323.csv",
        help="Path to output CSV",
    )

    args = parser.parse_args()
    build_upcoming_csv(args.raw_file, args.output)


if __name__ == "__main__":
    main()


