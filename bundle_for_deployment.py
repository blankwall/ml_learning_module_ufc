#!/usr/bin/env python3
"""
Bundle UFC Analysis for Deployment

Creates a minimal bundle with all necessary files to run:
- python -m evaluation.preview_upcoming_fights
- python xgboost_predict.py

The bundle includes:
- All necessary Python modules
- Database file
- All model files
- Configuration
- Setup script using uv
"""

import shutil
import sys
from pathlib import Path
from typing import List, Set

# Project root
PROJECT_ROOT = Path(__file__).parent
BUNDLE_DIR = PROJECT_ROOT / "ufc_analysis_bundle"
BUNDLE_DIR.mkdir(exist_ok=True)

# Directories to copy (Python packages)
PACKAGE_DIRS = [
    "database",
    "features",
    "models",
    "evaluation",
    "scripts",
    "schema",
    "config",
    "predict_site",
]

# Files to copy from root
ROOT_FILES = [
    "xgboost_predict.py",
    "pyproject.toml",
]

# Data files to copy
DATA_FILES = [
    "data/ufc_database.db",
]

# Model directory to copy entirely
MODEL_DIR = "models/saved"

# Files to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".git",
    ".gitignore",
    "*.log",
    ".DS_Store",
    "*.backup",
    "*.broken",
    "*.mismatch",
]


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def copy_directory(src: Path, dst: Path, exclude_patterns: List[str] = None):
    """Copy a directory recursively, excluding certain patterns."""
    if exclude_patterns is None:
        exclude_patterns = EXCLUDE_PATTERNS
    
    dst.mkdir(parents=True, exist_ok=True)
    
    for item in src.iterdir():
        if should_exclude(item):
            continue
        
        dst_item = dst / item.name
        
        if item.is_dir():
            copy_directory(item, dst_item, exclude_patterns)
        else:
            shutil.copy2(item, dst_item)
            print(f"  Copied: {item.relative_to(PROJECT_ROOT)}")


def create_setup_script(bundle_path: Path):
    """Create a setup script that uses uv to install dependencies."""
    setup_script = bundle_path / "setup.sh"
    
    content = """#!/bin/bash
# Setup script for UFC Analysis Bundle
# This script installs dependencies using uv

set -e

echo "=========================================="
echo "UFC Analysis Bundle Setup"
echo "=========================================="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv is not installed."
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  or: pip install uv"
    exit 1
fi

echo "✓ uv is installed"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Install dependencies
echo "Installing dependencies from pyproject.toml..."
# Activate venv and use python -m pip (most reliable)
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
deactivate

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To use the bundle:"
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Run predictions:"
echo "     # Web interface (recommended):"
echo "     streamlit run predict_site/app.py"
echo ""
echo "     # Or use CLI:"
echo "     python xgboost_predict.py --fighter-1 \"Fighter Name\" --fighter-2 \"Fighter Name\" --model xgboost_model_with_2025"
echo ""
echo "     python -m evaluation.preview_upcoming_fights \\"
echo "       --input data/predictions/upcoming_fights_ufc325.csv \\"
echo "       --model-name xgboost_model_with_2025 --symmetric"
echo ""
"""
    
    setup_script.write_text(content)
    setup_script.chmod(0o755)
    print(f"Created: {setup_script.relative_to(PROJECT_ROOT)}")


def create_readme(bundle_path: Path):
    """Create a README with instructions."""
    readme = bundle_path / "README.md"
    
    content = """# UFC Analysis Bundle

This bundle contains everything needed to run UFC fight predictions.

## Setup

1. Install `uv` if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # or: pip install uv
   ```

2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

## Usage

### Web Interface (Recommended)

```bash
streamlit run predict_site/app.py
```

The web interface provides:
- CSV upload/paste for batch predictions
- Direct fighter comparison
- Interactive results display

### Single Fight Prediction (CLI)

```bash
python xgboost_predict.py \\
  --fighter-1 "Tai Tuivasa" \\
  --fighter-2 "Tallison Teixeira" \\
  --model xgboost_model_with_2025
```

### Batch Predictions from CSV (CLI)

```bash
python -m evaluation.preview_upcoming_fights \\
  --input data/predictions/upcoming_fights_ufc325.csv \\
  --model-name xgboost_model_with_2025 \\
  --symmetric
```

## Available Models

All models are in `models/saved/`. The default model is `xgboost_model_with_2025`.

To see available models:
```bash
ls models/saved/*.json
```

## Files Included

- **Code**: All Python modules needed for predictions
- **Database**: `data/ufc_database.db` - Contains fighter and fight data
- **Models**: All trained models in `models/saved/`
- **Config**: Configuration in `config/config.yaml`

## Notes

- The database file (`data/ufc_database.db`) contains all fighter and fight history
- Models are stored in `models/saved/` with naming pattern: `{model_name}.json`, `{model_name}_feature_scaler.pkl`, etc.
- The bundle uses `uv` for fast dependency management
"""
    
    readme.write_text(content)
    print(f"Created: {readme.relative_to(PROJECT_ROOT)}")


def main():
    """Main bundling function."""
    print("=" * 60)
    print("UFC Analysis Bundle Creator")
    print("=" * 60)
    print(f"Bundle directory: {BUNDLE_DIR}")
    print("")
    
    # Clean bundle directory
    if BUNDLE_DIR.exists():
        print("Cleaning existing bundle directory...")
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir()
    
    # Copy package directories
    print("\nCopying Python packages...")
    for pkg_dir in PACKAGE_DIRS:
        src = PROJECT_ROOT / pkg_dir
        if src.exists():
            dst = BUNDLE_DIR / pkg_dir
            print(f"Copying {pkg_dir}/...")
            copy_directory(src, dst)
        else:
            print(f"Warning: {pkg_dir} not found, skipping")
    
    # Copy root files
    print("\nCopying root files...")
    for root_file in ROOT_FILES:
        src = PROJECT_ROOT / root_file
        if src.exists():
            dst = BUNDLE_DIR / root_file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  Copied: {root_file}")
        else:
            print(f"Warning: {root_file} not found, skipping")
    
    # Copy data files
    print("\nCopying data files...")
    for data_file in DATA_FILES:
        src = PROJECT_ROOT / data_file
        if src.exists():
            dst = BUNDLE_DIR / data_file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  Copied: {data_file}")
        else:
            print(f"Warning: {data_file} not found, skipping")
    
    # Copy models directory
    print("\nCopying models...")
    src_models = PROJECT_ROOT / MODEL_DIR
    if src_models.exists():
        dst_models = BUNDLE_DIR / MODEL_DIR
        print(f"Copying {MODEL_DIR}/...")
        copy_directory(src_models, dst_models)
        
        # Count model files
        model_files = list(dst_models.rglob("*"))
        print(f"  Total model files: {len(model_files)}")
    else:
        print(f"Warning: {MODEL_DIR} not found, skipping")
    
    # Create data/predictions directory structure
    print("\nCreating data/predictions directory...")
    (BUNDLE_DIR / "data" / "predictions").mkdir(parents=True, exist_ok=True)
    print("  Created: data/predictions/")
    
    # Create setup script
    print("\nCreating setup script...")
    create_setup_script(BUNDLE_DIR)
    
    # Create README
    print("\nCreating README...")
    create_readme(BUNDLE_DIR)
    
    # Create .gitkeep for empty directories
    (BUNDLE_DIR / "logs").mkdir(exist_ok=True)
    (BUNDLE_DIR / "logs" / ".gitkeep").touch()
    
    print("\n" + "=" * 60)
    print("Bundle created successfully!")
    print("=" * 60)
    print(f"\nBundle location: {BUNDLE_DIR}")
    print(f"\nTo deploy:")
    print(f"  1. Copy the bundle directory to your target machine")
    print(f"  2. Run: cd {BUNDLE_DIR.name} && ./setup.sh")
    print(f"  3. Activate: source .venv/bin/activate")
    print(f"\nBundle size: {get_directory_size(BUNDLE_DIR) / (1024*1024):.2f} MB")


def get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


if __name__ == "__main__":
    main()

