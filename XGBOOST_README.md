# XGBoost Implementation - Getting Started

## Quick Start (5 Minutes)

### 1. Train Your First Model

```bash
python xgboost_quickstart.py
```

This will:
- ✅ Load your 5,000+ fight training data
- ✅ Train XGBoost model (1-5 minutes)
- ✅ Show feature importance (what matters!)
- ✅ Generate calibration plots
- ✅ Save model for predictions

### 2. Make Predictions

```bash
# Predict specific fight
python -m models.xgboost_model --predict \
    --fighter1 "Conor McGregor" \
    --fighter2 "Dustin Poirier"

# Or use existing prediction script
python quick_predict.py
```

### 3. Understand Your Model

```bash
# See what features matter most
python -m models.xgboost_model --show-importance --top-n 20

# Check if probabilities are realistic
python -m models.xgboost_model --check-calibration --save-plots
```

---

## Files Created

| File | Purpose |
|------|---------|
| `XGBOOST_GUIDE.md` | **Complete documentation** - training, tuning, visualization |
| `XGBOOST_VS_AUTOGLUON.md` | **Why XGBoost** - comparison and reasoning |
| `models/xgboost_model.py` | **Main implementation** - full XGBoost model class |
| `xgboost_quickstart.py` | **Quick start script** - get running in 5 minutes |
| `SETUP.md` (updated) | **Installation guide** - updated with XGBoost instructions |

---

## Training Options

### Basic Training (Start Here)
```bash
python -m models.xgboost_model --train --evaluate --show-importance
```
**Time:** 1-5 minutes  
**Output:** Trained model + metrics + feature importance

### Advanced Training
```bash
# Custom parameters
python -m models.xgboost_model --train --evaluate \
    --n-estimators 200 \
    --max-depth 7 \
    --learning-rate 0.05

# Hyperparameter tuning (finds best parameters)
python -m models.xgboost_model --train --tune --cv-folds 5

# With calibration
python -m models.xgboost_model --train --calibrate --check-calibration
```

### Cross-Validation
```bash
# 5-fold cross-validation
python -m models.xgboost_model --cross-validate --cv-folds 5
```

---

## Key Commands

### Feature Analysis
```bash
# Top 20 features
python -m models.xgboost_model --show-importance --top-n 20 --save-plots

# See which features matter for predictions
python scripts/list_features.py
```

### Model Evaluation
```bash
# Check calibration
python -m models.xgboost_model --check-calibration --save-plots

# Plot learning curves
python -m models.xgboost_model --train --plot-learning-curve --save-plots
```

### Making Predictions
```bash
# Predict upcoming fights
python predict.py --model xgboost

# Find betting edges
python scripts/edge_validator.py --model xgboost
```

---

## Expected Results

### Performance Metrics
- **Accuracy:** 60-65%
- **Log Loss:** 0.50-0.60 (lower is better)
- **AUC:** 0.65-0.75
- **Training Time:** 1-5 minutes
- **Prediction Time:** < 1 millisecond per fight

### What You Get
1. **Feature Importance** - Know what matters (striking differential, reach, recent form)
2. **Fast Iteration** - Test new features in minutes, not hours
3. **Interpretability** - Understand why predictions happen
4. **Control** - Tune every parameter yourself
5. **Production Ready** - Industry-standard, battle-tested

---

## Learning Path

### Week 1: Get Running
```bash
# Day 1: Train basic model
python xgboost_quickstart.py

# Day 2-3: Understand features
python -m models.xgboost_model --show-importance --top-n 20

# Day 4-5: Test predictions
python quick_predict.py
```

### Week 2-3: Optimize
```bash
# Tune hyperparameters
python -m models.xgboost_model --train --tune

# Add/remove features based on importance
# See NEW_FEATURES_TO_ADD.md for ideas

# Check calibration
python -m models.xgboost_model --check-calibration
```

### Week 4+: Production
```bash
# Regular workflow:
# 1. Train model
# 2. Make predictions
# 3. Find edges
# 4. Track performance
# 5. Iterate based on results
```

---

## Why XGBoost Over AutoGluon?

| Feature | XGBoost | AutoGluon |
|---------|---------|-----------|
| Training Time | **3 minutes** | 8 hours |
| Interpretability | **✅ Full** | ❌ Black box |
| Control | **✅ Full** | ❌ Automated |
| Iteration Speed | **✅ Fast** | ❌ Slow |
| Feature Importance | **✅ Yes** | ❌ Hidden |
| Learning Curve | **✅ Learn** | ❌ Just trust |

**Read `XGBOOST_VS_AUTOGLUON.md` for detailed comparison.**

---

## Troubleshooting

### "Training data not found"
```bash
# Create training dataset first
python -m features.feature_pipeline --create
```

### "Model underfitting" (accuracy < 60%)
```bash
# Increase model complexity
python -m models.xgboost_model --train \
    --n-estimators 200 \
    --max-depth 8
```

### "Model overfitting" (train 90%, test 60%)
```bash
# Reduce complexity
python -m models.xgboost_model --train \
    --max-depth 4 \
    --subsample 0.7
```

### "Poor calibration"
```bash
# Apply calibration
python -m models.xgboost_model --train --calibrate
```

---

## Next Steps

1. **Train your first model:**
   ```bash
   python xgboost_quickstart.py
   ```

2. **Review outputs:**
   - `models/saved/feature_importance.png` - What matters?
   - `models/saved/calibration_curve.png` - Are probabilities realistic?
   - `models/saved/learning_curve.png` - Is model learning properly?

3. **Make predictions:**
   ```bash
   python quick_predict.py
   ```

4. **Read full guide:**
   - Open `XGBOOST_GUIDE.md` for complete documentation

5. **Iterate and improve:**
   - Add features from `NEW_FEATURES_TO_ADD.md`
   - Tune parameters based on results
   - Track performance on real events

---

## Files Generated After Training

```
models/saved/
├── xgboost_model.json              # Trained model
├── xgboost_model_features.json     # Feature names
├── xgboost_model_metrics.json      # Training metrics
├── xgboost_model_feature_importance.csv  # Feature rankings
├── feature_importance.png          # Feature importance plot
├── calibration_curve.png           # Calibration check
├── learning_curve.png              # Training progress
├── feature_scaler.pkl              # Feature scaler
└── feature_names.pkl               # Feature list
```

---

## Current Features (112 Total)

See `scripts/list_features.py` for complete list:
- 76 fighter-specific features (38 per fighter)
- 15 differential features (advantages)
- 9 style matchup features
- 2 common opponent features
- 10 round 3 performance features (cardio proxy)

**Recently Added:**
- ✅ Striking differential (F1 output vs F2 defense)
- ✅ Takedown matchup (F1 accuracy vs F2 defense)
- ✅ Round 3 performance (cardio proxy)

**To Add:** See `NEW_FEATURES_TO_ADD.md`

---

## Support & Documentation

- **Complete Guide:** `XGBOOST_GUIDE.md`
- **Why XGBoost:** `XGBOOST_VS_AUTOGLUON.md`
- **Feature List:** `scripts/list_features.py`
- **New Features:** `NEW_FEATURES_TO_ADD.md`
- **Setup:** `SETUP.md`
- **Betting Strategy:** `EDGE_VALIDATOR_GUIDE.md`

---

**Remember: XGBoost gives you control, speed, and understanding. This is how you become a great bettor.**

**Start now:**
```bash
python xgboost_quickstart.py
```

