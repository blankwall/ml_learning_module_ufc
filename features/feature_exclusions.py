"""
Feature Exclusions
------------------

Central place to **drop individual features/columns** from the final
training dataset and model input.

Usage:
  - Add base names (e.g. "early_finish_advantage") to EXCLUDED_BASE_FEATURES
    to drop all related columns:
      * f1_early_finish_advantage
      * f2_early_finish_advantage
      * early_finish_advantage_diff
  - Or add exact column names (matching schema/feature_schema.json) to
    EXCLUDED_COLUMNS to drop only those.

After changing this file:
  1. Re-create the training dataset
  2. Retrain the model
  3. Re-export the feature schema
"""

from typing import Iterable, List, Set

# Base logical feature names – we will drop any matchup columns derived from
# these (f1_*, f2_*, *_diff).
EXCLUDED_BASE_FEATURES: List[str] = [
    # Example:
    # "early_finish_advantage",
    "years_since_last_win",
    "age_x_years_since_last_win"
]

# Exact column names in the final training DataFrame to drop.
# These should match names in schema/feature_schema.json.
EXCLUDED_COLUMNS: List[str] = [
    # Example:
    # "power_striker_matchup",
]


def get_columns_to_exclude(all_columns: Iterable[str]) -> List[str]:
    """
    Given a list of DataFrame columns, return the subset that should be dropped.
    
    This supports:
      - Exact name matches from EXCLUDED_COLUMNS
      - Derived names from EXCLUDED_BASE_FEATURES:
          f1_<base>, f2_<base>, <base>_diff
    """
    cols_set: Set[str] = set(all_columns)
    to_drop: Set[str] = set()
    
    # Exact column exclusions
    for col in EXCLUDED_COLUMNS:
        if col in cols_set:
            to_drop.add(col)
    
    # Base feature exclusions (auto-expand to f1_*, f2_*, *_diff)
    for base in EXCLUDED_BASE_FEATURES:
        patterns = [
            base,
            f"f1_{base}",
            f"f2_{base}",
            f"{base}_diff",
        ]
        for p in patterns:
            if p in cols_set:
                to_drop.add(p)
    
    return sorted(to_drop)


def print_exclusion_summary() -> None:
    """Print a summary of configured exclusions before training."""
    print("\n" + "=" * 80)
    print("FEATURE EXCLUSION SUMMARY")
    print("=" * 80)
    
    if EXCLUDED_BASE_FEATURES:
        print(f"\nExcluding {len(EXCLUDED_BASE_FEATURES)} base features (will drop f1_*, f2_*, *_diff variants):")
        for base in EXCLUDED_BASE_FEATURES:
            print(f"  • {base}")
            print(f"    → will exclude: f1_{base}, f2_{base}, {base}_diff")
    else:
        print("\nNo base features excluded.")
    
    if EXCLUDED_COLUMNS:
        print(f"\nExcluding {len(EXCLUDED_COLUMNS)} exact column names:")
        for col in EXCLUDED_COLUMNS:
            print(f"  • {col}")
    else:
        print("\nNo exact columns excluded.")
    
    if not EXCLUDED_BASE_FEATURES and not EXCLUDED_COLUMNS:
        print("\n⚠️  No exclusions configured - all features will be used.")
    
    print("=" * 80 + "\n")


