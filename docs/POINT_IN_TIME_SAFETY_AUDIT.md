# Point-in-Time Safety Audit for Feature Schema

This document lists features from `schema/feature_schema.json` that should be verified for point-in-time safety.

## Risk Categories

- 🔴 **HIGH RISK**: Uses global Fighter stats directly (not computed from fight_history)
- 🟡 **MEDIUM RISK**: Derived from high-risk features or may have edge cases
- 🟢 **LOW RISK**: Uses fight_history (should be safe if properly filtered)
- ✅ **VERIFIED SAFE**: Already confirmed point-in-time safe
- ⚪ **STATIC**: Physical attributes or matchup features (always safe)

---

## 🔴 HIGH RISK - Require Immediate Attention

These features use global Fighter stats that could be updated after ingest:

### Striking Features (from `features/striking.py`)
- ✅ `f1_sig_strikes_landed_per_min` - **FIXED** (now uses fight_history)
- ✅ `f1_striking_accuracy` - **FIXED** (now uses fight_history, falls back to global stat only if no history)
- ✅ `f1_striking_defense` - **FIXED** (now computed from opponent accuracy in fight_history)
- ✅ `f2_striking_defense` - **FIXED** (same as above)
- ✅ `striking_differential` - **FIXED** (now uses computed `sig_strikes_absorbed` from fight_history)
- ✅ `defensive_efficiency` - **FIXED** (now uses computed `striking_defense` from fight_history)
- ✅ `striking_volume_control` - **FIXED** (now uses computed `sig_strikes_absorbed` from fight_history)

**Note**: All striking features now compute from fight_history. Global Fighter stats are only used as fallback when no fight history exists.

### Grappling Features (from `features/grappling.py`)
- 🔴 `f1_takedown_avg_per_15min` - **Uses global `fighter.takedown_avg_per_15min`**
- 🔴 `f1_takedown_accuracy` - **Uses global `fighter.takedown_accuracy`**
- 🔴 `f1_takedown_defense` - **Uses global `fighter.takedown_defense`**
- 🔴 `f1_submission_avg_per_15min` - **Uses global `fighter.submission_avg_per_15min`**
- 🔴 `f2_takedown_avg_per_15min` - Same issue
- 🔴 `f2_takedown_accuracy` - Same issue
- 🔴 `f2_takedown_defense` - Same issue
- 🔴 `f2_submission_avg_per_15min` - Same issue
- 🔴 `takedown_ability_diff` - Derived from grappling features (uses global stats)
- 🔴 `takedown_matchup` - Derived from grappling features (uses global stats)

**Note**: All grappling features use global Fighter stats. There's no computation from fight_history.

---

## 🟡 MEDIUM RISK - Derived Features or Edge Cases

### Power Striker Score
- 🟡 `f1_power_striker_score` - Uses components from fight_history, but depends on:
  - `ko_rate_last_5` (from fight_history ✅)
  - `first_round_ko_rate` (from fight_history ✅)
  - `knockdowns_lifetime` (from striking_features, which uses fight_history ✅)
  - `head_strike_rate_lifetime` (from striking_features, which uses fight_history ✅)
  
  **Status**: Should be safe since all components use fight_history, but verify.

### Striking Output Diff
- 🟡 `striking_output_diff` - Computed as `sig_strikes_landed_per_min` diff (now safe ✅)

---

## 🟢 LOW RISK - Use fight_history (Should Be Safe)

These features use `fight_history` DataFrame which is filtered by `as_of_date`:

### Time-Based Features
- `f1_current_win_streak`, `f1_current_loss_streak`
- `f1_days_since_last_fight`, `f1_days_between_last_2_fights`
- `f1_fights_in_last_year`, `f1_activity_rate`
- `f1_long_layoff_over_1yr`, `f1_long_layoff_over_2yr`
- `f1_fights_since_last_win`
- `f1_win_rate_last_3`, `f1_win_rate_last_5`, `f1_win_rate_last_3_years`
- `f1_finish_rate`, `f1_finish_rate_last_3`, `f1_finish_rate_last_5`
- `f1_ko_rate`, `f1_ko_rate_last_3`, `f1_ko_rate_last_5`
- `f1_submission_rate`
- `f1_decision_rate`
- `f1_time_decayed_win_rate`, `f1_time_decayed_finish_rate`, `f1_time_decayed_ko_rate`
- `f1_early_finish_rate_last_3`, `f1_early_finish_rate_last_5`
- `f1_first_round_finish_rate`, `f1_first_round_ko_rate`
- `f1_round_3_fight_rate`, `f1_round_3_finish_rate`, `f1_round_3_win_rate`
- All `f2_*` equivalents

### Recent Performance Features (from FightStats)
- `f1_recent_sig_strike_diff_last_3` - Uses `extract_recent_striking_features` ✅
- `f1_recent_knockdown_diff_last_3` - Uses `extract_recent_striking_features` ✅
- `f1_recent_control_time_sec_last_3` - Uses `extract_recent_grappling_features` ✅
- `f1_recent_control_time_diff_last_3` - Uses `extract_recent_grappling_features` ✅
- `f1_recent_finish_loss_last_fight` - Uses fight_history ✅
- `f1_recent_finish_losses_last_2` - Uses fight_history ✅
- All `f2_*` equivalents

### Career Stats
- `f1_total_fights`, `f1_wins`, `f1_losses`, `f1_draws` - Computed from fight_history ✅
- `f1_wins_last_3_years`, `f1_losses_last_3_years` - Computed from fight_history ✅
- `f1_has_ever_won`, `f1_has_fight_history` - Computed from fight_history ✅
- `f1_title_fight_experience` - Computed from fight_history ✅
- All `f2_*` equivalents

### Opponent Quality
- `f1_avg_opponent_win_rate` - Uses fight_history + get_fighter_record ✅
- `f1_avg_beaten_opponent_win_rate` - Uses fight_history ✅
- `f1_avg_lost_to_opponent_win_rate` - Uses fight_history ✅
- `f1_opponent_quality_score` - Uses fight_history ✅
- All `f2_*` equivalents

### Striking Features (from fight_history)
- `f1_sig_strikes_landed_per_min` - ✅ **FIXED** (now uses fight_history)
- `f1_striking_accuracy` - Uses fight_history if available ✅
- All `*_last_3` and `*_lifetime` striking metrics - Computed from fight_history ✅
  - `distance_accuracy_last_3`, `clinch_accuracy_last_3`, etc.
  - `head_strike_rate_last_3`, `body_strike_rate_last_3`, etc.
  - `knockdowns_last_3`, `knockdowns_lifetime`

---

## ⚪ STATIC - Always Safe

### Physical Features
- `f1_age`, `f1_height_cm`, `f1_weight_lbs`, `f1_reach_inches`
- `f1_stance_orthodox`, `f1_stance_southpaw`, `f1_stance_switch`
- `f1_age_in_prime`, `f1_age_past_prime`
- All `f2_*` equivalents
- `age_difference`, `height_advantage`, `reach_advantage`

### Matchup Features
- `is_title_fight`
- `orthodox_vs_orthodox`, `orthodox_vs_southpaw`, `southpaw_vs_southpaw`
- `both_strikers`, `both_grapplers`, `both_finishers`
- `striker_vs_grappler`
- `power_striker_matchup`
- `takedown_matchup` (derived from grappling features, but matchup is safe)

### Age Interaction Features
- `f1_age_x_days_since_last_fight`, `f1_age_x_fights_in_last_year`, etc.
- All age interaction features use fight_history for the time component ✅

---

## ✅ VERIFIED SAFE

- ✅ `f1_sig_strikes_landed_per_min` - Fixed to use fight_history
- ✅ `f2_sig_strikes_landed_per_min` - Fixed to use fight_history

---

## Summary: Features Requiring Verification

### Critical (Use Global Stats):
1. **`f1_striking_defense`** / **`f2_striking_defense`** - Only from global Fighter stat
2. **`f1_takedown_avg_per_15min`** / **`f2_takedown_avg_per_15min`** - Only from global Fighter stat
3. **`f1_takedown_accuracy`** / **`f2_takedown_accuracy`** - Only from global Fighter stat
4. **`f1_takedown_defense`** / **`f2_takedown_defense`** - Only from global Fighter stat
5. **`f1_submission_avg_per_15min`** / **`f2_submission_avg_per_15min`** - Only from global Fighter stat

### Important (Derived from Global Stats):
6. **`striking_differential`** - Uses `sig_strikes_absorbed` (global stat)
7. **`defensive_efficiency`** - Uses `striking_defense` (global stat)
8. **`striking_volume_control`** - Uses `sig_strikes_absorbed` (global stat)
9. **`takedown_ability_diff`** - Derived from grappling features (global stats)
10. **`takedown_matchup`** - Derived from grappling features (global stats)

### Should Verify (Components May Use Global Stats):
11. **`f1_power_striker_score`** / **`f2_power_striker_score`** - Verify all components use fight_history
12. **`f1_striking_accuracy`** / **`f2_striking_accuracy`** - Verify fallback behavior is acceptable

---

## Recommended Actions

1. **Priority 1**: Fix grappling features to compute from fight_history (similar to striking fix)
2. **Priority 2**: Compute `striking_defense` and `sig_strikes_absorbed` from fight_history
3. **Priority 3**: Verify `power_striker_score` components all use fight_history
4. **Priority 4**: Add unit tests for all high-risk features (similar to `test_sig_strikes_point_in_time.py`)

---

## Notes

- Most features that use `fight_history` are safe because `get_fight_history()` filters by `as_of_date`
- The main risk is features that use global Fighter stats directly
- Even if a feature is "computed" from fight_history, verify it's using the filtered history, not `fighter.fights_as_fighter_1/2`
- The `extract_recent_*` features are safe because they explicitly use `fight_history` parameter

