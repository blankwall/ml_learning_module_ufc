# Features Requiring Point-in-Time Safety Verification

Based on analysis of `schema/feature_schema.json`, here are the features that should be verified for point-in-time safety.

## 📊 Current Status Summary

- ✅ **All Critical Features Fixed**: Grappling and striking features are now point-in-time safe
- ⚠️ **1 Feature Needs Verification**: `power_striker_score` (components appear safe, verify)
- ✅ **All Other Features**: Already safe or verified

**Last Updated**: After grappling and striking defense fixes (January 2026)

## 🔴 CRITICAL - Use Global Fighter Stats (High Priority)

**NOTE**: This section is now empty - all critical features have been fixed! ✅

~~All features that were in this section have been fixed:~~
- ~~Grappling features~~ → ✅ **FIXED** (see below)
- ~~Striking defense features~~ → ✅ **FIXED** (see below)
- ~~Striking absorption features~~ → ✅ **FIXED** (see below)

---

## 🟡 MEDIUM PRIORITY - Verify Components

### Power Striker Score
1. **`f1_power_striker_score`** / **`f2_power_striker_score`**

**Status**: Uses components from fight_history, verify all components are point-in-time safe:
- `ko_rate_last_5` ✅ (from fight_history)
- `first_round_ko_rate` ✅ (from fight_history)
- `knockdowns_lifetime` ✅ (from striking_features using fight_history)
- `head_strike_rate_lifetime` ✅ (from striking_features using fight_history)

**Action**: Verify all components use fight_history (should be safe, but worth confirming).

---

## ✅ ALREADY VERIFIED SAFE

### Striking Features - **ALL FIXED** ✅
- ✅ `f1_sig_strikes_landed_per_min` / `f2_sig_strikes_landed_per_min` - **FIXED** (uses fight_history)
- ✅ `f1_striking_accuracy` / `f2_striking_accuracy` - **FIXED** (uses fight_history)
- ✅ `f1_striking_defense` / `f2_striking_defense` - **FIXED** (computed from opponent accuracy)
- ✅ `striking_differential` - **FIXED** (uses computed `sig_strikes_absorbed`)
- ✅ `defensive_efficiency` - **FIXED** (uses computed `striking_defense`)
- ✅ `striking_volume_control` - **FIXED** (uses computed `sig_strikes_absorbed`)
- ✅ All `*_last_3` and `*_lifetime` striking metrics - **FIXED** (computed from fight_history)

**Documentation**: See `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` and `docs/STRIKING_DEFENSE_POINT_IN_TIME_FIX.md`

### Grappling Features - **ALL FIXED** ✅
- ✅ `f1_takedown_avg_per_15min` / `f2_takedown_avg_per_15min` - **FIXED** (computed from fight_history)
- ✅ `f1_takedown_accuracy` / `f2_takedown_accuracy` - **FIXED** (computed from fight_history)
- ✅ `f1_takedown_defense` / `f2_takedown_defense` - **FIXED** (computed from opponent takedown accuracy)
- ✅ `f1_submission_avg_per_15min` / `f2_submission_avg_per_15min` - **FIXED** (computed from fight_history)
- ✅ `takedown_ability_diff` - **FIXED** (derived from fixed grappling features)
- ✅ `takedown_matchup` - **FIXED** (derived from fixed grappling features)

**Documentation**: See `docs/GRAPPLING_POINT_IN_TIME_FIX.md`

### Other Safe Features
- ✅ All time-based features (win_rate, finish_rate, etc.) - Use fight_history
- ✅ All recent performance features - Use fight_history
- ✅ All career stats - Computed from fight_history
- ✅ All physical features - Static attributes

---

## Recommended Testing Approach

For each feature above, create a test similar to `tests/test_sig_strikes_point_in_time.py`:

1. Extract features at different points in time (before/after fights)
2. Verify values change as fights are added (not using global stat)
3. Verify values don't include future fights

---

## Quick Reference: Feature Locations

- **Grappling**: `features/grappling.py` → `extract_grappling_features()` ✅ **FIXED**
- **Striking**: `features/striking.py` → `extract_striking_features()` ✅ **FIXED**
- **Power Striker**: `features/time_based.py` → `extract_power_striker_score()` ⚠️ Verify components
- **Registry**: `features/registry.py` → `_extract_grappling()`, `_extract_striking()`, `_extract_power_striker()`

---

## Fix Pattern (Reference)

All critical features have been fixed using this pattern. See documentation for details:

1. **Striking Features**: `docs/SIG_STRIKES_POINT_IN_TIME_FIX.md` and `docs/STRIKING_DEFENSE_POINT_IN_TIME_FIX.md`
2. **Grappling Features**: `docs/GRAPPLING_POINT_IN_TIME_FIX.md`

### Common Fix Pattern:
1. Change function signature to accept `context` dict
2. Use `fight_history` from context (already filtered by `as_of_date`)
3. Query Fight objects for fight IDs in filtered history
4. Compute metrics from fight-by-fight data
5. Remove fallback to global Fighter stats (or make it explicit)

### Test Files Created:
- `tests/test_sig_strikes_point_in_time.py` - Verifies `sig_strikes_landed_per_min`
- `tests/test_striking_defense_point_in_time.py` - Verifies `striking_defense` and related
- `tests/test_grappling_point_in_time.py` - Verifies all grappling features

