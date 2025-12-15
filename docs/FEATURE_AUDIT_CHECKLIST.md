# Feature Audit Checklist

This document provides a systematic checklist for auditing features to find logical errors, edge cases, and bugs similar to the `opponent_quality_score` bug we found.

## The Bug We Found

**Issue:** `opponent_quality_score` was penalizing losses to elite fighters when it should penalize losses to weak fighters.

**Root Cause:** Formula was `raw_score = avg_beaten_opp_wr - avg_lost_opp_wr`, which penalized losing to good opponents.

**Fix:** Changed to `raw_score = avg_beaten_opp_wr - (1 - avg_lost_opp_wr)`, which penalizes losing to weak opponents.

## Audit Checklist

### 1. Direction/Logic Errors

Check for calculations that might be backwards or have incorrect direction:

- [ ] **Penalties vs Rewards**: Are penalties applied correctly?
  - Example: Losing to elite fighters shouldn't hurt as much as losing to weak fighters
  - Check: Any feature that penalizes "bad" outcomes - verify the penalty direction

- [ ] **Differential Features**: Do differentials make sense?
  - Example: `striking_output_diff = f1 - f2` - positive means f1 advantage (correct)
  - Check: All `_diff` features have correct direction

- [ ] **Rate Calculations**: Are rates calculated correctly?
  - Example: `win_rate = wins / total_fights` (correct)
  - Check: All rate features use correct numerator/denominator

### 2. Edge Cases

Test with edge case scenarios:

- [ ] **No Fight History**: Fighter with 0 fights
  - Should return default values (0.0, not None)
  - Should not crash

- [ ] **Perfect Records**: Fighter with only wins or only losses
  - Win-only: Loss-related features should handle gracefully
  - Loss-only: Win-related features should handle gracefully

- [ ] **Single Fight**: Fighter with only 1 fight
  - Rolling averages should handle single data point
  - "Last 3" features should handle < 3 fights

- [ ] **Division by Zero**: Check all divisions
  - `accuracy = landed / attempted` - handle `attempted == 0`
  - `rate = value / total` - handle `total == 0`

### 3. Sanity Checks

Verify values are in expected ranges:

- [ ] **Rates (0-1)**: Win rates, accuracy rates, finish rates
  - Should be between 0.0 and 1.0
  - Check: `win_rate`, `striking_accuracy`, `finish_rate`, etc.

- [ ] **Counts (≥0)**: Wins, losses, total fights
  - Should be non-negative integers
  - Check: `wins`, `losses`, `total_fights`, `knockdowns`, etc.

- [ ] **Per-Minute Rates (≥0)**: Strikes per minute, takedowns per 15min
  - Should be non-negative
  - Check: `sig_strikes_landed_per_min`, `takedown_avg_per_15min`, etc.

- [ ] **Scores**: Quality scores, performance scores
  - Check bounds are reasonable
  - Check: `opponent_quality_score`, `performance_score`, etc.

### 4. Consistency Checks

Verify related features are consistent:

- [ ] **Win Rate Consistency**: `win_rate == wins / total_fights`
- [ ] **Strike Rate Consistency**: `head_rate + body_rate + leg_rate ≈ 1.0`
- [ ] **Finish Rate Consistency**: `finish_rate == (ko_rate + sub_rate)`
- [ ] **Time Windows**: `win_rate_last_3` should use last 3 fights, not all fights

### 5. Feature-Specific Checks

#### Opponent Quality Features
- [ ] Losing to elite fighters (0.8+ win rate) doesn't heavily penalize score
- [ ] Losing to weak fighters (0.3- win rate) heavily penalizes score
- [ ] Beating good opponents increases score
- [ ] Score accounts for sample size (few fights = less confident)

#### Time-Decayed Features
- [ ] Recent fights weighted more heavily than old fights
- [ ] Very old fights (5+ years) have minimal weight
- [ ] Handles fighters with gaps in fight history

#### Rolling Statistics
- [ ] "Last 3" uses exactly 3 most recent fights
- [ ] "Last 5" uses exactly 5 most recent fights
- [ ] Handles fighters with < 3 or < 5 fights

#### Striking Features
- [ ] Accuracy = landed / attempted (not attempted / landed)
- [ ] Strike rates sum to ~1.0 (head + body + leg)
- [ ] Per-minute rates account for fight duration

#### Grappling Features
- [ ] Takedown accuracy = successful / attempted
- [ ] Control time features account for fight duration
- [ ] Submission rate = submissions / wins

## Running the Audit

### Automated Audit Script

```bash
python scripts/audit_features.py
```

This will:
- Test all feature modules with sample fighters
- Check for logical errors, edge cases, sanity checks, and consistency
- Generate a report of potential issues

### Manual Review Process

1. **For each feature module:**
   - Read the code
   - Identify the calculation logic
   - Test with known examples (like Strickland losing to Du Plessis)
   - Verify edge cases (no fights, perfect records, etc.)

2. **Test with real fighters:**
   - Use fighters with known characteristics
   - Verify features match expectations
   - Check for counterintuitive values

3. **Compare to market:**
   - If model prediction differs significantly from betting odds
   - Investigate which features are driving the difference
   - Check if those features have logical errors

## Common Bug Patterns

### Pattern 1: Backwards Penalties
**Example:** Penalizing losses to elite fighters
**Fix:** Invert the penalty calculation

### Pattern 2: Missing Edge Case Handling
**Example:** Division by zero when no fights
**Fix:** Add default values or safe division

### Pattern 3: Wrong Time Window
**Example:** "Last 3" using all fights instead of recent 3
**Fix:** Sort by date and take first N

### Pattern 4: Inconsistent Aggregation
**Example:** Using mean when sum is more appropriate
**Fix:** Use correct aggregation method

### Pattern 5: Missing Context
**Example:** Not accounting for opponent quality in win rate
**Fix:** Add opponent-quality-adjusted metrics

## Review Priority

Focus on these high-impact features first:

1. **Opponent Quality** (already fixed)
2. **Time-Decayed Features** (high importance, might have similar issues)
3. **Rolling Statistics** (used heavily, check time windows)
4. **Differential Features** (check direction)
5. **Striking/Grappling Rates** (check consistency)

## Questions to Ask

For each feature, ask:

1. **Does the direction make sense?** (Higher value = better?)
2. **What happens with edge cases?** (No fights, perfect records, etc.)
3. **Are the bounds reasonable?** (Values in expected range?)
4. **Is it consistent?** (Related features agree?)
5. **Does it match intuition?** (Strickland losing to Du Plessis shouldn't hurt much)

## Next Steps After Audit

1. Fix identified bugs
2. Retrain model with corrected features
3. Validate predictions improve
4. Document fixes for future reference
5. Add unit tests to prevent regression

