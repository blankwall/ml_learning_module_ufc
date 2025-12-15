#!/usr/bin/env python3
"""
Initialize or update the monotone_constraints schema.

This script reads `schema/feature_schema.json` and creates
`schema/monotone_constraints.json` with one entry per feature.

You then manually edit `schema/monotone_constraints.json` to set:
  +1 → higher feature should INCREASE win probability
  -1 → higher feature should DECREASE win probability
   0 → no constraint
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any


FEATURE_SCHEMA_PATH = Path("schema/feature_schema.json")
MONO_SCHEMA_PATH = Path("schema/monotone_constraints.json")


def load_feature_schema() -> Dict[str, Any]:
    if not FEATURE_SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"{FEATURE_SCHEMA_PATH} not found. Export feature schema first via FeaturePipeline.export_feature_schema()."
        )
    with FEATURE_SCHEMA_PATH.open("r") as f:
        return json.load(f)


def init_monotone_schema(force: bool = False) -> None:
    schema = load_feature_schema()
    features = schema.get("features", [])
    version = schema.get("version", "1.0.0")

    if MONO_SCHEMA_PATH.exists() and not force:
        print(f"{MONO_SCHEMA_PATH} already exists. Use --force to overwrite.")
        return

    constraints = {name: 0 for name in features}

    mono_schema = {
        "version": version,
        "num_features": len(features),
        "default": 0,
        "constraints": constraints,
    }

    MONO_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MONO_SCHEMA_PATH.open("w") as f:
        json.dump(mono_schema, f, indent=2)

    print(f"Initialized monotone_constraints schema at {MONO_SCHEMA_PATH}")
    print(
        "Edit this file to set +1 / -1 / 0 per feature, then re-run training "
        "to apply monotonic constraints."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize monotone_constraints schema from feature_schema.json"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing schema/monotone_constraints.json",
    )
    args = parser.parse_args()

    init_monotone_schema(force=args.force)


if __name__ == "__main__":
    main()


