#!/usr/bin/env bash
set -euo pipefail

# Feature set selection: 'base', 'advanced', or 'full' (default: full)
# You can override this by setting FEATURE_SET environment variable:
#   FEATURE_SET=base ./train.sh
#   FEATURE_SET=advanced ./train.sh
FEATURE_SET="${FEATURE_SET:-full}"

echo "Starting feature generation with '${FEATURE_SET}' feature set..."

# Create training dataset using the new modular feature system
# This internally generates fighter features and creates matchup features
# The feature pipeline handles everything: fighter features -> matchup features -> training dataset
python3 -m features.feature_pipeline --create --feature-set "${FEATURE_SET}"
echo "✔ Training dataset created with modular feature system"

echo "Starting model training & evaluation..."

# Train & evaluate XGBoost model
python3 -m models.xgboost_model \
  --train \
  --evaluate \
  --check-calibration \
  --save-plots \
  --export-schema \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05 \
  --subsample 0.8 \
  --colsample-bytree 0.8

echo "✅ Pipeline completed successfully"
