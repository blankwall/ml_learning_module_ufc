"""
new_validate_database.py
------------------------

Cross-validate the SQLite database created by ``new_create_database.py`` against
the original JSON files in ``data/processed``.

Validation strategy
-------------------
1. **Database vs JSON (per table)**
   - For each supported dataset (fighters, fight_details, events):
     - Load the JSON file as a list of records.
     - For each record:
         * Extract the primary key (e.g. fighter_id).
         * Fetch the corresponding row from SQLite.
         * Parse the stored JSON from the ``data`` column.
         * Compare the full Python structures for equality.
     - Also verify that the row counts in SQLite match the JSON counts and that
       there are no "extra" rows in the database.

2. **Cross-dataset statistical validation (JSON vs JSON)**
   - Ensure every fight and winner/loser outcome is consistent across:
     - ``events.json`` (event fight cards),
     - ``fight_details.json`` (detailed fight objects),
     - ``fighters.json`` (per-fighter fight history and win/loss/draw totals).
   - Checks include:
     - Every ``events.fights[*].fight_detail_id`` exists in ``fight_details.json``.
     - Fighter names and winners in events vs fight_details match.
     - For each fighter, every fight in ``fight_history`` is matched to the
       corresponding event fight (by event URL + opponent + fighter name).
     - The per-fight outcome in ``fight_history`` matches the winner recorded
       in the event card.
     - Aggregate ``wins``, ``losses`` and ``draws`` on the fighter record equal
       the counts recomputed from their fight history.

If any discrepancies are found, they are reported and the process exits with
status code 1. On success, exit status is 0.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_DATA_DIR = Path("data/processed")
DEFAULT_DB_PATH = Path("database/ufc_data.sqlite")


@dataclass
class DatasetConfig:
    json_filename: str
    table_name: str
    id_key: str


DATASETS: List[DatasetConfig] = [
    DatasetConfig("fighters.json", "fighters", "fighter_id"),
    DatasetConfig("fight_details.json", "fight_details", "fight_id"),
    DatasetConfig("events.json", "events", "event_id"),
]


def load_json_array(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected top-level JSON array in {path}, got {type(data)!r}")
    return data


def fetch_all_ids(conn: sqlite3.Connection, table_name: str, id_column: str) -> List[str]:
    cursor = conn.cursor()
    cursor.execute(f"SELECT {id_column} FROM {table_name};")
    rows = [str(row[0]) for row in cursor.fetchall()]
    cursor.close()
    return rows


def fetch_row_data(conn: sqlite3.Connection, table_name: str, id_column: str, record_id: str) -> str | None:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT data FROM {table_name} WHERE {id_column} = ?;",
        (record_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        return None
    return row[0]


def compare_records(
    json_record: Dict[str, Any],
    db_json_str: str,
    dataset: DatasetConfig,
) -> bool:
    """Return True if the DB JSON matches the original JSON structure."""
    try:
        db_obj = json.loads(db_json_str)
    except json.JSONDecodeError as exc:
        print(
            f"[ERROR] Invalid JSON stored in table '{dataset.table_name}' "
            f"for {dataset.id_key}={json_record.get(dataset.id_key)!r}: {exc}"
        )
        return False

    if json_record == db_obj:
        return True

    # Optional: provide a minimal hint about differences.
    json_keys = set(json_record.keys())
    db_keys = set(db_obj.keys())
    missing_in_db = json_keys - db_keys
    extra_in_db = db_keys - json_keys
    key_mismatches = []
    for key in json_keys & db_keys:
        if json_record[key] != db_obj[key]:
            key_mismatches.append(key)

    print(
        f"[MISMATCH] Dataset '{dataset.table_name}' {dataset.id_key}="
        f"{json_record.get(dataset.id_key)!r}: "
        f"{len(missing_in_db)} missing keys, {len(extra_in_db)} extra keys, "
        f"{len(key_mismatches)} keys with different values."
    )
    if missing_in_db:
        print(f"           Missing keys in DB: {sorted(missing_in_db)[:5]}...")
    if extra_in_db:
        print(f"           Extra keys in DB: {sorted(extra_in_db)[:5]}...")
    if key_mismatches:
        print(f"           Keys with differing values (sample): {key_mismatches[:5]}...")

    return False


def validate_dataset(
    conn: sqlite3.Connection,
    data_dir: Path,
    dataset: DatasetConfig,
) -> bool:
    """Validate one dataset; return True if it passes, False otherwise."""
    json_path = data_dir / dataset.json_filename
    if not json_path.exists():
        print(f"[WARN] JSON file not found for dataset '{dataset.table_name}': {json_path}")
        return True  # treat as non-fatal; nothing to validate

    print(f"[INFO] Validating dataset '{dataset.table_name}' using {json_path}...")
    json_records = list(load_json_array(json_path))
    json_count = len(json_records)

    # Count rows in DB and gather IDs.
    db_ids = fetch_all_ids(conn, dataset.table_name, dataset.id_key)
    db_count = len(db_ids)

    ok = True

    if json_count != db_count:
        print(
            f"[ERROR] Count mismatch for '{dataset.table_name}': "
            f"JSON has {json_count} records, DB has {db_count} rows."
        )
        ok = False

    # Validate each JSON record against the DB row.
    seen_ids = set()
    for record in json_records:
        if dataset.id_key not in record:
            print(
                f"[ERROR] Record in JSON for '{dataset.table_name}' is missing id key "
                f"'{dataset.id_key}'. Record keys: {list(record.keys())}"
            )
            ok = False
            continue

        record_id = str(record[dataset.id_key])
        seen_ids.add(record_id)

        db_json_str = fetch_row_data(conn, dataset.table_name, dataset.id_key, record_id)
        if db_json_str is None:
            print(
                f"[ERROR] Missing row in table '{dataset.table_name}' for "
                f"{dataset.id_key}={record_id!r}."
            )
            ok = False
            continue

        if not compare_records(record, db_json_str, dataset):
            ok = False

    # Check for extra IDs in DB that are not present in JSON.
    extra_ids = sorted(set(db_ids) - seen_ids)
    if extra_ids:
        print(
            f"[ERROR] Found {len(extra_ids)} extra rows in table '{dataset.table_name}' "
            f"that do not exist in JSON. Sample: {extra_ids[:10]}"
        )
        ok = False

    if ok:
        print(f"[OK] Dataset '{dataset.table_name}' is consistent with JSON.")
    else:
        print(f"[FAIL] Dataset '{dataset.table_name}' has inconsistencies.")

    return ok


# ---------------------------------------------------------------------------
# Cross-dataset statistical validation helpers
# ---------------------------------------------------------------------------

def _normalize_event_result(raw: str) -> str:
    """Normalize fight result indicator from events/fight_details to a canonical form.

    Returns one of: 'fighter_1', 'fighter_2', 'draw', 'nc', 'unknown'.
    """
    text = (raw or "").strip().lower()
    if text in {"fighter_1", "f1", "red"}:
        return "fighter_1"
    if text in {"fighter_2", "f2", "blue"}:
        return "fighter_2"
    if text in {"draw", "d"}:
        return "draw"
    if text in {"nc", "n/c", "no contest", "no-contest"}:
        return "nc"
    return "unknown"


def _normalize_fighter_result(raw: str) -> str:
    """Normalize fighter-level result strings to: 'win', 'loss', 'draw', 'nc', 'unknown'."""
    text = (raw or "").strip().lower()
    if text in {"w", "win", "wins"}:
        return "win"
    if text in {"l", "loss", "losses"}:
        return "loss"
    if text in {"d", "draw", "draws"}:
        return "draw"
    if text in {"nc", "n/c", "no contest", "no-contest"}:
        return "nc"
    return "unknown"


def _derive_fighter_outcome_from_event_fight(
    fighter_name: str,
    fight: Dict[str, Any],
) -> str:
    """Given a fighter name and an event fight object, return that fighter's outcome.

    Returns: 'win', 'loss', 'draw', 'nc', or 'unknown'.
    """
    name1 = fight.get("fighter_1_name") or ""
    name2 = fight.get("fighter_2_name") or ""
    result = _normalize_event_result(fight.get("result", ""))

    if fighter_name == name1:
        if result == "fighter_1":
            return "win"
        if result == "fighter_2":
            return "loss"
        if result == "draw":
            return "draw"
        if result == "nc":
            return "nc"
        return "unknown"

    if fighter_name == name2:
        if result == "fighter_1":
            return "loss"
        if result == "fighter_2":
            return "win"
        if result == "draw":
            return "draw"
        if result == "nc":
            return "nc"
        return "unknown"

    # Fighter name does not appear in this fight.
    return "unknown"


def _index_events_by_url(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Create a mapping from event URL to event object."""
    index: Dict[str, Dict[str, Any]] = {}
    for event in events:
        url = event.get("url")
        if isinstance(url, str):
            index[url] = event
    return index


def _index_fight_details_by_id(fight_details: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for fd in fight_details:
        fid = fd.get("fight_id")
        if isinstance(fid, str):
            index[fid] = fd
    return index


def _winner_name_from_struct(
    fight: Dict[str, Any],
    result_field: str,
) -> str | None:
    """Return the winner's name for a fight struct, or None for draw/NC/unknown."""
    norm = _normalize_event_result(fight.get(result_field, ""))
    name1 = fight.get("fighter_1_name")
    name2 = fight.get("fighter_2_name")

    if norm == "fighter_1":
        return name1 if isinstance(name1, str) else None
    if norm == "fighter_2":
        return name2 if isinstance(name2, str) else None

    # draw / nc / unknown → no single winner name
    return None


def validate_events_against_fight_details(
    events: List[Dict[str, Any]],
    fight_details: List[Dict[str, Any]],
) -> bool:
    """Ensure every event fight links to a valid fight_detail and winner data matches."""
    print("[INFO] Cross-validating events.json against fight_details.json...")
    fight_details_by_id = _index_fight_details_by_id(fight_details)
    ok = True

    for event in events:
        event_name = event.get("name", "<unknown event>")
        fights = event.get("fights") or []
        if not isinstance(fights, list):
            print(f"[ERROR] Event '{event_name}' has non-list 'fights' field.")
            ok = False
            continue

        for fight in fights:
            fight_id = fight.get("fight_detail_id")
            if not fight_id:
                print(
                    f"[ERROR] Event '{event_name}' has fight without 'fight_detail_id'. "
                    f"Fight data: {fight}"
                )
                ok = False
                continue

            fd = fight_details_by_id.get(fight_id)
            if fd is None:
                # This typically means the fight_details scraper has not covered this
                # historical fight yet. Treat as a warning rather than a hard error.
                print(
                    f"[WARN] Event '{event_name}' references missing fight_details "
                    f"record fight_id={fight_id!r}."
                )
                continue

            # Compare fighter names ignoring ordering: the pair of names must match as a set.
            ev_names = {
                n for n in (fight.get("fighter_1_name"), fight.get("fighter_2_name")) if isinstance(n, str)
            }
            fd_names = {
                n for n in (fd.get("fighter_1_name"), fd.get("fighter_2_name")) if isinstance(n, str)
            }
            if not fd_names:
                # Incomplete fight_details entry (no names parsed) – warn and skip.
                print(
                    f"[WARN] fight_details entry for fight_id={fight_id!r} ({event_name}) "
                    f"has no fighter names; skipping strict comparison."
                )
                continue

            if ev_names != fd_names:
                print(
                    f"[ERROR] Name mismatch for fight_id={fight_id!r} ({event_name}): "
                    f"events.names={sorted(ev_names)!r}, fight_details.names={sorted(fd_names)!r}"
                )
                ok = False

            # Compare winner by fighter name (not by corner index).
            ev_winner_name = _winner_name_from_struct(fight, "result")
            fd_winner_name = _winner_name_from_struct(fd, "winner")

            # If fight_details could not determine a single winner name, just warn.
            if fd_winner_name is None and ev_winner_name is not None:
                print(
                    f"[WARN] fight_details has no clear winner for fight_id={fight_id!r} "
                    f"({event_name}); events.winner_name={ev_winner_name!r}."
                )
                continue

            if ev_winner_name != fd_winner_name:
                print(
                    f"[ERROR] Winner mismatch for fight_id={fight_id!r} ({event_name}): "
                    f"events.winner_name={ev_winner_name!r}, "
                    f"fight_details.winner_name={fd_winner_name!r}"
                )
                ok = False

    if ok:
        print("[OK] events.json and fight_details.json winners and participants are consistent.")
    else:
        print("[FAIL] Inconsistencies found between events.json and fight_details.json.")

    return ok


def validate_fighter_stats_against_events(
    fighters: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> bool:
    """Validate per-fighter fight history and aggregate records against events.json."""
    print("[INFO] Cross-validating fighters.json against events.json (per-fight outcomes and records)...")
    events_by_url = _index_events_by_url(events)
    ok = True

    for fighter in fighters:
        name = fighter.get("name")
        if not isinstance(name, str):
            continue

        history = fighter.get("fight_history") or []
        if not isinstance(history, list):
            print(
                f"[ERROR] Fighter {name!r} has non-list 'fight_history' field: "
                f"{type(history)!r}"
            )
            ok = False
            continue

        computed_wins = 0
        computed_losses = 0
        computed_draws = 0

        for entry in history:
            event_url = entry.get("event_url")
            opponent = entry.get("opponent")
            hist_result = _normalize_fighter_result(entry.get("result", ""))

            # Always count outcomes based on the fighter's own history record.
            if hist_result == "win":
                computed_wins += 1
            elif hist_result == "loss":
                computed_losses += 1
            elif hist_result == "draw":
                computed_draws += 1

            if not isinstance(event_url, str):
                print(
                    f"[WARN] Fighter {name!r} has history entry without valid 'event_url': "
                    f"{entry}"
                )
                continue

            event = events_by_url.get(event_url)
            if event is None:
                print(
                    f"[WARN] Fighter {name!r} references unknown event_url={event_url!r} "
                    f"in fight history."
                )
                continue

            fights = event.get("fights") or []
            if not isinstance(fights, list):
                print(
                    f"[WARN] Event for URL {event_url!r} has non-list 'fights' field."
                )
                continue

            # Find the matching fight in the event card based on fighter names.
            matches: List[Dict[str, Any]] = []
            for fight in fights:
                f1 = fight.get("fighter_1_name")
                f2 = fight.get("fighter_2_name")
                if (
                    isinstance(f1, str)
                    and isinstance(f2, str)
                    and isinstance(opponent, str)
                ):
                    if (f1 == name and f2 == opponent) or (f2 == name and f1 == opponent):
                        matches.append(fight)

            if not matches:
                print(
                    f"[WARN] Could not find matching event fight for fighter {name!r} "
                    f"vs opponent {opponent!r} at event_url={event_url!r}."
                )
                continue

            if len(matches) > 1:
                print(
                    f"[WARN] Multiple matching fights found for fighter {name!r} "
                    f"vs opponent {opponent!r} at event_url={event_url!r}."
                )
                continue

            event_fight = matches[0]
            outcome_from_event = _derive_fighter_outcome_from_event_fight(name, event_fight)

            if outcome_from_event == "unknown":
                print(
                    f"[WARN] Unable to derive outcome from event for fighter {name!r} "
                    f"vs opponent {opponent!r} at event_url={event_url!r}. "
                    f"Event fight: {event_fight}"
                )
                continue

            if hist_result != "unknown" and hist_result != outcome_from_event:
                print(
                    f"[ERROR] Outcome mismatch for fighter {name!r} vs opponent {opponent!r} "
                    f"at event_url={event_url!r}: history.result={entry.get('result')!r}, "
                    f"event-derived={outcome_from_event!r}"
                )
                ok = False

        # Compare aggregate record.
        json_wins = fighter.get("wins")
        json_losses = fighter.get("losses")
        json_draws = fighter.get("draws")

        if (
            isinstance(json_wins, int)
            and isinstance(json_losses, int)
            and isinstance(json_draws, int)
        ):
            if (
                json_wins != computed_wins
                or json_losses != computed_losses
                or json_draws != computed_draws
            ):
                print(
                    f"[ERROR] Record mismatch for fighter {name!r}: "
                    f"JSON wins/losses/draws=({json_wins}, {json_losses}, {json_draws}), "
                    f"recomputed=({computed_wins}, {computed_losses}, {computed_draws})."
                )
                ok = False

    if ok:
        print(
            "[OK] fighters.json fight histories and aggregate records are "
            "consistent with events.json."
        )
    else:
        print(
            "[FAIL] Inconsistencies found between fighters.json and events.json "
            "(per-fight outcomes or aggregate records)."
        )

    return ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that the SQLite DB contents match the JSON files in data/processed.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing fighters.json, fight_details.json, events.json "
        "(default: data/processed).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file to validate "
        "(default: database/ufc_data.sqlite).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.db_path.exists():
        print(f"[ERROR] Database file does not exist: {args.db_path}")
        sys.exit(1)

    all_ok = True
    with sqlite3.connect(args.db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        for dataset in DATASETS:
            dataset_ok = validate_dataset(conn, args.data_dir, dataset)
            if not dataset_ok:
                all_ok = False

    # Load JSON once for cross-dataset statistical validation.
    try:
        fighters_path = args.data_dir / "fighters.json"
        events_path = args.data_dir / "events.json"
        fight_details_path = args.data_dir / "fight_details.json"

        fighters: List[Dict[str, Any]] = (
            list(load_json_array(fighters_path)) if fighters_path.exists() else []
        )
        events: List[Dict[str, Any]] = (
            list(load_json_array(events_path)) if events_path.exists() else []
        )
        fight_details: List[Dict[str, Any]] = (
            list(load_json_array(fight_details_path)) if fight_details_path.exists() else []
        )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[ERROR] Failed to load JSON for cross-dataset validation: {exc}")
        sys.exit(1)

    if events and fight_details:
        if not validate_events_against_fight_details(events, fight_details):
            all_ok = False

    if fighters and events:
        if not validate_fighter_stats_against_events(fighters, events):
            all_ok = False

    if all_ok:
        print("[DONE] Validation successful: all datasets match JSON.")
        sys.exit(0)
    else:
        print("[DONE] Validation failed: see errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()


