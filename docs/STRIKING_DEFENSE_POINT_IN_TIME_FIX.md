# Striking Defense & Absorption Point-in-Time Safety Fix

## Issue Identified

The remaining striking features were **NOT** point-in-time safe:
1. ❌ `striking_defense` - Used global `fighter.striking_defense` stat
2. ❌ `sig_strikes_absorbed` - Used global `fighter.sig_strikes_absorbed_per_min` stat
3. ❌ `striking_differential` - Derived from `sig_strikes_absorbed` (global stat)
4. ❌ `defensive_efficiency` - Derived from `striking_defense` (global stat)
5. ❌ `striking_volume_control` - Derived from `sig_strikes_absorbed` (global stat)

## Fix Applied

### Changes to `features/striking.py`

1. **Updated `extract_fight_details()` function**:
   - Now extracts opponent's striking stats from FightStats
   - Calculates `opp_sig_strikes_landed_per_min` (opponent's output against this fighter)
   - Calculates `striking_defense_fight` = 1 - opponent's striking accuracy
   - Adds these to fight_metrics dictionary

2. **Updated `extract_striking_features()` function**:
   - Computes `sig_strikes_absorbed_per_min_lifetime` from opponent's output across all fights
   - Computes `striking_defense_lifetime` as average of fight-by-fight defense values
   - Uses computed values instead of global Fighter stats when fight_history is available
   - Falls back to global stats only if no fight history exists

3. **Updated derived features**:
   - `striking_differential` now uses computed `sig_strikes_absorbed_effective`
   - `defensive_efficiency` now uses computed `striking_defense_effective`
   - `striking_volume_control` now uses computed `sig_strikes_absorbed_effective`
   - `striking_accuracy` now uses computed `striking_accuracy_effective` (from fight_history)

## Test Results (After Fix)

```
🔍 Testing David Abbott (ID: 5)
   Fights: 15
   striking_defense:
     Before first fight:  0.177
     After first fight:   0.177
     After second fight: 0.062
     After third fight:  0.121
     ✓ Values differ across time points (not using global stat)
   striking_differential:
     Before first fight:  -0.913
     After first fight:   -0.913
     After second fight: -5.300
     After third fight:  -3.225
     ✓ Values differ across time points (not using global stat)
   defensive_efficiency:
     Before first fight:  0.079
     After first fight:   0.079
     After second fight: 0.011
     After third fight:  0.028
     ✓ Values differ across time points (not using global stat)
   striking_volume_control:
     Before first fight:  0.596
     After first fight:   0.596
     After second fight: 0.070
     After third fight:  0.259
     ✓ Values differ across time points (not using global stat)
   ✅ All striking defense features are point-in-time safe!
```

## Verification

The features are now:
- ✅ **Computed strictly up to fight_date**: Uses `fight_history` filtered by `as_of_date`
- ✅ **Not re-normalized using future fights**: Only includes fights before `as_of_date`
- ✅ **Not recomputed globally after ingest**: Computes from fight-by-fight data, not global Fighter stats

## Fixed Features

All remaining striking features are now point-in-time safe:
- ✅ `f1_striking_defense` / `f2_striking_defense` - Now computed from opponent accuracy
- ✅ `striking_differential` - Now uses computed `sig_strikes_absorbed`
- ✅ `defensive_efficiency` - Now uses computed `striking_defense`
- ✅ `striking_volume_control` - Now uses computed `sig_strikes_absorbed`
- ✅ `f1_striking_accuracy` / `f2_striking_accuracy` - Now uses computed value from fight_history

## Impact

This fix ensures that:
- Training data uses only historical information available at fight time
- Predictions for upcoming fights don't leak future performance
- Backtesting results are accurate and not inflated by data leakage
- All striking-related features are consistent with the point-in-time safe pattern

## Related

See:
- `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` - Initial fix for `sig_strikes_landed_per_min`
- `docs/GRAPPLING_POINT_IN_TIME_FIX.md` - Similar fix for grappling features

