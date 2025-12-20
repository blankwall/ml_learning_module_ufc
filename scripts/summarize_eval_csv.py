#!/usr/bin/env python3
"""
summarize_eval_csv.py

Small helper to make eval_data_*.csv easy to read.

It extracts just the key "row perspective" columns:
  - f1_name, f2_name (who is f1 vs f2 on this row)
  - market_prob_f1, model_prob_f1, edge, price_f1
  - plus fight_key / event_date / target for context

Works without pandas to keep it lightweight.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import sqlite3
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Dict, Optional


DEFAULT_COLS: List[str] = [
    "event_date",
    "fight_key",
    "f1_name",
    "f2_name",
    "target",
    "market_prob_f1",
    "model_prob_f1",
    "edge",
    "price_f1",
    "model_name",
]


def _parse_date(s: str) -> Optional[date]:
    """
    Parse an event_date string into a date.

    Expected format in this repo is ISO (YYYY-MM-DD). If parsing fails, returns None.
    """
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        # ISO date
        return date.fromisoformat(s)
    except Exception:
        pass
    try:
        # Some sources might include datetime; keep date part
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def _build_fighter_fight_dates(db_path: Path) -> Dict[int, List[date]]:
    """
    Build mapping:
      fighter_db_id -> sorted list of event dates (one per fight) from our UFC DB.

    Notes:
    - Uses the `fights` + `events` tables (SQLAlchemy schema: `fighters.id` referenced by fights.*_id)
    - Dates are parsed as ISO (YYYY-MM-DD). Unparseable dates are skipped.
    """
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Pull all fights with event dates once (DB has ~8k fights; this is cheap).
    rows = cur.execute(
        """
        SELECT
          f.fighter_1_id AS f1_id,
          f.fighter_2_id AS f2_id,
          e.date AS event_date
        FROM fights f
        JOIN events e ON e.id = f.event_id
        WHERE e.date IS NOT NULL AND e.date != ''
        """
    ).fetchall()

    out: Dict[int, List[date]] = {}
    for r in rows:
        d = _parse_date(r["event_date"])
        if d is None:
            continue
        for fid_key in ("f1_id", "f2_id"):
            fid = r[fid_key]
            if fid is None:
                continue
            try:
                fid_int = int(fid)
            except Exception:
                continue
            out.setdefault(fid_int, []).append(d)

    for fid, ds in out.items():
        ds.sort()
        out[fid] = ds

    con.close()
    return out


def _require_cols(header: Iterable[str], required: Iterable[str]) -> None:
    header_set = set(header)
    missing = [c for c in required if c not in header_set]
    if missing:
        raise SystemExit(f"Missing required columns in eval CSV: {missing}")


def _matches_filters(
    row: Dict[str, str],
    *,
    fight_key: Optional[str],
    contains: Optional[str],
) -> bool:
    if fight_key and row.get("fight_key") != fight_key:
        return False
    if contains:
        needle = contains.lower()
        hay = " ".join(
            [
                str(row.get("fight_key", "")),
                str(row.get("f1_name", "")),
                str(row.get("f2_name", "")),
            ]
        ).lower()
        if needle not in hay:
            return False
    return True


def _to_float(s: str) -> float:
    try:
        return float(s)
    except Exception:
        return float("nan")


def main() -> None:
    p = argparse.ArgumentParser(description="Extract easy-to-read columns from eval_data_*.csv")
    p.add_argument("--eval-data", required=True, help="Path to reports*/eval_data_*.csv")
    p.add_argument(
        "--out",
        default="",
        help="Optional output CSV path. If omitted, writes to stdout.",
    )
    p.add_argument(
        "--fight-key",
        default="",
        help="Optional exact fight_key filter (e.g. '2025-09-06|harry hardwick|kaue fernandes')",
    )
    p.add_argument(
        "--contains",
        default="",
        help="Optional substring filter (matches fight_key/f1_name/f2_name, case-insensitive).",
    )
    p.add_argument(
        "--cols",
        default="",
        help=(
            "Comma-separated list of columns to output. "
            f"Default: {','.join(DEFAULT_COLS)}"
        ),
    )
    p.add_argument(
        "--sort-by",
        default="",
        help="Optional column to sort by (numeric sort). Example: model_prob_f1",
    )
    p.add_argument(
        "--desc",
        action="store_true",
        help="Sort descending (only used with --sort-by).",
    )
    p.add_argument(
        "--add-ufc-fights-before",
        action="store_true",
        help=(
            "Add f1_ufc_fights_before and f2_ufc_fights_before: "
            "counts of each fighter's prior UFC fights in our DB strictly before event_date."
        ),
    )
    p.add_argument(
        "--db-path",
        default="/Users/tylerbohan/code/ufc_analysis_v2/data/ufc_database.db",
        help="SQLite DB path used for --add-ufc-fights-before (default: data/ufc_database.db).",
    )

    args = p.parse_args()

    in_path = Path(args.eval_data)
    if not in_path.exists():
        raise SystemExit(f"File not found: {in_path}")

    out_cols = (
        [c.strip() for c in args.cols.split(",") if c.strip()]
        if args.cols.strip()
        else list(DEFAULT_COLS)
    )

    # Optional enrichment: UFC fight counts before this event date.
    add_ufc_counts = bool(args.add_ufc_fights_before)
    fighter_fight_dates: Dict[int, List[date]] = {}
    computed_cols = {"f1_ufc_fights_before", "f2_ufc_fights_before"}
    if add_ufc_counts:
        # Ensure required metadata exists in eval_data (row perspective IDs + event_date)
        # In this codebase, fighter_1_id / fighter_2_id correspond to the row's f1/f2 IDs.
        required_for_counts = ["event_date", "fighter_1_id", "fighter_2_id"]
        # We'll validate after reading header; for now, append output cols.
        for extra in ["f1_ufc_fights_before", "f2_ufc_fights_before"]:
            if extra not in out_cols:
                out_cols.append(extra)

    rows_out: List[Dict[str, str]] = []

    with in_path.open("r", newline="", errors="ignore") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("CSV appears to have no header row.")
        _require_cols(reader.fieldnames, ["f1_name", "f2_name", "fight_key"])

        # If user requests columns not present, fail fast (typos are common).
        # (Exclude computed enrichment columns, which are added by this script.)
        input_cols = [c for c in out_cols if c not in computed_cols]
        _require_cols(reader.fieldnames, input_cols)

        if add_ufc_counts:
            _require_cols(reader.fieldnames, ["event_date", "fighter_1_id", "fighter_2_id"])
            db_path = Path(args.db_path)
            if not db_path.exists():
                raise SystemExit(f"--db-path not found: {db_path}")
            fighter_fight_dates = _build_fighter_fight_dates(db_path)

        fight_key = args.fight_key.strip() or None
        contains = args.contains.strip() or None

        for row in reader:
            if not _matches_filters(row, fight_key=fight_key, contains=contains):
                continue
            out_row = {c: row.get(c, "") for c in out_cols if c not in {"f1_ufc_fights_before", "f2_ufc_fights_before"}}

            if add_ufc_counts:
                d = _parse_date(row.get("event_date", ""))
                try:
                    f1_id = int(row.get("fighter_1_id", "") or 0)
                except Exception:
                    f1_id = 0
                try:
                    f2_id = int(row.get("fighter_2_id", "") or 0)
                except Exception:
                    f2_id = 0

                def _count_before(fid: int) -> str:
                    if fid <= 0 or d is None:
                        return ""
                    dates = fighter_fight_dates.get(fid, [])
                    # strict before this contest
                    return str(bisect.bisect_left(dates, d))

                out_row["f1_ufc_fights_before"] = _count_before(f1_id)
                out_row["f2_ufc_fights_before"] = _count_before(f2_id)

            rows_out.append(out_row)

    if args.sort_by:
        sort_col = args.sort_by.strip()
        if sort_col not in out_cols:
            raise SystemExit(
                f"--sort-by '{sort_col}' must be one of the output cols: {out_cols}"
            )
        rows_out.sort(key=lambda r: _to_float(r.get(sort_col, "")), reverse=bool(args.desc))

    out_f = open(args.out, "w", newline="") if args.out else sys.stdout
    try:
        writer = csv.DictWriter(out_f, fieldnames=out_cols)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)
    finally:
        if args.out:
            out_f.close()


if __name__ == "__main__":
    main()


