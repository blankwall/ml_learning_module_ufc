# Excluded Features: Point-in-Time Safety Status

This document analyzes the features currently excluded in `features/feature_exclusions.py` and their point-in-time safety status.

## Summary

- ✅ **Already Point-in-Time Safe** (but still excluded): Most features
- ⚠️ **Needs Verification**: `years_since_last_win` (appears safe but should be verified)
- ✅ **Recently Fixed**: All striking and grappling features (now safe but still excluded)

---

## ✅ Already Point-in-Time Safe (But Still Excluded)

### Striking Features - **RECENTLY FIXED** ✅

All of these features have been **fixed to be point-in-time safe** but remain excluded:

#### Core Striking Stats
- ✅ `sig_strikes_landed_per_min` - **FIXED** (uses fight_history)
- ✅ `striking_accuracy` - **FIXED** (uses fight_history)
- ✅ `striking_defense` - **FIXED** (computed from opponent accuracy in fight_history)
- ✅ `striking_differential` - **FIXED** (uses computed `sig_strikes_absorbed`)
- ✅ `defensive_efficiency` - **FIXED** (uses computed `striking_defense`)
- ✅ `striking_volume_control` - **FIXED** (uses computed `sig_strikes_absorbed`)

#### Last 3 Fights Metrics
- ✅ `distance_accuracy_last_3` - **FIXED** (computed from fight_history)
- ✅ `clinch_accuracy_last_3` - **FIXED** (computed from fight_history)
- ✅ `ground_output_per_min_last_3` - **FIXED** (computed from fight_history)
- ✅ `leg_strike_rate_last_3` - **FIXED** (computed from fight_history)
- ✅ `knockdowns_last_3` - **FIXED** (computed from fight_history)
- ✅ `striking_accuracy_last_3` - **FIXED** (computed from fight_history)
- ✅ `sig_strikes_landed_per_min_last_3` - **FIXED** (computed from fight_history)
- ✅ `head_strike_rate_last_3` - **FIXED** (computed from fight_history)
- ✅ `body_strike_rate_last_3` - **FIXED** (computed from fight_history)
- ✅ `ground_strike_rate_last_3` - **FIXED** (computed from fight_history)
- ✅ `distance_strike_rate_last_3` - **FIXED** (computed from fight_history)

#### Lifetime Metrics
- ✅ `distance_accuracy_lifetime` - **FIXED** (computed from fight_history)
- ✅ `clinch_accuracy_lifetime` - **FIXED** (computed from fight_history)
- ✅ `ground_output_per_min_lifetime` - **FIXED** (computed from fight_history)
- ✅ `leg_strike_rate_lifetime` - **FIXED** (computed from fight_history)
- ✅ `knockdowns_lifetime` - **FIXED** (computed from fight_history)
- ✅ `head_strike_rate_lifetime` - **FIXED** (computed from fight_history)
- ✅ `body_strike_rate_lifetime` - **FIXED** (computed from fight_history)
- ✅ `ground_strike_rate_lifetime` - **FIXED** (computed from fight_history)
- ✅ `distance_strike_rate_lifetime` - **FIXED** (computed from fight_history)
- ✅ `sig_strikes_landed_per_min_lifetime` - **FIXED** (computed from fight_history)
- ✅ `striking_accuracy_lifetime` - **FIXED** (computed from fight_history)

**Status**: All fixed in recent changes. See `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` and `docs/STRIKING_DEFENSE_POINT_IN_TIME_FIX.md`.

**Why Still Excluded?**: Likely excluded for other reasons (data quality, feature importance, model performance, etc.), not point-in-time safety.

**Action**: Can be safely re-enabled if desired. Verify they're not excluded for other valid reasons.

---

### Grappling Features - **RECENTLY FIXED** ✅

All of these features have been **fixed to be point-in-time safe** but remain excluded:

- ✅ `takedown_avg_per_15min` - **FIXED** (computed from fight_history)
- ✅ `takedown_accuracy` - **FIXED** (computed from fight_history)
- ✅ `takedown_defense` - **FIXED** (computed from opponent takedown accuracy)
- ✅ `submission_avg_per_15min` - **FIXED** (computed from fight_history)

**Status**: All fixed in recent changes. See `docs/GRAPPLING_POINT_IN_TIME_FIX.md`.

**Why Still Excluded?**: Likely excluded for other reasons (data quality, feature importance, model performance, etc.), not point-in-time safety.

**Action**: Can be safely re-enabled if desired. Verify they're not excluded for other valid reasons.

---

## ⚠️ Needs Verification / Minor Issues

### Time-Based Features

#### `years_since_last_win`
- **Location**: `features/time_based.py` → `extract_decline_features()`
- **Current Implementation**: 
  - Uses `fight_history` DataFrame (already filtered by `as_of_date`)
  - Uses `as_of_date` parameter when provided (line 201-203)
  - Calculates: `(ref_date - last_win_date).days / 365.25`
- **Status**: **APPEARS POINT-IN-TIME SAFE** ✅
  - Uses `fight_history` which is filtered by `as_of_date`
  - Uses `as_of_date` as reference date
  - Only looks at fights before `as_of_date`
- **Verification Needed**: 
  - Create unit test to verify values change across time points
  - Ensure `last_win_date` is from filtered history, not all-time

**Action**: Verify with unit test, then can be safely re-enabled.

#### `age_x_years_since_last_win`
- **Location**: `features/time_based.py` → `extract_age_interactions()`
- **Current Implementation**: 
  - Computed as `age * years_since_last_win`
  - Uses `age` from `fighter.age` (current age at scraping time)
  - Uses `years_since_last_win` from `extract_decline_features()` (point-in-time safe)
- **Status**: **MINOR ISSUE** ⚠️
  - `years_since_last_win` is point-in-time safe ✅
  - `age` uses `fighter.age` which is current age, not age at fight time ⚠️
  - Impact: Age changes slowly (1 year per year), so error is small but not zero
- **Fix Needed**: 
  - Calculate age at fight time from `fighter.date_of_birth` and fight date
  - Formula: `age_at_fight = (fight_date - date_of_birth).days / 365.25`
- **Verification Needed**: 
  - Verify `years_since_last_win` is point-in-time safe (see above)
  - Fix age calculation to use fight date instead of current age

**Action**: 
1. Verify `years_since_last_win` with unit test
2. Fix age calculation to compute at fight time
3. Then can be safely re-enabled

---

## Why Features Might Be Excluded (Even If Point-in-Time Safe)

Features can be excluded for reasons other than point-in-time safety:

1. **Data Quality Issues**
   - Missing data in many fights
   - Inconsistent data collection
   - Data quality concerns

2. **Feature Importance**
   - Low feature importance in model
   - Redundant with other features
   - Not predictive

3. **Model Performance**
   - Hurts model performance
   - Causes overfitting
   - Reduces generalization

4. **Data Leakage Concerns**
   - Even if point-in-time safe, may still leak information
   - Derived from sources that could be updated
   - Concerns about future information leakage

5. **Computational Cost**
   - Expensive to compute
   - Slow feature extraction

---

## Recommended Actions

### For Already Fixed Features (Striking & Grappling)

1. **Review exclusion reasons**: Check if they were excluded for point-in-time safety or other reasons
2. **Test re-enabling**: If excluded only for point-in-time safety, consider re-enabling:
   ```python
   # Remove from EXCLUDED_BASE_FEATURES if safe to re-enable
   ```
3. **Monitor performance**: If re-enabled, monitor model performance to ensure no degradation

### For Features Needing Verification

1. **`years_since_last_win`**:
   - Create unit test: `tests/test_years_since_last_win_point_in_time.py`
   - Verify values change across time points
   - Verify uses `as_of_date` correctly

2. **`age_x_years_since_last_win`**:
   - Verify after `years_since_last_win` is confirmed safe
   - Ensure age is computed at fight time

---

## Testing Template

For each feature that needs verification, create a test similar to:

```python
def test_feature_point_in_time():
    # Extract features at different points in time
    features_before = extract_features(fighter_id, as_of_date=before_fight_1)
    features_after_1 = extract_features(fighter_id, as_of_date=after_fight_1)
    features_after_2 = extract_features(fighter_id, as_of_date=after_fight_2)
    
    # Verify values change (not using global stat)
    assert features_before['feature'] != features_after_2['feature']
    
    # Verify values don't include future fights
    # (implicitly tested by using as_of_date)
```

---

## Summary Table

| Feature Category | Count | Status | Action |
|-----------------|-------|--------|--------|
| Striking (Core) | 6 | ✅ Fixed | Review exclusion reasons |
| Striking (Last 3) | 11 | ✅ Fixed | Review exclusion reasons |
| Striking (Lifetime) | 11 | ✅ Fixed | Review exclusion reasons |
| Grappling | 4 | ✅ Fixed | Review exclusion reasons |
| Time-Based (`years_since_last_win`) | 1 | ⚠️ Verify | Create unit test |
| Time-Based (`age_x_years_since_last_win`) | 1 | ⚠️ Minor Issue | Fix age calculation |
| **Total** | **34** | | |

## Detailed Fix Requirements

### For `years_since_last_win`

**Current Status**: Appears point-in-time safe (uses `as_of_date` and filtered `fight_history`)

**Fix Required**: 
- ✅ None - appears safe
- ⚠️ Verification: Create unit test to confirm

**Implementation**:
```python
# In extract_decline_features() - already correct:
ref_date = pd.to_datetime(as_of_date) if as_of_date is not None else datetime.now()
years_since_last_win = max(0.0, (ref_date - last_win_date).days / 365.25)
```

**Test Needed**: `tests/test_years_since_last_win_point_in_time.py`

---

### For `age_x_years_since_last_win`

**Current Status**: Minor point-in-time issue

**Issue**: 
- `years_since_last_win` is point-in-time safe ✅
- `age` uses `fighter.age` (current age) instead of age at fight time ⚠️

**Fix Required**:
1. Update `extract_physical_features()` to accept `as_of_date` parameter
2. Calculate age at fight time: `age_at_fight = (fight_date - date_of_birth).days / 365.25`
3. Pass `as_of_date` through context to physical features extraction

**Implementation**:
```python
# In extract_physical_features() - needs update:
def extract_physical_features(fighter: Fighter, as_of_date: Optional[datetime] = None) -> Dict[str, float]:
    # Calculate age at fight time if date_of_birth available
    if fighter.date_of_birth and as_of_date:
        try:
            dob = datetime.strptime(fighter.date_of_birth, "%b %d, %Y")
            fight_date = pd.to_datetime(as_of_date)
            age_at_fight = (fight_date - dob).days / 365.25
            age = age_at_fight
        except:
            age = fighter.age  # Fallback to stored age
    else:
        age = fighter.age  # Fallback to stored age
```

**Test Needed**: `tests/test_age_interactions_point_in_time.py`

---

## Quick Reference: What Needs Fixing

### ✅ Already Fixed (Can Re-enable)
- All striking features (28 features)
- All grappling features (4 features)
- **Total: 32 features ready to re-enable**

### ⚠️ Needs Verification
- `years_since_last_win` - Create unit test to verify

### ⚠️ Needs Fix
- `age_x_years_since_last_win` - Fix age calculation to use fight date

---

## Next Steps

1. ✅ **Completed**: Fixed all striking and grappling features
2. ⏳ **In Progress**: Verify `years_since_last_win` and `age_x_years_since_last_win`
3. 📋 **Pending**: Review why fixed features are still excluded
4. 📋 **Pending**: Decide whether to re-enable fixed features

---

## Related Documentation

- `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` - Fix for `sig_strikes_landed_per_min`
- `docs/STRIKING_DEFENSE_POINT_IN_TIME_FIX.md` - Fix for `striking_defense` and related
- `docs/GRAPPLING_POINT_IN_TIME_FIX.md` - Fix for grappling features
- `docs/POINT_IN_TIME_SAFETY_AUDIT.md` - Full audit of all features

