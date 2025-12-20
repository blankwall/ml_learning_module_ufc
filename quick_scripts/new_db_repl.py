"""
new_db_repl.py
--------------

Simple interactive REPL for spot-checking the SQLite database created by
``new_create_database.py``.

This script does NOT depend on any existing project code – it just opens the
database, lets you run a few friendly commands, and pretty-prints selected
fields from the JSON blobs stored in the tables.

Default DB path: ``database/ufc_data.sqlite``
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from textwrap import indent
from typing import Any, Dict, Optional


DEFAULT_DB_PATH = Path("database/ufc_data.sqlite")


def pretty_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


def open_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"[ERROR] Database file not found: {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def cmd_help() -> None:
    print(
        "\nCommands:\n"
        "  help                         Show this help.\n"
        "  quit / exit                  Exit the REPL.\n"
        "  fight <fight_id>             Show a fight_details record.\n"
        "  fighter <fighter_id>         Show a fighters record.\n"
        "  fighter-by-name <name>       Search fighters by (case-insensitive) name.\n"
        "  event <event_id>             Show an events record.\n"
        "  event-by-name <name>         Search events by (case-insensitive) name.\n"
        "\n"
        "Examples:\n"
        "  fight 5f5b626e67529056\n"
        "  fighter eae48ff31db420c2\n"
        "  fighter-by-name Tsarukyan\n"
        "  event 92c96df8bdab5fea\n"
        "  event-by-name Tsarukyan vs. Hooker\n"
    )


def fetch_json_by_id(
    conn: sqlite3.Connection,
    table: str,
    id_column: str,
    record_id: str,
) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        f"SELECT data FROM {table} WHERE {id_column} = ?;",
        (record_id,),
    )
    row = cur.fetchone()
    cur.close()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Stored JSON in {table}.{id_column}={record_id!r} is invalid: {exc}")
        return None


def search_json_by_name(
    conn: sqlite3.Connection,
    table: str,
    id_column: str,
    name_field: str,
    name_query: str,
    limit: int = 10,
) -> None:
    """Simple LIKE-based name search within the JSON `data` column."""
    # We search via JSON_EXTRACT if available; if not, fall back to LIKE on the raw JSON.
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT {id_column}, data
            FROM {table}
            WHERE json_extract(data, ?) LIKE ?
            LIMIT ?;
            """,
            (f"$.{name_field}", f"%{name_query}%", limit),
        )
    except sqlite3.OperationalError:
        # Fallback: plain LIKE on the JSON blob.
        cur.execute(
            f"""
            SELECT {id_column}, data
            FROM {table}
            WHERE data LIKE ?
            LIMIT ?;
            """,
            (f"%{name_query}%", limit),
        )

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print(f"[INFO] No matches found in '{table}' for name query {name_query!r}.")
        return

    print(f"[INFO] Found {len(rows)} match(es) in '{table}':")
    for rec_id, data_str in rows:
        try:
            obj = json.loads(data_str)
        except json.JSONDecodeError:
            print(f"  - {rec_id}: <invalid JSON>")
            continue

        display_name = obj.get(name_field) or "<no name>"
        print(f"  - {rec_id}: {display_name}")


def show_fight(conn: sqlite3.Connection, fight_id: str) -> None:
    obj = fetch_json_by_id(conn, "fight_details", "fight_id", fight_id)
    if obj is None:
        print(f"[INFO] No fight_details row found for fight_id={fight_id!r}.")
        return

    header = (
        f"Fight {obj.get('fight_id')} | "
        f"{obj.get('fighter_1_name')} ({obj.get('fighter_1_result')}) vs. "
        f"{obj.get('fighter_2_name')} ({obj.get('fighter_2_result')}) | "
        f"winner={obj.get('winner')}"
    )
    print(header)
    print("-" * len(header))
    print(indent(pretty_json(obj), "  "))


def show_fighter(conn: sqlite3.Connection, fighter_id: str) -> None:
    obj = fetch_json_by_id(conn, "fighters", "fighter_id", fighter_id)
    if obj is None:
        print(f"[INFO] No fighters row found for fighter_id={fighter_id!r}.")
        return

    header = (
        f"Fighter {obj.get('fighter_id')} | {obj.get('name')} | "
        f"record={obj.get('wins')}-{obj.get('losses')}-{obj.get('draws')}"
    )
    print(header)
    print("-" * len(header))
    print(indent(pretty_json(obj), "  "))


def show_event(conn: sqlite3.Connection, event_id: str) -> None:
    obj = fetch_json_by_id(conn, "events", "event_id", event_id)
    if obj is None:
        print(f"[INFO] No events row found for event_id={event_id!r}.")
        return

    header = f"Event {obj.get('event_id')} | {obj.get('name')} | {obj.get('date')}"
    print(header)
    print("-" * len(header))

    fights = obj.get("fights") or []
    if isinstance(fights, list) and fights:
        print("  Card:")
        for f in fights:
            f1 = f.get("fighter_1_name")
            f2 = f.get("fighter_2_name")
            res = f.get("result")
            fid = f.get("fight_detail_id")
            print(f"    - {f1} vs. {f2} | result={res} | fight_id={fid}")
    else:
        print("  (No fights list on this event.)")

    print("\n  Full JSON:")
    print(indent(pretty_json(obj), "  "))


def repl(conn: sqlite3.Connection) -> None:
    cmd_help()
    while True:
        try:
            line = input("\nufc-db> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Exiting.")
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"quit", "exit"}:
            print("[INFO] Bye.")
            break
        if cmd == "help":
            cmd_help()
            continue

        if cmd == "fight":
            if not args:
                print("Usage: fight <fight_id>")
            else:
                show_fight(conn, args[0])
            continue

        if cmd == "fighter":
            if not args:
                print("Usage: fighter <fighter_id>")
            else:
                show_fighter(conn, args[0])
            continue

        if cmd == "fighter-by-name":
            if not args:
                print("Usage: fighter-by-name <name substring>")
            else:
                search_json_by_name(conn, "fighters", "fighter_id", "name", " ".join(args))
            continue

        if cmd == "event":
            if not args:
                print("Usage: event <event_id>")
            else:
                show_event(conn, args[0])
            continue

        if cmd == "event-by-name":
            if not args:
                print("Usage: event-by-name <name substring>")
            else:
                search_json_by_name(conn, "events", "event_id", "name", " ".join(args))
            continue

        print(f"[WARN] Unknown command: {cmd!r}. Type 'help' for options.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive REPL for exploring the UFC SQLite database.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file (default: database/ufc_data.sqlite).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = open_connection(args.db_path)
    try:
        repl(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()


