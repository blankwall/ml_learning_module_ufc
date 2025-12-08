"""
Convert a line-by-line odds board CSV (like data/predictions/ufc_324.csv)
into the simple upcoming-fights format used by export_predictions_to_excel.py.

Input format (tab-separated, as in ufc_324.csv):
  - Header row: "Fighters\tBetOnline\tBovada\t..."
  - For each fighter:
      row i:   fighter name in "Fighters" column
      rows i+: odds values in bookmaker columns (e.g. BetOnline) on separate
               lines, possibly interleaved with blank rows, until the next
               non-empty "Fighters" cell (next fighter).

We:
  - Extract the first non-empty BetOnline price under each fighter.
  - Pair fighters in order: (0,1), (2,3), ...
  - Emit a CSV with columns:
        event,fight_date,fighter_1_name,fighter_2_name,
        fighter_1_odds,fighter_2_odds,is_title_fight
"""

import argparse
from pathlib import Path

import pandas as pd
from loguru import logger


def _parse_american_odds(value: str) -> int:
    """Parse American odds like '+170' or '-200' into an int."""
    if value is None:
        raise ValueError("Empty odds string")
    s = str(value).strip()
    if not s:
        raise ValueError("Empty odds string")
    # Strip leading '+' if present
    if s.startswith("+"):
        s = s[1:]
    return int(s)


def extract_fighter_odds_from_board(df: pd.DataFrame, book_col: str = "BetOnline"):
    """
    Given the raw odds board DataFrame, return a list of (name, odds_int).

    The UFC 324 CSV you have is essentially a single logical column where:
      - A row with a non-empty string that does NOT start with '+' or '-'
        is treated as a fighter name.
      - The next non-empty string that DOES start with '+' or '-' is treated
        as that fighter's American odds.

    The other bookmaker columns are effectively unused in the current file,
    so we just look at the 'Fighters' column.
    """
    if "Fighters" not in df.columns:
        raise ValueError("Expected a 'Fighters' column in input CSV")

    series = df["Fighters"]
    fighters = []
    i = 0
    n = len(series)

    while i < n:
        val = series.iloc[i]
        if pd.isna(val):
            i += 1
            continue

        text = str(val).strip()
        if not text:
            i += 1
            continue

        # If this line starts with + or -, it's an odds line, not a name.
        if text.startswith("+") or text.startswith("-"):
            i += 1
            continue

        # Treat as fighter name
        name = text

        # Look ahead for the next odds-looking value
        odds_value = None
        j = i + 1
        while j < n:
            next_val = series.iloc[j]
            if pd.isna(next_val) or not str(next_val).strip():
                j += 1
                continue

            next_text = str(next_val).strip()
            if next_text.startswith("+") or next_text.startswith("-"):
                odds_value = next_text
                break
            else:
                # We've hit the next fighter name without finding odds
                break

            j += 1

        if odds_value is None:
            logger.warning(f"No odds found for fighter '{name}' starting at row {i}")
            i += 1
            continue

        try:
            odds_int = _parse_american_odds(odds_value)
        except Exception as e:
            logger.error(f"Failed to parse odds '{odds_value}' for fighter '{name}': {e}")
            i = j + 1
            continue

        fighters.append((name, odds_int))
        # Move on from where we found odds
        i = j + 1

    return fighters


def build_upcoming_from_board(
    input_path: Path,
    output_path: Path,
    event_name: str = "UFC 324",
    book_col: str = "BetOnline",
) -> Path:
    logger.info(f"Loading raw odds board from {input_path} ...")
    df_raw = pd.read_csv(input_path, sep="\t")

    fighters = extract_fighter_odds_from_board(df_raw, book_col=book_col)
    if len(fighters) % 2 != 0:
        logger.warning(
            f"Odd number of fighters extracted ({len(fighters)}). "
            "The last one will be dropped when pairing into fights."
        )
        fighters = fighters[:-1]

    rows = []
    for i in range(0, len(fighters), 2):
        (f1_name, f1_odds) = fighters[i]
        (f2_name, f2_odds) = fighters[i + 1]
        rows.append(
            {
                "event": event_name,
                "fight_date": "",
                "fighter_1_name": f1_name,
                "fighter_2_name": f2_name,
                "fighter_1_odds": f1_odds,
                "fighter_2_odds": f2_odds,
                "is_title_fight": 0,
            }
        )

    df_out = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)

    logger.success(
        f"Wrote upcoming fights CSV with {len(df_out)} rows to {output_path}"
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert UFC 324 odds board CSV into upcoming_fights format."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/predictions/ufc_324.csv",
        help="Path to raw UFC 324 odds CSV.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/predictions/upcoming_fights_ufc324.csv",
        help="Path to write upcoming fights CSV.",
    )
    parser.add_argument(
        "--event-name",
        type=str,
        default="UFC 324",
        help="Event name to use in the 'event' column.",
    )
    parser.add_argument(
        "--book-col",
        type=str,
        default="BetOnline",
        help="Which bookmaker column to use for odds (default: BetOnline).",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    build_upcoming_from_board(
        input_path=input_path,
        output_path=output_path,
        event_name=args.event_name,
        book_col=args.book_col,
    )


if __name__ == "__main__":
    main()


