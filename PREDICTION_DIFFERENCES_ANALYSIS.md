# Prediction Differences Analysis

## Overview
This document explains potential reasons why `xgboost_predict.py` and `scripts/export_predictions_to_excel.py` might produce different predictions for the same matchup.

## Key Differences Found

### 1. **Fighter Name Matching** (Minor Difference)
Both scripts use `ILIKE` pattern matching, but with slightly different string formatting:
- `xgboost_predict.py`: `Fighter.name.ilike(f'%{fighter_1_name}%')`
- `export_predictions_to_excel.py`: `Fighter.name.ilike(f"%{name}%")`

**Impact**: Functionally identical, but could theoretically match different fighters if there are ambiguous names. However, both use `.first()` so they should match the same fighter.

### 2. **Date Handling** (Potential Issue)
The `export_predictions_to_excel.py` script reads a `fight_date` from the Excel file but **never uses it**:

```python
fight_date = row.get("fight_date", "")  # Line 230 - read but never used
features = matchup_extractor.extract_matchup_features(f1.id, f2.id)  # Line 242 - no as_of_date passed
```

**Impact**: 
- If the database contains fights that occurred **after** the `fight_date` in the Excel file, those fights will still be included in feature calculation
- This could cause predictions to differ if:
  - The database was updated between running the two scripts
  - The Excel file has a future date but the database has more recent fights
  - You want to simulate "what would the model have predicted on this date?"

**Fix**: Pass `as_of_date` to `extract_matchup_features`:
```python
from datetime import datetime
# Parse fight_date if provided
as_of_date = None
if fight_date:
    try:
        # Try to parse the date (adjust format as needed)
        as_of_date = pd.to_datetime(fight_date).to_pydatetime()
    except:
        pass

features = matchup_extractor.extract_matchup_features(f1.id, f2.id, as_of_date=as_of_date)
```

### 3. **Database Session State** (Potential Issue)
Both scripts create new database sessions, but:
- `xgboost_predict.py`: Creates session, uses it, closes it immediately
- `export_predictions_to_excel.py`: Creates session once, uses it for all fights, closes at end

**Impact**: If the database is being updated concurrently, or if there are transaction isolation issues, this could cause differences. However, this is unlikely to be the main issue.

### 4. **Feature Pipeline State** (Unlikely Issue)
Both scripts load the feature pipeline identically:
```python
pipeline = FeaturePipeline(initialize_db=False)
pipeline.load_pipeline()
```

**Impact**: Should be identical unless the saved pipeline files changed between runs.

### 5. **Model Loading** (Unlikely Issue)
Both scripts load the model identically:
```python
xgb_model = XGBoostModel()
xgb_model.load_model("xgboost_model")  # or 'xgboost_model'
```

**Impact**: Should be identical unless the model file changed between runs.

## Most Likely Causes of Differences

1. **Database State Changed**: If the database was updated between running the two scripts, predictions will differ because both use `as_of_date=None` (all available fights).

2. **Fighter Name Ambiguity**: If the name matching finds different fighters (unlikely but possible with ambiguous names).

3. **Date Not Being Used**: The Excel script reads `fight_date` but doesn't use it, so if you expect predictions "as of" that date, they won't match.

## How to Debug

Run the comparison script:
```bash
python compare_predictions.py --fighter-1 "Fighter Name 1" --fighter-2 "Fighter Name 2"
```

This will:
- Show if different fighters were matched
- Compare all feature values
- Compare scaled features
- Show prediction differences

## Recommended Fixes

1. **Use `as_of_date` in Excel export script** if `fight_date` is provided
2. **Add logging** to show which fighters were matched
3. **Add validation** to ensure both scripts match the same fighters
4. **Consider caching** feature extraction results if running multiple times

