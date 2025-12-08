# XGBoost Implementation Guide

Complete guide for training, evaluating, and using XGBoost for UFC fight prediction.

## Why XGBoost for UFC Betting

✅ **Fast training** – minutes instead of hours  
✅ **Fast predictions** – milliseconds per fight  
✅ **Feature importance** – see what matters (reach? striking accuracy?)  
✅ **Hyperparameter control** – tune for your specific problem  
✅ **Industry standard** – used by winning Kaggle teams, hedge funds  
✅ **Handles missing data** – fighters with incomplete stats  
✅ **Interpretable** – understand WHY predictions happen  

---

## Quick Start (Get Running Today)

### 1. Train Basic XGBoost Model

```bash
# Train with default parameters (takes 1-5 minutes)
python -m models.xgboost_model --train

# Train and evaluate
python -m models.xgboost_model --train --evaluate

# View feature importance
python -m models.xgboost_model --train --show-importance
```

### 2. Make Predictions

```bash
# Predict for specific fighters
python -m models.xgboost_model --predict \
    --fighter1 "Conor McGregor" \
    --fighter2 "Dustin Poirier"

# Predict upcoming event
python quick_predict.py --model xgboost
```

---

## Training Options

### Basic Training (Start Here)

```bash
python -m models.xgboost_model --train --evaluate
```

**Default Parameters:**
- `n_estimators`: 100 trees
- `max_depth`: 6
- `learning_rate`: 0.1
- `subsample`: 0.8
- `colsample_bytree`: 0.8

**Expected Results:**
- Training time: 1-5 minutes
- Log Loss: ~0.50-0.60 (lower is better)
- Accuracy: ~60-65%
- AUC: ~0.65-0.75

### Advanced Training with Custom Parameters

```bash
# More trees, slower learning
python -m models.xgboost_model --train \
    --n-estimators 200 \
    --learning-rate 0.05 \
    --max-depth 5

# Faster training, fewer trees
python -m models.xgboost_model --train \
    --n-estimators 50 \
    --learning-rate 0.2 \
    --max-depth 4
```

### Hyperparameter Tuning (Grid Search)

```bash
# Automatically find best parameters (takes 30-60 mins)
python -m models.xgboost_model --tune

# Tune with specific parameter ranges
python -m models.xgboost_model --tune --cv-folds 5
```

---

## Understanding Your Model

### Feature Importance

**This is CRITICAL for becoming a better bettor.**

```bash
# Show top 20 features
python -m models.xgboost_model --show-importance --top-n 20

# Save importance plot
python -m models.xgboost_model --show-importance --save-plot importance.png
```

**What This Tells You:**
- Is striking accuracy more important than takedown defense?
- Does reach advantage matter?
- Is recent form more predictive than career stats?

**You'll learn what ACTUALLY predicts fights** – not just rely on black box.

### Model Calibration

**Make sure your probabilities are realistic.**

```bash
# Check calibration
python -m models.xgboost_model --check-calibration

# Generate calibration plot
python -m models.xgboost_model --check-calibration --save-plot calibration.png
```

**What This Shows:**
- When you predict 40%, do fighters actually win 40% of the time?
- Or are you overconfident/underconfident?

**This is KEY for betting** – if your probabilities are miscalibrated, your edge calculations are wrong.

---

## Visualization & Analysis

### Training Curves

```bash
# Plot training progress
python -m models.xgboost_model --train --plot-learning-curve
```

Shows how model improves over iterations and detects overfitting.

### SHAP Values (Explainability)

```bash
# Explain individual predictions
python -m models.xgboost_model --explain-prediction \
    --fighter1 "Jon Jones" \
    --fighter2 "Stipe Miocic"
```

Shows which features contributed to this specific prediction.

### Cross-Validation

```bash
# 5-fold cross-validation
python -m models.xgboost_model --cross-validate --cv-folds 5

# Time-based cross-validation (more realistic for betting)
python -m models.xgboost_model --cross-validate --time-based
```

---

## Your Learning Path

### Week 1 (This Week)

**Goal: Get basic XGBoost working**

```bash
# Day 1: Train basic model
python -m models.xgboost_model --train --evaluate --show-importance

# Day 2: Check calibration
python -m models.xgboost_model --check-calibration

# Day 3: Make test predictions
python quick_predict.py --model xgboost

# Day 4-7: Analyze feature importance, understand what matters
```

### Week 2-3 (Early Dec)

**Goal: Test predictions on real events**

1. Make predictions for upcoming card
2. Track actual results vs predictions
3. Calculate log loss on real events
4. Iterate on features based on what worked

### Week 4-8 (Jan-Feb)

**Goal: Optimize and build intuition**

1. Paper trade 5-6 events
2. Tune hyperparameters based on results
3. Add/remove features systematically
4. Build intuition for what matters

---

## Parameter Guide

### Core Parameters

| Parameter | Default | What It Does | When to Increase | When to Decrease |
|-----------|---------|--------------|------------------|------------------|
| `n_estimators` | 100 | Number of trees | Model underfitting | Training too slow |
| `max_depth` | 6 | Tree depth | Model too simple | Overfitting |
| `learning_rate` | 0.1 | Step size | With more trees | Training unstable |
| `subsample` | 0.8 | % data per tree | Overfitting | Training too slow |
| `colsample_bytree` | 0.8 | % features per tree | Overfitting | Too much randomness |

### Common Configurations

**Fast Iteration (Development):**
```bash
python -m models.xgboost_model --train \
    --n-estimators 50 \
    --max-depth 4 \
    --learning-rate 0.2
```
Training time: ~30 seconds

**Balanced (Production):**
```bash
python -m models.xgboost_model --train \
    --n-estimators 100 \
    --max-depth 6 \
    --learning-rate 0.1
```
Training time: ~2 minutes

**High Accuracy (Competition):**
```bash
python -m models.xgboost_model --train \
    --n-estimators 300 \
    --max-depth 7 \
    --learning-rate 0.03
```
Training time: ~10 minutes

---

## Integration with Betting Workflow

### Step 1: Train Model

```bash
python -m models.xgboost_model --train --evaluate
```

### Step 2: Make Predictions

```bash
python predict.py --model xgboost --event-url "UFC_EVENT_URL"
```

### Step 3: Find Edges

```bash
python scripts/edge_validator.py --model xgboost
```

### Step 4: Track Performance

```bash
python scripts/track_performance.py --model xgboost
```

---

## The Mental Model Shift

### AutoGluon Approach
"Throw data at black box, hope it works, can't understand why"

### XGBoost Approach
"I control features → I see importance → I understand predictions → I iterate → I improve → I become expert"

**This is how you become a great bettor:**
- You understand WHY your model picks Fighter A over Fighter B
- You can explain: "He has better striking defense and reach advantage"
- You're not just trusting a black box
- **You're developing domain expertise**

---

## Troubleshooting

### Model Underfitting (Low Training Accuracy)

**Symptoms:** Training accuracy < 60%

**Solutions:**
```bash
# Increase model complexity
python -m models.xgboost_model --train \
    --n-estimators 200 \
    --max-depth 8
```

### Model Overfitting (Train >> Test Accuracy)

**Symptoms:** Training accuracy 90%+, test accuracy 60%

**Solutions:**
```bash
# Reduce complexity, add regularization
python -m models.xgboost_model --train \
    --max-depth 4 \
    --subsample 0.7 \
    --colsample-bytree 0.7 \
    --reg-alpha 1.0 \
    --reg-lambda 1.0
```

### Poor Calibration

**Symptoms:** Predictions consistently too high/low

**Solutions:**
```bash
# Apply calibration
python -m models.xgboost_model --train --calibrate
```

### Slow Training

**Symptoms:** Training takes > 10 minutes

**Solutions:**
```bash
# Use fewer trees or lower depth
python -m models.xgboost_model --train \
    --n-estimators 50 \
    --max-depth 5
```

---

## Advanced Features

### Custom Objective Functions

For betting-specific optimization (e.g., maximize ROI instead of accuracy).

See `models/xgboost_model.py` - `custom_objective()` function.

### Early Stopping

Automatically stops training when performance plateaus:

```python
# Built into default training
# Stops if no improvement for 20 rounds
```

### Feature Selection

Automatically remove unimportant features:

```bash
python -m models.xgboost_model --train --feature-selection --min-importance 0.01
```

---

## Files Generated

After training, you'll have:

```
models/saved/
├── xgboost_model.json          # Trained model
├── xgboost_model_params.json   # Hyperparameters
├── feature_importance.csv      # Feature rankings
├── feature_importance.png      # Importance plot
├── calibration_curve.png       # Calibration plot
├── learning_curve.png          # Training progress
└── training_metrics.json       # Performance metrics
```

---

## Next Steps

1. **Train your first model:**
   ```bash
   python -m models.xgboost_model --train --evaluate --show-importance
   ```

2. **Review feature importance** - understand what matters

3. **Check calibration** - ensure probabilities are realistic

4. **Make predictions** for upcoming card

5. **Track results** and iterate

---

## Support & Resources

- **Feature Engineering:** See `NEW_FEATURES_TO_ADD.md` for improvement ideas
- **Current Features:** See `scripts/list_features.py` for all 112 features
- **Betting Strategy:** See `EDGE_VALIDATOR_GUIDE.md` for finding value
- **Performance Tracking:** See `VALIDATION_WORKFLOW.md` for monitoring

---

**Remember: Start simple, iterate, learn, improve. You're building expertise, not just a model.**

