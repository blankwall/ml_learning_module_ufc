# Next Steps for Feature Auditing

The automated audit is now clean! Here's what to do next for comprehensive feature validation:

## ✅ Completed

1. **Automated Audit** - Fixed bugs and false positives
2. **Opponent Quality Score** - Fixed backwards penalty logic
3. **Strike Rate Normalization** - Fixed to handle data inconsistencies

## 🔍 Next Steps

### 1. Feature Distribution Analysis

Run distribution validator to check for outliers and anomalies:

```bash
/Users/tylerbohan/code/ufc_analysis_v2/.venv/bin/python scripts/validate_feature_distributions.py
```

**What to look for:**
- Extreme outliers (99th percentile >> median)
- Unexpected negative values
- Infinite or NaN values
- Features with zero variance (all same value)

### 2. Test Known Fighters

Validate features against fighters with known characteristics:

```bash
/Users/tylerbohan/code/ufc_analysis_v2/.venv/bin/python scripts/test_known_fighters.py
```

**Test cases:**
- Elite fighters who lost to elite opponents (Strickland) → should have positive opponent_quality_score
- Undefeated fighters → win_rate_last_3 = 1.0
- Fighters with only losses → should handle gracefully
- Fighters with gaps in history → should handle time windows correctly

### 3. Manual Code Review

Review high-impact features manually:

#### Priority 1: Time-Decayed Features
- **File**: `features/time_based.py`
- **Check**: Does `time_decayed_win_rate` properly weight recent fights?
- **Test**: Fighter with old wins but recent losses should have low time_decayed_win_rate

#### Priority 2: Rolling Statistics  
- **File**: `features/time_based.py` → `extract_rolling_stats`
- **Check**: "Last 3" uses exactly 3 most recent fights (sorted by date)
- **Test**: Fighter with 5 fights, check that last_3 uses fights 1, 2, 3 (most recent)

#### Priority 3: Differential Features
- **File**: `features/matchup_features.py` → `_calculate_differentials`
- **Check**: All differentials have correct direction (positive = f1 advantage)
- **Test**: If f1 is better, differentials should be positive

#### Priority 4: Grappling Features
- **File**: `features/grappling.py`
- **Check**: Takedown accuracy, control time calculations
- **Test**: Similar to striking - check for normalization issues

### 4. Compare Predictions to Market

Identify fights where model differs significantly from betting odds:

```bash
# Run predictions for recent fights
# Compare to actual betting odds
# Flag fights with >20% difference
```

**What to investigate:**
- Which features are driving the difference?
- Are those features calculated correctly?
- Is there a logical error in those features?

### 5. Edge Case Testing

Test specific scenarios:

#### Scenario 1: Fighter with 1 fight
- Should all "last_3" features use that 1 fight?
- Should lifetime = last_3?

#### Scenario 2: Fighter with 10-year gap
- Does time_decayed properly down-weight old fights?
- Are recent features using correct time window?

#### Scenario 3: Fighter who only fights elite opponents
- Does opponent_quality_score reflect this?
- Are they penalized for losses to elite fighters?

### 6. Feature Importance Review

Check feature importance for anomalies:

```bash
# Review models/saved/xgboost_model_feature_importance.csv
```

**Questions to ask:**
- Are the most important features intuitive?
- Are there features with unexpectedly high/low importance?
- Do interaction features make sense?

### 7. Cross-Validation Checks

Verify related features are consistent:

- `win_rate_last_3` should match `wins_last_3 / 3` (if exactly 3 fights)
- `time_decayed_win_rate` should be between `win_rate_last_3` and career win_rate
- Strike rates should sum to ~1.0 (already checked)
- Opponent quality should correlate with fighter's record quality

### 8. Data Quality Checks

Verify source data is correct:

- Check a few fights manually in the database
- Verify fight stats parsing is correct
- Check date parsing (some fights might have wrong dates)

## 🎯 Recommended Order

1. **Distribution Analysis** (quick, automated)
2. **Known Fighter Tests** (validates fixes work)
3. **Manual Code Review** (high-impact features first)
4. **Prediction Comparison** (finds real-world issues)
5. **Edge Case Testing** (ensures robustness)

## 📊 Success Criteria

Features are validated when:
- ✅ Automated audit passes
- ✅ Distributions look reasonable
- ✅ Known fighters have expected values
- ✅ Predictions align with market (within reason)
- ✅ Edge cases handled gracefully
- ✅ No logical errors in high-impact features

## 🐛 What to Look For

**Red Flags:**
- Features that don't match intuition
- Extreme outliers without explanation
- Predictions that seem wrong for known fighters
- Features with unexpected importance
- Inconsistencies between related features

**Good Signs:**
- Features match expected values for known fighters
- Distributions are reasonable
- Predictions align with market
- Edge cases handled gracefully
- Feature importance makes sense

