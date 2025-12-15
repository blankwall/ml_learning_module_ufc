# Confident Betting with Your UFC Model

## Current Model Performance (Baseline)

✅ **Strengths:**
- 70% accuracy on 2025 holdout (legitimate, no data leakage)
- 22% ROI on flat stakes (professional-level performance)
- 78% AUC (good ranking ability)
- Beats market when they disagree (53% win rate)

⚠️ **Weaknesses:**
- 46% accuracy on upsets (worse than coin flip)
- 50% accuracy on middleweight fights
- 45% accuracy when confidence is low (50-60% predictions)

## Phase 1: Immediate Betting Setup (Start Today)

### 1. **Train Model B (Production Model)**

```bash
# Include 2025 data for more informed predictions
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_with_2025 \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05 \
  --subsample 0.8 \
  --colsample-bytree 0.8
```

### 2. **Generate Predictions for Dec 13 Card**

```bash
# Get predictions with both models
python -m evaluation.preview_upcoming_fights \
  --input data/predictions/upcoming_fights_fight_night_royval_kape.csv \
  --output-csv data/predictions/dec13_model_a.csv \
  --model-name xgboost_model

python -m evaluation.preview_upcoming_fights \
  --input data/predictions/upcoming_fights_fight_night_royval_kape.csv \
  --output-csv data/predictions/dec13_model_b.csv \
  --model-name xgboost_model_with_2025
```

### 3. **Apply Betting Filters**

Only bet when:
- ✅ **Edge > 8%** (minimum threshold for profit after vig)
- ✅ **Model confidence > 60%** (avoid the 45% accuracy zone)
- ✅ **Both models agree** on winner (within 10%)
- ✅ **Not an upset pick** (model struggles here)
- ✅ **Not middleweight** (50% accuracy)
- ❌ **Avoid fights with risk_notes** (slumping fighters, debutants)

### 4. **Position Sizing (Kelly Criterion)**

```python
# For each bet:
edge = model_prob - market_prob
kelly_fraction = edge / (decimal_odds - 1)
bet_size = bankroll × kelly_fraction × 0.25  # Use 1/4 Kelly for safety
```

**Example:**
- Bankroll: $1,000
- Model: 65% probability
- Odds: +150 (40% implied, 2.5 decimal)
- Edge: 25%
- Full Kelly: 25% / 1.5 = 16.7%
- Quarter Kelly: 4.2%
- Bet size: $42

### 5. **Track Results**

Create a simple tracking spreadsheet:

| Date | Fighter | Odds | Model % | Edge | Bet | Result | Profit |
|------|---------|------|---------|------|-----|--------|--------|
| 12/13 | Chikadze | +185 | 55% | +20% | $42 | ? | ? |

## Phase 2: Model Improvement (Next 2 Weeks)

### Strategy 1: Fix Weak Spots

**Problem: 46% on upsets**

Create "upset potential" features:
```python
# In features/time_based.py or new file
def extract_upset_potential(
    age: float,
    win_rate_last_3: float,
    opponent_quality_score: float,
    recent_finish_losses: int
) -> float:
    """
    Identify fighters who might be upset-prone:
    - Aging (>35)
    - Recent decline
    - Faced tough opponents (tired/damaged)
    - Recent finish losses (confidence shaken)
    """
    age_factor = max(0, (age - 35) / 10)  # 0 at 35, 1.0 at 45
    decline_factor = max(0, 1.0 - win_rate_last_3)
    damage_factor = min(1.0, recent_finish_losses / 2.0)
    
    upset_vulnerability = (
        age_factor * 0.4 +
        decline_factor * 0.3 +
        damage_factor * 0.3
    )
    
    return float(min(1.0, upset_vulnerability))
```

**Problem: 50% on middleweight**

Investigate why:
```bash
# Check middleweight fights in holdout
python -c "
import pandas as pd
df = pd.read_csv('reports/eval_data_20251212_110450.csv')
mw = df[df['weight_class'] == 'Middleweight']
print(f'Middleweight fights: {len(mw)}')
print(f'Model accuracy: {mw[\"model_pick\"].eq(mw[\"target\"]).mean():.1%}')
print(f'Market accuracy: {mw[\"market_pick\"].eq(mw[\"target\"]).mean():.1%}')
"
```

Possible fixes:
- Add middleweight-specific features (clinch control, cardio)
- Weight class interaction features
- Separate model for each weight class

### Strategy 2: Feature Engineering Priorities

**High Impact Features to Add:**

1. **Camp Quality** (if you can scrape this):
   - Training camp location
   - Coach reputation
   - Training partners

2. **Stylistic Matchup Indicators**:
```python
def extract_style_mismatch_features(
    f1_striking_rate: float,
    f1_takedown_rate: float,
    f2_striking_defense: float,
    f2_takedown_defense: float
) -> Dict:
    """
    Identify advantageous style matchups:
    - Wrestler vs poor TDD
    - Striker vs poor striking defense
    """
    wrestling_advantage = f1_takedown_rate * (1.0 - f2_takedown_defense)
    striking_advantage = f1_striking_rate * (1.0 - f2_striking_defense)
    
    return {
        "wrestling_exploit": wrestling_advantage,
        "striking_exploit": striking_advantage,
    }
```

3. **Recent Damage Indicators**:
```python
def extract_cumulative_damage_features(
    fight_history: pd.DataFrame
) -> Dict:
    """
    Track accumulated damage in recent fights:
    - Significant strikes absorbed (last 3 fights)
    - Time spent defending (on back, against cage)
    - Number of rounds fought recently
    """
    recent_3 = fight_history.head(3)
    
    # Would need fight stats for this
    strikes_absorbed = ...  # Sum of sig strikes absorbed
    time_in_danger = ...     # Time on back or against cage
    total_rounds = recent_3['rounds_fought'].sum()
    
    return {
        "recent_damage_absorbed": strikes_absorbed,
        "recent_rounds_fought": total_rounds,
        "wear_and_tear_score": (strikes_absorbed / 100) + (total_rounds / 15)
    }
```

4. **Momentum Score Refinement**:
```python
def extract_contextual_momentum(
    win_streak: int,
    loss_streak: int,
    avg_opponent_quality: float,
    finish_rate_last_3: float
) -> float:
    """
    Win streak against good opponents > win streak against weak opponents
    """
    if win_streak > 0:
        momentum = win_streak * (0.5 + avg_opponent_quality)
        if finish_rate_last_3 > 0.5:
            momentum *= 1.2  # Finishing bonus
        return min(1.0, momentum / 5.0)  # Normalize
    else:
        return 0.0
```

### Strategy 3: Model Ensemble

Train multiple models and combine predictions:

```bash
# Model 1: Current XGBoost
# Already have this

# Model 2: More conservative (lower learning rate)
python -m models.xgboost_model \
  --train \
  --model-name xgboost_conservative \
  --n-estimators 300 \
  --max-depth 3 \
  --learning-rate 0.03

# Model 3: More aggressive (deeper trees)
python -m models.xgboost_model \
  --train \
  --model-name xgboost_aggressive \
  --n-estimators 150 \
  --max-depth 6 \
  --learning-rate 0.07
```

Then average predictions:
```python
prob = (prob_conservative + prob_balanced + prob_aggressive) / 3
```

## Phase 3: Advanced Betting Strategy

### 1. **Tiered Confidence System**

| Tier | Criteria | Action |
|------|----------|--------|
| **Tier 1** | Edge >15%, Both models agree, Confidence >70% | Bet 5% Kelly |
| **Tier 2** | Edge >10%, Both models agree, Confidence >60% | Bet 3% Kelly |
| **Tier 3** | Edge >8%, Confidence >60% | Bet 1% Kelly |
| **Pass** | Everything else | No bet |

### 2. **Avoid These Spots**

❌ **Never bet:**
- Middleweight fights (until you fix the 50% accuracy)
- When model predicts an upset (46% accuracy)
- Fights with `risk_notes` warning
- When models disagree by >15%
- Debut fighters (limited data)

### 3. **Find Your Edge**

Your model is BEST at:
- ✅ Favorites (81% accuracy)
- ✅ High confidence picks (88% at >80% confidence)
- ✅ Light Heavyweight (86% accuracy)
- ✅ Welterweight (75% accuracy)

**Focus bets in these categories!**

### 4. **Line Shopping**

```bash
# Generate predictions early in the week
python -m evaluation.preview_upcoming_fights \
  --input upcoming_fights.csv \
  --model-name xgboost_model_with_2025

# Compare across books:
# - DraftKings
# - FanDuel
# - BetMGM
# - Caesars

# Bet at the book with best odds for your side
```

## Phase 4: Performance Tracking & Iteration

### 1. **After Each Event**

```bash
# 1. Update results in your tracking sheet
# 2. Calculate actual ROI
# 3. Identify biggest wins/losses
# 4. Look for patterns in losses
```

### 2. **Monthly Model Update**

```bash
# After 4-6 events (30-50 bets):
# 1. Retrain Model B with latest results
python -m models.xgboost_model \
  --train \
  --model-name xgboost_model_with_2025 \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05

# 2. Re-evaluate performance
# 3. Adjust betting filters based on what's working
```

### 3. **Quarterly Deep Dive**

```bash
# Every 3 months:
# 1. Update holdout set (e.g., 2026 fights)
# 2. Re-run full evaluation
python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2026_odds.csv \
  --min-year 2026 \
  --output-dir reports

# 3. Compare ROI: Is it still ~20%?
# 4. Identify new weak spots
# 5. Add/remove features accordingly
```

## Phase 5: Advanced Topics

### A. **Calibration Tuning**

Your Brier score is 0.189 (good), but you can improve:

```bash
# Train calibrated version
python -m models.xgboost_model \
  --train \
  --calibrate \
  --model-name xgboost_model_calibrated \
  --data-path data/processed/training_data.csv
```

This adjusts probabilities to match actual win rates better.

### B. **Market Line Movement**

Track how odds change from opening to closing:

```python
# Add to your odds file:
- opening_odds_f1
- closing_odds_f1
- line_movement_f1

# Incorporate into model:
sharp_money_indicator = closing_odds < opening_odds
```

Sharp bettors move lines. If your model agrees with line movement → extra confidence.

### C. **Live Betting Opportunities**

Your model gives pre-fight probabilities. Live odds change based on:
- Round-by-round action
- Visible fatigue
- Injuries

If you can:
1. Watch fights live
2. See when live odds deviate from your pre-fight model
3. Bet mid-fight when value appears

### D. **Correlation Analysis**

Check which features drive your profitable bets:

```python
# After 50+ bets:
profitable_bets = bets[bets['profit'] > 0]
losing_bets = bets[bets['profit'] < 0]

# Which features were highest in profitable bets?
# Which features misled you in losing bets?
```

## Quick Start Action Plan

### This Week (Dec 13 Event):

1. ✅ **Train Model B** (with 2025 data)
2. ✅ **Generate predictions** for Dec 13 card
3. ✅ **Apply betting filters** (edge >8%, confidence >60%, both models agree)
4. ✅ **Make 3-5 small bets** ($10-20 each)
5. ✅ **Track results** in spreadsheet

### Next Week (After Dec 13):

1. **Review results**: Which bets won? Which lost? Why?
2. **Update Model B**: Include Dec 13 results
3. **Analyze errors**: Look for patterns in your losses
4. **Adjust filters**: Based on what worked/didn't work

### Month 1 (Dec-Jan):

1. **Bet on 3-4 events** (30-50 bets total)
2. **Track actual ROI**: Compare to expected 22%
3. **Identify profitable spots**: Which weight classes? Fighter types?
4. **Focus future bets**: Double down on what's working

### Month 2-3 (Feb-Mar):

1. **Feature engineering**: Add 2-3 new features based on loss analysis
2. **Retrain models**: With updated features
3. **Re-evaluate holdout**: Did new features help?
4. **Scale up stakes**: If ROI holds >10%, increase Kelly fraction

## Recommended Starting Bankroll Strategy

### Conservative (Recommended):

```
Starting Bankroll: $1,000
Max bet per fight: $50 (5% of bankroll)
Average bet: $25-30 (using quarter Kelly)
Expected monthly volume: 40-60 bets
Expected monthly profit: $200-300 (at 20% ROI)
```

### Aggressive (If You Have Experience):

```
Starting Bankroll: $2,000
Max bet per fight: $100 (5% of bankroll)
Average bet: $50-75 (using half Kelly)
Expected monthly volume: 40-60 bets
Expected monthly profit: $400-600 (at 20% ROI)
```

### Ultra-Conservative (Learning Phase):

```
Starting Bankroll: $500
Max bet per fight: $20 (4% of bankroll)
Average bet: $10-15 (using 1/8 Kelly)
Expected monthly volume: 30-50 bets
Expected monthly profit: $100-150 (at 20% ROI)
```

**Start conservative until you have 50+ bets of real-world data!**

## Risk Management Rules

### Hard Rules (NEVER Break):

1. ❌ **Never bet more than 5% of bankroll on one fight**
2. ❌ **Never chase losses** (doubling bets after losses)
3. ❌ **Never bet on a fight without running both models**
4. ❌ **Never bet without checking risk_notes**
5. ❌ **Never bet when both models disagree by >15%**

### Soft Rules (Use Judgment):

1. ⚠️ Reduce bet size by 50% on middleweight fights
2. ⚠️ Skip upsets unless edge is >15% and both models agree
3. ⚠️ Skip if model confidence is <60%
4. ⚠️ Skip if you can't find the line at predicted edge (odds moved)

## Feature Improvement Roadmap

### Quick Wins (Implement This Week):

1. **Remove problematic features**:
```python
# In features/feature_exclusions.py
EXCLUDED_BASE_FEATURES = [
    # Features that might still have issues
    # Test removing these one at a time
]
```

2. **Add simple interaction features**:
```python
# age × recent_finish_losses
# striking_output × opponent_striking_defense
# takedown_accuracy × opponent_takedown_defense
```

### Medium-Term (Next Month):

1. **Scrape additional data**:
   - Betting line movement (opening vs closing)
   - Fight location (altitude, travel)
   - Fighter camp information

2. **Add composite features**:
   - Style matchup scores
   - Upset vulnerability index
   - Peak performance indicators

3. **Weight class specific models**:
```bash
# Train separate models for problem divisions
python train_weight_class_model.py --weight-class Middleweight
```

### Long-Term (3+ Months):

1. **Ensemble models**: Combine XGBoost + Neural Net + LightGBM
2. **Live betting model**: Update probabilities during fights
3. **DFS lineup optimizer**: Use fight predictions for DraftKings
4. **Automated betting**: API integration with sportsbooks

## Key Metrics to Track

### Model Metrics:
- ✅ **Holdout accuracy** (currently 70%)
- ✅ **ROI** (currently 22%)
- ✅ **Brier score** (currently 0.189)
- ✅ **Win rate on disagreements** (currently 53%)

### Betting Metrics:
- **Actual ROI** (track weekly, monthly, quarterly)
- **Profit by weight class** (find your strongest divisions)
- **Profit by bet size** (are bigger bets less profitable?)
- **Profit by confidence tier** (validate your filters)
- **Closing Line Value** (CLV) - did you beat closing odds?

### Red Flags to Watch:
- 🚩 Actual ROI < 5% for 3+ weeks → Stop betting, retrain
- 🚩 Losing streak of 10+ bets → Review strategy
- 🚩 One weight class consistently loses money → Exclude it
- 🚩 Model and market never disagree → Model is useless

## Success Criteria

### After 50 Bets:
- ✅ ROI > 10% → Model is working, continue
- ⚠️ ROI 5-10% → Breakeven with vig, needs improvement
- 🚩 ROI < 5% → Stop betting, deep model review needed

### After 200 Bets:
- ✅ ROI > 15% → Exceptional, scale up carefully
- ✅ ROI 10-15% → Very good, sustainable edge
- ⚠️ ROI 5-10% → Slight edge, continue refining
- 🚩 ROI < 5% → Model isn't beating market, major overhaul

## Next Steps (This Week)

### Step 1: Train Model B
```bash
python -m models.xgboost_model --train --model-name xgboost_model_with_2025 \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 --max-depth 4 --learning-rate 0.05
```

### Step 2: Compare Predictions
```bash
python scripts/compare_models.py \
  --fighter-1 "Brandon Royval" \
  --fighter-2 "Manel Kape"
```

### Step 3: Generate Full Card Predictions
```bash
python scripts/export_predictions_to_excel.py \
  --input data/predictions/upcoming_fights_fight_night_royval_kape.csv \
  --output data/predictions/dec13_bets.xlsx \
  --model-name xgboost_model_with_2025
```

### Step 4: Filter and Bet
- Open `dec13_bets.xlsx`
- Filter for: `edge > 8%`, `risk_notes = ""`, `recommended_bet != "none"`
- Make 3-5 small bets
- Track results

### Step 5: Review After Event
- Which bets won? Which lost?
- Was there a pattern?
- Should you adjust filters?

---

**Remember:** You already have a profitable model (22% ROI). Don't over-optimize before you have real-world results. Start betting small, track everything, and iterate based on actual performance!

