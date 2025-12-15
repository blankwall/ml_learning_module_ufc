# Two-Model Strategy Guide

## Overview

Maintain two separate models to get the best of both worlds:

| Model | Training Data | Purpose |
|-------|---------------|---------|
| **Model A (Benchmark)** | Pre-2025 only | Clean evaluation & baseline |
| **Model B (Production)** | All data including 2025 | Informed predictions |

## Setup

### Step 1: Keep Your Current Model (Model A)

Your current model is already saved as `xgboost_model` in `models/saved/`.

This is your **benchmark model** trained only on pre-2025 data.

### Step 2: Train Model B with 2025 Data

```bash
# Train on ALL data including 2025
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_with_2025 \
  --export-schema \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05 \
  --subsample 0.8 \
  --colsample-bytree 0.8
```

This creates:
- `models/saved/xgboost_model_with_2025.json`
- `models/saved/xgboost_model_with_2025_features.json`

## Usage

### Compare Predictions Between Models

```bash
python scripts/compare_models.py \
  --fighter-1 "Kevin Vallejos" \
  --fighter-2 "Giga Chikadze" \
  --model-a xgboost_model \
  --model-b xgboost_model_with_2025
```

**Example Output:**
```
MODEL COMPARISON: Kevin Vallejos vs Giga Chikadze
================================================================================

XGBOOST_MODEL (without 2025):
  Kevin Vallejos: 44.9%
  Giga Chikadze: 55.1%
  Predicted Winner: Giga Chikadze
  Confidence: 10.2%

XGBOOST_MODEL_WITH_2025 (with 2025):
  Kevin Vallejos: 49.3%
  Giga Chikadze: 50.7%
  Predicted Winner: Giga Chikadze
  Confidence: 1.4%

DIFFERENCE (xgboost_model_with_2025 - xgboost_model):
  Kevin Vallejos: +4.4%
  Giga Chikadze: -4.4%

✓ Both models agree: Giga Chikadze wins
================================================================================
```

### Use Model B for Actual Predictions

Modify `xgboost_predict.py` to use Model B:

```bash
# Option 1: Pass model name as argument (requires code change)
python xgboost_predict.py \
  --fighter-1 "Kevin Vallejos" \
  --fighter-2 "Giga Chikadze" \
  --model-name xgboost_model_with_2025
```

Or temporarily rename the models:

```bash
# Option 2: Swap the default model
cd models/saved
mv xgboost_model.json xgboost_model_holdout.json
mv xgboost_model_with_2025.json xgboost_model.json
# Now xgboost_predict.py uses the 2025-informed model
```

### Use Model B for Excel Exports

Update `scripts/export_predictions_to_excel.py`:

```python
# Line 210: Change from
xgb_model.load_model("xgboost_model")

# To
xgb_model.load_model("xgboost_model_with_2025")
```

Then run:
```bash
python scripts/export_predictions_to_excel.py \
  --input data/predictions/upcoming_fights_fight_night_royval_kape.csv \
  --output data/predictions/predictions_informed.xlsx
```

## Advantages

### ✅ **Model A (Benchmark)**
- Clean 22% ROI evaluation
- No data contamination
- Honest performance baseline
- Great for research papers / presentations

### ✅ **Model B (Production)**
- Uses latest information (2025 data)
- More informed predictions
- Adjusts for recent UFC performances
- Better for actual betting decisions

### ✅ **Both Together**
- Compare predictions to see impact of 2025 data
- Track which model performs better over time
- Understand how new data changes model behavior
- Build confidence in predictions when both agree

## When Models Disagree

If Model A and Model B give different predictions, it means:

**The 2025 data significantly changed the model's opinion.**

Example scenarios:

1. **Fighter had breakout 2025 performances**
   - Model A: Underestimates them (no 2025 data)
   - Model B: Gives them more credit
   - → **Trust Model B**

2. **Fighter had decline in 2025**
   - Model A: Overestimates them (old data)
   - Model B: Adjusts downward
   - → **Trust Model B**

3. **Opponent level changed in 2025**
   - Model A: Based on pre-2025 opponent quality
   - Model B: Updated with 2025 opponent results
   - → **Trust Model B**

## Monthly Maintenance

### When December 13 Fights Conclude:

1. **Update 2025 data** with Dec 13 results
2. **Retrain Model B** with updated data:

```bash
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_with_2025 \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05
```

3. **Keep Model A unchanged** (your benchmark stays clean)

### In 2026:

Create Model C with all 2025 + 2026 data, and hold out 2026 for evaluation:

```bash
# New benchmark (2026 holdout)
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_2026_holdout \
  --holdout-from-year 2026 \
  --data-path data/processed/training_data.csv \
  # ... other args

# Production model (all data)
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_production \
  --data-path data/processed/training_data.csv \
  # ... other args
```

## Best Practices

1. **Always keep a clean holdout model** for honest evaluation
2. **Use the informed model for real money decisions**
3. **Compare predictions** when making significant bets
4. **Track performance of both models** over time
5. **Retrain production model monthly** with latest data
6. **Never retrain the benchmark model** (preserve evaluation integrity)

## Model Naming Convention

Suggested naming scheme:

```
xgboost_model                    # Current default (pre-2025)
xgboost_model_with_2025          # Includes 2025 data
xgboost_model_2025_holdout       # Explicit benchmark
xgboost_model_production         # Always the latest
xgboost_model_YYYYMM             # Monthly snapshots (e.g., xgboost_model_202512)
```

## Quick Reference

### Train New Model
```bash
python -m models.xgboost_model --train --model-name YOUR_NAME_HERE
```

### Compare Two Models
```bash
python scripts/compare_models.py \
  --fighter-1 "Fighter A" \
  --fighter-2 "Fighter B" \
  --model-a MODEL_A_NAME \
  --model-b MODEL_B_NAME
```

### List Available Models
```bash
ls models/saved/*.json | grep -v "_features"
```

### Delete Old Model
```bash
rm models/saved/OLD_MODEL_NAME.json
rm models/saved/OLD_MODEL_NAME_features.json
```

