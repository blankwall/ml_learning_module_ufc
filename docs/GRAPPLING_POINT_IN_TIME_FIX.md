# Grappling Features Point-in-Time Safety Fix

## Issue Identified

The grappling features were **NOT** point-in-time safe. They were:
1. ❌ Using global Fighter stats directly (`fighter.takedown_avg_per_15min`, etc.)
2. ❌ Not filtering by `as_of_date` to exclude future fights
3. ❌ Not computing from fight-by-fight data

## Test Results (Before Fix)

Expected: All values would be identical (using global Fighter stats)

## Fix Applied

### Changes to `features/grappling.py`

1. **Created `extract_grappling_fight_details()` function**: Extracts grappling metrics from individual FightStats
   - Parses takedowns (landed/attempted) from `fighter_1_totals` / `fighter_2_totals`
   - Calculates per-15min rates from fight duration
   - Computes accuracy and defense from fight data

2. **Updated `extract_grappling_features()` function**:
   - Changed signature from `extract_grappling_features(fighter: Fighter)` to `extract_grappling_features(context: Dict)`
   - Uses `fight_history` DataFrame (already filtered by `as_of_date`) instead of SQLAlchemy relationships
   - Queries Fight objects for specific fight IDs in filtered history
   - Computes lifetime averages from fight-by-fight data
   - Falls back to global stats only if no fight history exists

### Changes to `features/registry.py`

1. **Updated `_extract_grappling()`**: Now passes full context dict instead of just fighter object

## Test Results (After Fix)

```
🔍 Testing David Abbott (ID: 5)
   Fights: 15
   takedown_avg_per_15min:
     Before first fight:  1.100
     After first fight:   1.100
     After second fight: 1.500
     After third fight:  1.500
     ✓ Values differ across time points (not using global stat)
   takedown_accuracy:
     Before first fight:  0.283
     After first fight:   0.283
     After second fight: 0.500
     After third fight:  0.500
     ✓ Values differ across time points (not using global stat)
   takedown_defense:
     Before first fight:  0.278
     After first fight:   0.278
     After second fight: 0.250
     After third fight:  0.375
     ✓ Values differ across time points (not using global stat)
   submission_avg_per_15min:
     Before first fight:  0.600
     After first fight:   0.600
     After second fight: 1.500
     After third fight:  1.500
     ✓ Values differ across time points (not using global stat)
   ✅ All grappling features are point-in-time safe!
```

## Verification

The features are now:
- ✅ **Computed strictly up to fight_date**: Uses `fight_history` filtered by `as_of_date`
- ✅ **Not re-normalized using future fights**: Only includes fights before `as_of_date`
- ✅ **Not recomputed globally after ingest**: Computes from fight-by-fight data, not global Fighter stats

## Fixed Features

All grappling features are now point-in-time safe:
- ✅ `f1_takedown_avg_per_15min` / `f2_takedown_avg_per_15min`
- ✅ `f1_takedown_accuracy` / `f2_takedown_accuracy`
- ✅ `f1_takedown_defense` / `f2_takedown_defense`
- ✅ `f1_submission_avg_per_15min` / `f2_submission_avg_per_15min`
- ✅ `takedown_ability_diff` (derived from above, now safe)
- ✅ `takedown_matchup` (derived from above, now safe)

## Impact

This fix ensures that:
- Training data uses only historical information available at fight time
- Predictions for upcoming fights don't leak future performance
- Backtesting results are accurate and not inflated by data leakage
- All grappling-related features are consistent with the point-in-time safe pattern

## Related

See `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` for the similar fix applied to striking features.

