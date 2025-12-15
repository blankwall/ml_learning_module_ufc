# Physical Difference Bug Fix

## Problem Identified

The feature distribution validation revealed extreme physical differences:
- **Height differences**: Min: -190.5 cm, Max: 190.5 cm
- **Reach differences**: Min: -80.0 inches, Max: 84.0 inches
- **Mean reach difference**: 44.1 inches (should be ~0)

## Root Cause

When fighters had missing physical data (`None` in database), the feature extraction was defaulting to `0`:

```python
# OLD CODE (BUGGY)
height_cm = fighter.height_cm or 0  # None becomes 0!
reach_inches = fighter.reach_inches or 0  # None becomes 0!
```

This created false extreme differentials:
- Fighter 1: height = 190.5 cm, Fighter 2: height = None → height_advantage = 190.5 - 0 = **190.5 cm** ❌
- Fighter 1: height = None, Fighter 2: height = 190.5 cm → height_advantage = 0 - 190.5 = **-190.5 cm** ❌

## Solution

Changed to use `NaN` for missing values instead of `0`:

### 1. Updated `features/physical.py`
```python
# NEW CODE (FIXED)
height_cm = fighter.height_cm if fighter.height_cm is not None else np.nan
reach_inches = fighter.reach_inches if fighter.reach_inches is not None else np.nan
```

### 2. Updated `features/matchup_features.py`
```python
# NEW CODE (FIXED)
def safe_diff(key: str, default=0):
    """Calculate difference, returning NaN if either value is NaN"""
    v1 = f1_features.get(key, default)
    v2 = f2_features.get(key, default)
    if np.isnan(v1) or np.isnan(v2):
        return np.nan  # Don't create false differentials
    return v1 - v2

differentials['height_advantage'] = safe_diff('height_cm', np.nan)
differentials['reach_advantage'] = safe_diff('reach_inches', np.nan)
```

## Impact

**Before Fix:**
- Extreme false differentials when one fighter has missing data
- Mean reach difference: 44.1 inches (biased)
- Min/Max ranges: -190.5 to 190.5 cm (impossible values)

**After Fix:**
- Missing data results in NaN (explicit missing value)
- No false extreme differentials
- Mean should be closer to 0 (only real differences counted)
- Min/Max ranges should be realistic (e.g., -30 to 30 cm)

## Data Quality Notes

From investigation:
- **Null heights**: 14 fighters
- **Null reaches**: 784 fighters (significant!)

The model/scaler will need to handle NaN values:
- Option 1: Impute with median/mean before training
- Option 2: Use a model that handles NaN natively (XGBoost can handle NaN)
- Option 3: Add a "missing_height" / "missing_reach" binary indicator

## Next Steps

1. ✅ Fix applied - use NaN for missing values
2. ⏳ Re-run feature extraction
3. ⏳ Re-run distribution validation - should see realistic ranges
4. ⏳ Verify model handles NaN correctly (XGBoost should be fine)
5. ⏳ Consider adding missing data indicators as features

