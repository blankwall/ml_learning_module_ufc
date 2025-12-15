# Feature Audit Results

## Summary

Found 25 potential issues, but many are false positives. Here's the breakdown:

## False Positives (Not Bugs)

### 1. `activity_rate > 1.0` ✅ CORRECT
- **Issue**: Values of 2.0, 3.0, 4.0 reported
- **Reality**: `activity_rate` is fights per year, not a 0-1 rate
- **Fix**: Updated audit to skip this check for `activity_rate`

### 2. `recent_vs_career_win_rate < 0` ✅ CORRECT  
- **Issue**: Negative values (-0.2, -0.255) reported
- **Reality**: This is a difference metric (recent - career). Negative = declining, which is valid
- **Fix**: Updated audit to exclude difference/decline features from non-negative checks

### 3. `avg_opponent_total_fights` not integer ✅ CORRECT
- **Issue**: Float values (26.5, 27.47) reported
- **Reality**: These are averages, should be floats
- **Fix**: Updated audit to exclude "avg" and "mean" features from integer checks

## Real Issues to Investigate

### 1. Strike Rate Consistency ⚠️ POTENTIAL BUG

**Issue**: Head + Body + Leg strike rates not summing to ~1.0

**Expected**: `head_strike_rate + body_strike_rate + leg_strike_rate ≈ 1.0`

**Found Values**: 0.0, 1.6, 2.0

**Possible Causes**:
1. **Data Quality**: Fight stats might have double-counting or missing data
2. **Calculation Error**: Rates might be calculated incorrectly
3. **Edge Case**: Fighters with no strikes (0.0 sum is OK)
4. **Missing Data**: Some strike types might not be recorded

**Investigation Needed**:
- Check if `head_landed + body_landed + leg_landed = sig_total_landed`
- Verify data quality in fight stats
- Check edge cases (fighters with very few strikes)

**Code Location**: `features/striking.py` lines 78-82

**Calculation**:
```python
'leg_strike_rate': leg_landed / sig_total_landed if sig_total_landed > 0 else 0,
'body_strike_rate': body_landed / sig_total_landed if sig_total_landed > 0 else 0,
'head_strike_rate': head_landed / sig_total_landed if sig_total_landed > 0 else 0,
```

**Expected**: If `head_landed + body_landed + leg_landed = sig_total_landed`, then rates should sum to 1.0

## Next Steps

1. **Investigate Strike Rate Issue**:
   - Add validation: `assert abs(head_rate + body_rate + leg_rate - 1.0) < 0.01`
   - Check data quality for fighters with sum ≠ 1.0
   - Verify fight stats parsing is correct

2. **Run Updated Audit**:
   - Re-run with fixed checks
   - Should reduce false positives significantly

3. **Manual Review**:
   - Check fighters with strike rate sum = 2.0 (definitely wrong)
   - Check fighters with strike rate sum = 0.0 (might be OK if no strikes)

## Updated Audit Script

The audit script has been updated to:
- Skip `activity_rate` from 0-1 rate checks
- Exclude difference/decline features from non-negative checks  
- Exclude averages from integer checks
- Better handle strike rate checks (separate target area vs position)

Run again with: `python scripts/audit_features.py`

