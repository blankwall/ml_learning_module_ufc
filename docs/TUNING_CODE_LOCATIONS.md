# Code Locations for Tuning Strickland Prediction

## Option 1: Further Reduce Elite Loss Penalty ⭐ RECOMMENDED FIRST

**File:** `features/time_based.py`  
**Lines:** 483-490

**Current Code:**
```python
elif row["result"] == "loss":
    # Loss: negative score, but loss to elite opponent is MUCH less penalized
    # For elite opponent (0.8+ win rate): multiplier ~1.7
    # For weak opponent (0.3 win rate): multiplier ~0.95
    # Use squared multiplier in denominator to make elite losses much less penalized
    # Loss to elite (1.7x): -1.0 / (1.7^2) = -1.0 / 2.89 = -0.346 (much better!)
    # Loss to weak (0.95x): -1.0 / (0.95^2) = -1.0 / 0.90 = -1.11 (still bad)
    score_contribution = -1.0 / (opponent_quality_multiplier ** 2)
```

**Change Options:**
- **Cubic:** `score_contribution = -1.0 / (opponent_quality_multiplier ** 3)`
  - Loss to elite (1.7x): -1.0 / (1.7^3) = -0.203 (even less penalty!)
  - Loss to weak (0.95x): -1.0 / (0.95^3) = -1.17
  
- **Capped:** `score_contribution = max(-0.5, -1.0 / (opponent_quality_multiplier ** 2))`
  - Maximum penalty of -0.5 for any loss
  
- **Exponential:** `score_contribution = -1.0 * np.exp(-opponent_quality_multiplier)`
  - More aggressive reduction for elite opponents

**Also Update Normalization:** Lines 509-518
- If you change the penalty formula, update the normalization range calculation
- Current: `normalized_score = (avg_score + 4.0) / 6.0`
- May need adjustment based on new min/max values

---

## Option 2: Increase Opponent Quality Multiplier

**File:** `features/time_based.py`  
**Lines:** 470-473

**Current Code:**
```python
opp_win_rate = record["win_rate"]
# Normalize opponent quality: 0.5 = average, 1.0 = elite, 0.0 = weak
# Scale from [0, 1] to [0.5, 1.5] so average opponent = 1.0x multiplier
opponent_quality_multiplier = 0.5 + (opp_win_rate * 1.5)
```

**Change Options:**
- **Stronger:** `opponent_quality_multiplier = 0.3 + (opp_win_rate * 2.0)`
  - Range: [0.3, 2.3] - stronger differentiation
  
- **Even Stronger:** `opponent_quality_multiplier = 0.5 + (opp_win_rate * 2.5)`
  - Range: [0.5, 3.0] - very strong differentiation

**Also Update Normalization:** Lines 509-518
- Update the range calculation in comments and normalization formula
- New range will affect the normalization denominator

---

## Option 3: Add Explicit "Elite Loss Context" Feature

**File:** `features/time_based.py`  
**Location:** Add new function after `extract_opponent_quality_adjusted_time_decayed_features` (around line 520)

**New Function to Add:**
```python
def extract_elite_loss_adjustment(
    fight_history: pd.DataFrame,
    get_fighter_record: Callable[[int], Optional[Dict]],
    lambda_decay: float = 0.3,
    elite_threshold: float = 0.75
) -> Dict[str, float]:
    """
    Calculate adjustment for fighters who lost to elite opponents.
    
    This directly rewards fighters who lost to high-quality opponents,
    addressing the case where a loss to an elite fighter shouldn't hurt much.
    """
    if len(fight_history) == 0:
        return {"elite_loss_adjustment": 0.0}
    
    if "event_date_parsed" not in fight_history.columns or "opponent_id" not in fight_history.columns:
        return {"elite_loss_adjustment": 0.0}
    
    now = datetime.now()
    total_adjustment = 0.0
    total_weight = 0.0
    
    for _, row in fight_history.iterrows():
        if row["result"] != "loss":
            continue
            
        try:
            fight_date = row["event_date_parsed"]
            years_ago = (now - fight_date).days / 365.25
            time_weight = np.exp(-lambda_decay * years_ago)
            
            opponent_id = row.get("opponent_id")
            if pd.isna(opponent_id):
                continue
                
            record = get_fighter_record(int(opponent_id))
            if record and record.get("win_rate") is not None:
                opp_win_rate = record["win_rate"]
                if opp_win_rate >= elite_threshold:
                    # Lost to elite opponent - give bonus
                    # More recent = higher bonus, more elite = higher bonus
                    adjustment = (opp_win_rate - elite_threshold) * time_weight
                    total_adjustment += adjustment
                    total_weight += time_weight
        except Exception:
            continue
    
    if total_weight == 0:
        return {"elite_loss_adjustment": 0.0}
    
    # Normalize to [0, 1] range
    avg_adjustment = total_adjustment / total_weight
    normalized = min(1.0, max(0.0, avg_adjustment / (1.0 - elite_threshold)))
    
    return {"elite_loss_adjustment": float(normalized)}
```

**Then Register It:**
- **File:** `features/registry.py`
- **Line:** ~30 (add to imports)
- **Line:** ~73 (add to FEATURE_SET_TIME_BASED)
- **Line:** ~133 (add to feature_map)
- **Line:** ~220 (add extraction method)

**Then Add Differential:**
- **File:** `features/matchup_features.py`
- **Line:** ~256 (after time_decayed_win_rate_adj_opp_quality_diff)
- **Add:** `differentials['elite_loss_adjustment_diff'] = f1_features.get('elite_loss_adjustment', 0.0) - f2_features.get('elite_loss_adjustment', 0.0)`

---

## Option 4: Create Interaction Features

**File:** `features/matchup_features.py`  
**Location:** In `_calculate_differentials` method, around line 256

**Add After Existing Differentials:**
```python
# Opponent quality × recent form interaction
# Balances opponent quality with recent performance
f1_opp_quality = f1_features.get('opponent_quality_score', 0.0)
f1_recent_form = f1_features.get('time_decayed_win_rate', 0.0)
f2_opp_quality = f2_features.get('opponent_quality_score', 0.0)
f2_recent_form = f2_features.get('time_decayed_win_rate', 0.0)

differentials['opponent_quality_x_recent_form_diff'] = (
    (f1_opp_quality * f1_recent_form) - (f2_opp_quality * f2_recent_form)
)

# Opponent quality × adjusted recent form
f1_adj_form = f1_features.get('time_decayed_win_rate_adj_opp_quality', 0.0)
f2_adj_form = f2_features.get('time_decayed_win_rate_adj_opp_quality', 0.0)

differentials['opponent_quality_x_adj_form_diff'] = (
    (f1_opp_quality * f1_adj_form) - (f2_opp_quality * f2_adj_form)
)
```

---

## Option 5: Adjust Normalization to Preserve Differences

**File:** `features/time_based.py`  
**Lines:** 509-518

**Current Code:**
```python
# Normalize score to [0, 1] range (win rate equivalent)
# With multiplier range [0.5, 2.0] and squared penalty:
# - Worst case: all losses to weak (0.5x) = -1.0 / (0.5^2) = -1.0 / 0.25 = -4.0
# - Best case: all wins vs elite (2.0x) = 1.0 * 2.0 = +2.0
# So actual range is approximately [-4.0, 2.0]
avg_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
# Normalize from [-4.0, 2.0] to [0, 1]
# Add 4.0 to shift to [0, 6.0], then divide by 6.0
normalized_score = (avg_score + 4.0) / 6.0
normalized_score = max(0.0, min(1.0, normalized_score))  # Clamp to [0, 1]
```

**Change Options:**
- **Sigmoid (preserves differences better):**
  ```python
  # Use sigmoid to preserve differences in the middle range
  normalized_score = 1.0 / (1.0 + np.exp(-avg_score))
  ```

- **Percentile-based (if you have distribution data):**
  ```python
  # Would need to calculate percentiles from training data
  # More complex but preserves relative differences better
  ```

- **Less aggressive clamping:**
  ```python
  # Allow values slightly outside [0, 1] to preserve differences
  normalized_score = (avg_score + 4.0) / 6.0
  # Don't clamp, or use wider range like [-0.1, 1.1]
  ```

---

## Option 6: Add Monotone Constraints (Model-Level)

**File:** `models/xgboost_model.py` (or wherever you train the model)

**Location:** In model training/configuration

**Add:**
```python
# Force opponent quality features to have positive monotonic relationship
monotone_constraints = {
    'opponent_quality_score_diff': 1,  # Positive: higher = better
    'avg_opponent_win_rate_diff': 1,   # Positive: higher = better
    'avg_beaten_opponent_win_rate_diff': 1,  # Positive: higher = better
}

# In XGBoost params:
params = {
    'monotone_constraints': monotone_constraints,
    # ... other params
}
```

**Note:** This requires knowing the feature indices in XGBoost, which depends on your feature pipeline.

---

## Option 7: Create "Strength of Schedule Adjusted Win Rate"

**File:** `features/time_based.py`  
**Location:** Add new function (similar to Option 3)

**New Function:**
```python
def extract_sos_adjusted_win_rate(
    fight_history: pd.DataFrame,
    get_fighter_record: Callable[[int], Optional[Dict]]
) -> Dict[str, float]:
    """
    Calculate win rate adjusted by strength of schedule.
    
    Directly multiplies win rate by opponent quality bonus.
    """
    if len(fight_history) == 0:
        return {"sos_adjusted_win_rate": 0.0}
    
    wins = 0
    total = 0
    total_opp_quality = 0.0
    
    for _, row in fight_history.iterrows():
        if row["result"] in ["win", "loss"]:
            total += 1
            if row["result"] == "win":
                wins += 1
            
            opponent_id = row.get("opponent_id")
            if not pd.isna(opponent_id):
                record = get_fighter_record(int(opponent_id))
                if record and record.get("win_rate") is not None:
                    total_opp_quality += record["win_rate"]
    
    if total == 0:
        return {"sos_adjusted_win_rate": 0.0}
    
    win_rate = wins / total
    avg_opp_quality = total_opp_quality / total
    
    # Adjust win rate by opponent quality
    # Higher opponent quality = bonus multiplier
    quality_bonus = 0.5 + (avg_opp_quality * 1.5)  # Same formula as multiplier
    sos_adjusted = win_rate * quality_bonus
    
    # Normalize back to [0, 1]
    sos_adjusted = min(1.0, sos_adjusted / 2.0)  # Divide by max possible (2.0)
    
    return {"sos_adjusted_win_rate": float(sos_adjusted)}
```

**Then register and add differential** (same process as Option 3)

---

## Quick Test Priority

1. **Option 1** (Line 490 in `time_based.py`) - Change `** 2` to `** 3`
2. **Option 2** (Line 473 in `time_based.py`) - Change `1.5` to `2.0` or `2.5`
3. **Option 3** (New function) - Most direct fix but requires more code

Start with Option 1 - it's the quickest test and should have immediate impact!

