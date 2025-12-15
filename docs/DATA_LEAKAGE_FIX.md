# Data Leakage Fix - Point-in-Time Feature Calculation

## The Problem

The model was achieving 90.2% accuracy on the 2025 holdout set, which seemed too good to be true. Deep analysis revealed **data leakage**: features were being calculated using **ALL** of a fighter's historical data, including fights that happened **after** the fight being predicted.

### Evidence of Leakage:

- **38 features had >0.5 correlation with outcomes** (suspicious!)
- `fights_since_last_win_diff`: 0.824 correlation
- `losses_since_last_win_diff`: 0.821 correlation
- `time_decayed_win_rate_diff`: 0.804 correlation

These correlations are impossibly high unless the features are "peeking" at future data.

### Example of the Bug:

```python
# Predicting a fight from February 2025
fight_date = datetime(2025, 2, 15)

# BUG: Features calculated using ALL 2025 fights
features = extract_features(fighter_id, as_of_date=None)  # ❌ WRONG

# Turner's "fights_since_last_win" would be 0 if he won in March
# But we're using that to predict his February fight!
```

## The Fix

### 1. **Updated `create_training_dataset`** (`features/matchup_features.py`)

Changed from:
```python
features_win = matchup_extractor.extract_matchup_features(
    winner_id,
    loser_id,
    as_of_date=None,  # ❌ Using all data
    feature_set=feature_set
)
```

To:
```python
event_date = fight.event.date if fight.event and fight.event.date else None

features_win = matchup_extractor.extract_matchup_features(
    winner_id,
    loser_id,
    as_of_date=event_date,  # ✅ Only use fights BEFORE this event
    feature_set=feature_set
)
```

### 2. **Updated `get_fighter_record`** (`features/registry.py`)

Changed from using cumulative career stats (Fighter.wins/losses) to calculating from fight history:

```python
def get_fighter_record(
    self,
    fighter_id: int,
    as_of_date: Optional[datetime] = None  # ✅ Added parameter
) -> Optional[Dict]:
    # Calculate from fight history to respect as_of_date
    fight_history = self.get_fight_history(fighter_id, as_of_date)
    
    wins = (fight_history["result"] == "win").sum()
    losses = (fight_history["result"] == "loss").sum()
    # ...
```

### 3. **Wrapped `get_fighter_record` in context** (`features/registry.py`)

Created a closure that captures `as_of_date`:

```python
def get_fighter_record_as_of(fid: int) -> Optional[Dict]:
    return self.get_fighter_record(fid, as_of_date)

context = {
    # ...
    "get_fighter_record": get_fighter_record_as_of,  # ✅ Passes as_of_date
}
```

This ensures opponent quality features also respect point-in-time calculation.

## What This Means

### Before the Fix:
- Model "knew" who won because features included future data
- 90.2% accuracy was **fake**
- Model was useless for actual predictions

### After the Fix:
- Features only use data available **at prediction time**
- Accuracy will drop significantly (this is GOOD!)
- Model predictions are now **legitimate**
- You can trust the holdout evaluation

## Next Steps

### 1. Verify the Fix Works

```bash
python scripts/verify_point_in_time.py
```

This should show that features change over time (not constant).

### 2. Recreate Training Data

```bash
./train.sh
```

This will regenerate the training dataset with point-in-time features.

### 3. Re-evaluate on Holdout Set

```bash
python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2025_odds.csv \
  --min-year 2025 \
  --output-dir reports
```

### 4. Re-run Deep Analysis

```bash
python -m evaluation.deep_analysis \
  --eval-data reports/eval_data_<timestamp>.csv \
  --min-year 2025 \
  --output-dir reports/deep_analysis
```

## Expected Results After Fix

- **Model accuracy: 55-75%** (more realistic)
- **Market accuracy: 65-70%**
- **Feature correlations: <0.4** (no more suspiciously high values)
- **Agreement with market: 70-85%** (healthy)
- **Model edge on disagreements: 55-65%** (if model is good)

If the model still shows >85% accuracy after this fix, there's another source of leakage to investigate.

## Technical Details

### Point-in-Time Calculation Flow:

1. **Training**: For each fight, pass `fight.event.date` as `as_of_date`
2. **get_fight_history**: Filter to only fights where `event_date_parsed <= as_of_date`
3. **get_fighter_record**: Calculate wins/losses from filtered fight history
4. **All features**: Calculate using only the filtered historical data

### Cache Key Update:

The fighter record cache now uses `(fighter_id, as_of_date_iso)` tuples as keys instead of just `fighter_id`, allowing cached records for different time points.

## Files Changed

1. `features/matchup_features.py` - Pass event_date to extract_matchup_features
2. `features/registry.py` - Update get_fighter_record to use fight history + add as_of_date wrapper
3. `evaluation/deep_analysis.py` - Fix date handling bug
4. `scripts/verify_point_in_time.py` - New verification script

## Verification Checklist

- [ ] Run `scripts/verify_point_in_time.py` - features change over time
- [ ] Recreate training data with `./train.sh`
- [ ] Check training log - no errors during feature extraction
- [ ] Re-evaluate on 2025 holdout set
- [ ] Run deep analysis - correlations drop below 0.5
- [ ] Model accuracy drops to realistic range (55-75%)
- [ ] Test predictions on upcoming fights - make sense

## Notes

- This fix applies to **all** historical analysis, not just the holdout set
- If you use `as_of_date=None`, features will use all available data (useful for live predictions)
- The fix maintains backward compatibility - existing code that doesn't pass `as_of_date` will still work

