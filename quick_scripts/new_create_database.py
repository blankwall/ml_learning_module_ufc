"""
new_create_database.py
-----------------------

Create a fresh SQLite database from the JSON files in ``data/processed``.

Design goals:
- Do not depend on any existing project code.
- Preserve the full JSON objects for exact round‑tripping and validation.
- Keep the schema simple and robust.

Schema
------
We create one table per JSON file, storing the full JSON blob plus a stable
primary key extracted from each record:

- fighters.json      -> table "fighters"      (fighter_id TEXT PRIMARY KEY, data TEXT NOT NULL)
- fight_details.json -> table "fight_details" (fight_id   TEXT PRIMARY KEY, data TEXT NOT NULL)
- events.json        -> table "events"        (event_id   TEXT PRIMARY KEY, data TEXT NOT NULL)

This keeps the database easy to validate: the ``data`` column is a JSON
representation of the original record.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


DEFAULT_DATA_DIR = Path("data/processed")
DEFAULT_DB_PATH = Path("database/ufc_data.sqlite")


class DatabaseCreator:
    """Create and populate an SQLite database from JSON files."""

    def __init__(self, db_path: Path, data_dir: Path) -> None:
        self.db_path = db_path
        self.data_dir = data_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> None:
        self._ensure_parent_dir()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            self._create_tables(conn)
            self._populate_all(conn)
            conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_parent_dir(self) -> None:
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Drop and recreate all target tables."""
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS fighters;")
        cursor.execute(
            """
            CREATE TABLE fighters (
                fighter_id TEXT PRIMARY KEY,
                data       TEXT NOT NULL
            );
            """
        )

        cursor.execute("DROP TABLE IF EXISTS fight_details;")
        cursor.execute(
            """
            CREATE TABLE fight_details (
                fight_id TEXT PRIMARY KEY,
                data     TEXT NOT NULL
            );
            """
        )

        cursor.execute("DROP TABLE IF EXISTS events;")
        cursor.execute(
            """
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                data     TEXT NOT NULL
            );
            """
        )

        cursor.close()

    def _populate_all(self, conn: sqlite3.Connection) -> None:
        """Populate all tables from their corresponding JSON files."""
        self._populate_table(
            conn=conn,
            json_path=self.data_dir / "fighters.json",
            table_name="fighters",
            id_key="fighter_id",
        )
        self._populate_table(
            conn=conn,
            json_path=self.data_dir / "fight_details.json",
            table_name="fight_details",
            id_key="fight_id",
        )
        self._populate_table(
            conn=conn,
            json_path=self.data_dir / "events.json",
            table_name="events",
            id_key="event_id",
        )

    def _populate_table(
        self,
        conn: sqlite3.Connection,
        json_path: Path,
        table_name: str,
        id_key: str,
    ) -> None:
        """Load one JSON file and insert rows into the given table.

        Parameters
        ----------
        conn
            Open SQLite connection.
        json_path
            Path to the JSON file containing a list of records.
        table_name
            Name of the SQLite table to insert into.
        id_key
            Key inside each JSON object that will be used as the primary key.
        """
        if not json_path.exists():
            print(f"[WARN] JSON file not found for table '{table_name}': {json_path}")
            return

        print(f"[INFO] Loading {json_path} into table '{table_name}'...")
        records = self._load_json_array(json_path)

        rows = [
            self._record_to_row(record=record, id_key=id_key, table_name=table_name)
            for record in records
        ]

        # Filter out any records that were skipped due to missing ID.
        rows = [row for row in rows if row is not None]

        with conn:
            conn.executemany(
                f"INSERT OR REPLACE INTO {table_name} ( {id_key}, data ) VALUES (?, ?);",
                rows,  # type: ignore[arg-type]
            )

        print(f"[INFO] Inserted {len(rows)} rows into '{table_name}'.")

    @staticmethod
    def _load_json_array(path: Path) -> Iterable[Dict[str, Any]]:
        """Load a JSON file that contains a top-level list of objects."""
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Expected top-level JSON array in {path}, got {type(data)!r}")

        return data

    @staticmethod
    def _record_to_row(
        record: Dict[str, Any],
        id_key: str,
        table_name: str,
    ) -> Tuple[str, str] | None:
        """Convert a JSON record into a (id, json_string) row tuple."""
        if id_key not in record:
            print(
                f"[WARN] Skipping record without '{id_key}' in table '{table_name}'. "
                f"Record keys: {list(record.keys())}"
            )
            return None

        record_id = str(record[id_key])
        # Use a canonical JSON representation for stability.
        json_str = json.dumps(record, sort_keys=True, ensure_ascii=False)
        return record_id, json_str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an SQLite database from UFC JSON data in data/processed.",
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
        help="Path to the SQLite database file to create (default: database/ufc_data.sqlite).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    creator = DatabaseCreator(db_path=args.db_path, data_dir=args.data_dir)
    creator.run()
    print(f"[DONE] Database created at: {args.db_path}")


if __name__ == "__main__":
    main()


