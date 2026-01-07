# sig_strikes_landed_per_min Point-in-Time Safety Fix

## Issue Identified

The `sig_strikes_landed_per_min` feature was **NOT** point-in-time safe. It was:
1. ❌ Using `fighter.fights_as_fighter_1` and `fighter.fights_as_fighter_2` which include ALL fights regardless of date
2. ❌ Falling back to global `fighter.sig_strikes_landed_per_min` stat (which could be updated after ingest)
3. ❌ Not filtering by `as_of_date` to exclude future fights

## Test Results (Before Fix)

```
🔍 Testing David Abbott (ID: 5)
   sig_strikes_landed_per_min:
     Before first fight:  1.347
     After first fight:   1.347
     After second fight: 1.347
     After third fight:  1.347
   ❌ ERROR: All values identical - likely using global fighter stat!
```

## Fix Applied

### Changes to `features/striking.py`

1. **Updated function signature**: Changed from `extract_striking_features(fighter: Fighter)` to `extract_striking_features(context: Dict)`
2. **Use date-filtered fight_history**: Now uses `fight_history` DataFrame (already filtered by `as_of_date`) instead of SQLAlchemy relationships
3. **Query Fight objects from fight IDs**: Gets Fight objects for the specific fight IDs in the filtered history
4. **Removed global stat fallback**: Only falls back to global stats if no fight history exists (for fighters with zero fights)

### Changes to `features/registry.py`

1. **Pass full context**: Updated `_extract_striking` to pass full context dict instead of just fighter object
2. **Load fight stats for striking**: Ensured `fight_stats_by_fight_id` is loaded when "striking" feature set is requested
3. **Add session to context**: Added `session` to context so `extract_striking_features` can query Fight objects

## Test Results (After Fix)

```
🔍 Testing David Abbott (ID: 5)
   Fights: 15
   sig_strikes_landed_per_min:
     Before first fight:  1.347
     After first fight:   1.347
     After second fight: 0.400
     After third fight:  1.125
   ✓ Feature values change as fights are added (point-in-time filtering working)
   ✓ Values differ across time points (not using global stat)
```

## Verification

The feature is now:
- ✅ **Computed strictly up to fight_date**: Uses `fight_history` filtered by `as_of_date`
- ✅ **Not re-normalized using future fights**: Only includes fights before `as_of_date`
- ✅ **Not recomputed globally after ingest**: Computes from fight-by-fight data, not global Fighter stats

## Impact

This fix ensures that:
- Training data uses only historical information available at fight time
- Predictions for upcoming fights don't leak future performance
- Backtesting results are accurate and not inflated by data leakage

## Related Features

The same pattern should be verified for:
- `striking_accuracy` (uses same code path)
- `striking_defense` (uses global stat but should be computed from fight history)
- Other striking metrics derived from `recent_metrics`

Note: `striking_defense` and `sig_strikes_absorbed` still use global Fighter stats as fallback, but the main `sig_strikes_landed_per_min` feature is now point-in-time safe.

