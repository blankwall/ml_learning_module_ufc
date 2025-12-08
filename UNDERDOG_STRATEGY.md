# UFC Underdog Betting Strategy - Complete Guide

## 🐕 Why Underdogs?

**Underdogs are where amateur bettors can find edge.**

### The Market Inefficiency:

```
┌─────────────────────────────────────────────────┐
│  Public Betting Patterns in UFC                │
├─────────────────────────────────────────────────┤
│  70-80% of bets → Favorites                     │
│  20-30% of bets → Underdogs                     │
│                                                 │
│  Bookmaker Response:                            │
│  • Shade favorite odds higher (worse value)    │
│  • Shade underdog odds lower (better value)    │
│                                                 │
│  Result: UNDERDOGS = VALUE                      │
└─────────────────────────────────────────────────┘
```

### Why This Happens:

1. **Recency Bias** - Recent winners get overvalued
2. **Name Recognition** - Famous fighters overbet
3. **Casual Bettors** - Love betting favorites "for fun"
4. **Emotional Betting** - People bet their favorite fighter
5. **Fear of Loss** - Underdogs feel "risky" even when they're not

**Your Model + Math = Exploit This!**

---

## 🎯 The Underdog Edge Strategy

### Core Thesis:

```
IF: Your model is 66% accurate overall
AND: Bookmakers are 64% accurate on favorites
BUT: Bookmakers are 60% accurate on underdogs (public bias)
THEN: You have 6% edge on underdogs! ✅
```

### Target Underdogs:

```python
ideal_underdog_profile = {
    'odds_range': '+120 to +200',  # Sweet spot
    'model_confidence': '40-48%',  # Almost even fights
    'edge_threshold': '>5%',
    'avoid': {
        'huge_underdogs': '+300 or worse',
        'low_confidence': '<35% model probability',
        'no_edge': '<3% edge'
    }
}
```

---

## 📊 Using the Edge Validator for Underdogs

### Step-by-Step Guide:

#### Step 1: Run Your Model

```bash
# Generate predictions for all historical fights
python features/feature_pipeline.py --create
python models/autogluon_model.py --train --evaluate
```

#### Step 2: Get Historical Odds

You need actual bookmaker odds. Options:

**Option A: Manual Research**
```bash
# Visit BestFightOdds.com
# Record opening and closing lines for 100+ fights
# Create CSV with fight_id, fighter, odds
```

**Option B: Use Estimated Odds (Less Accurate)**
```python
# Estimate odds from fight history
# Better than nothing, but not ideal
if fighter_is_favorite:
    estimated_odds = -150  # Typical favorite
else:
    estimated_odds = +135  # Typical underdog
```

#### Step 3: Prepare Data for Validator

```python
import pandas as pd

# Load your predictions
predictions = pd.read_csv('data/predictions/model_predictions.csv')

# Add required columns
predictions_with_odds = []

for _, pred in predictions.iterrows():
    # Determine if underdog
    is_underdog = pred['model_prob'] < 0.5
    
    # Get bookmaker odds (from your research or estimates)
    bookmaker_odds = get_actual_odds(pred['fight_id'])  # You provide this
    
    predictions_with_odds.append({
        'fight_id': pred['fight_id'],
        'fighter_name': pred['fighter_name'],
        'model_prob': pred['model_prob'],
        'actual_result': pred['actual_result'],  # 1=won, 0=lost
        'bookmaker_odds': bookmaker_odds,
        'is_underdog': is_underdog
    })

df = pd.DataFrame(predictions_with_odds)
df.to_csv('data/predictions/predictions_with_odds.csv', index=False)
```

#### Step 4: Run Underdog Analysis

```python
from scripts.validate_edge import analyze_underdog_strategy

# Load data
df = pd.read_csv('data/predictions/predictions_with_odds.csv')

# Analyze underdog strategy
results = analyze_underdog_strategy(df)

print(f"\n{'='*60}")
print("UNDERDOG STRATEGY RESULTS")
print(f"{'='*60}")
print(f"Has Edge: {results['has_edge']}")
print(f"Best Threshold: {results.get('best_threshold', 'N/A')}")
print(f"Expected ROI: {results.get('expected_roi', 0):.2f}%")
print(f"Win Rate: {results.get('win_rate', 0):.1f}%")
print(f"Bets Per Year: {results.get('bets_per_year', 0)}")
```

#### Step 5: Interpret Results

**Scenario A: Profitable Underdogs** ✅
```python
if roi > 10%:
    action = """
    ✅ STRONG EDGE ON UNDERDOGS
    
    Next Steps:
    1. Paper trade 50 underdog bets
    2. Track every result meticulously
    3. If still profitable, start with $500-1000
    4. Use 25% Kelly sizing
    5. Maximum 5% per bet
    6. Expect 30-50% drawdowns
    """
```

**Scenario B: Marginal Edge** ⚠️
```python
elif roi > 3%:
    action = """
    ⚠️  MARGINAL EDGE
    
    Next Steps:
    1. Collect more data (need 200+ fights)
    2. Test for statistical significance
    3. Find specific niches (weight class, style matchup)
    4. Paper trade only
    5. DO NOT bet real money yet
    """
```

**Scenario C: No Edge** ❌
```python
else:
    action = """
    ❌ NO EDGE ON UNDERDOGS
    
    Next Steps:
    1. Don't bet underdogs
    2. Try other strategies:
       - Prop bets (method/round)
       - Specific weight classes
       - Live betting
    3. Or accept no betting edge exists
    4. Use system for non-betting purposes
    """
```

---

## 💰 Underdog Bankroll Management

### Conservative Approach (Recommended):

```python
bankroll_management = {
    'starting_bankroll': 1000,  # Start small!
    'bet_sizing': '25% Kelly',  # Conservative
    'max_single_bet': '5% of bankroll',
    'max_exposure': '15% at once',  # Max 3 bets at once
    'stop_loss': 'Down 30%, reassess everything'
}

# Example:
bankroll = 1000
edge = 0.08  # 8% edge on underdog
odds = 1.75  # +175 American odds

# Kelly Criterion
kelly = (0.45 × 1.75 - 0.55) / 0.75 = 0.32
quarter_kelly = 0.32 × 0.25 = 0.08  # 8% of bankroll

bet_size = min(bankroll × 0.08, bankroll × 0.05)
# → Bet $50 (5% max)
```

### Aggressive Approach (Higher Risk):

```python
# Only if you've proven edge over 100+ bets
bankroll_management = {
    'starting_bankroll': 5000,
    'bet_sizing': '50% Kelly',
    'max_single_bet': '10% of bankroll',
    'max_exposure': '30% at once',
}

# Higher returns, MUCH higher variance
# Can lose 50% of bankroll in bad streak
```

---

## 📈 Expected Performance (Underdog Focus)

### If Your Model Has Real Edge:

```python
underdog_betting_expectations = {
    'year_1': {
        'bets': 30,
        'win_rate': '42%',
        'roi': '12%',
        'profit': '+$600 on $5,000 wagered',
        'max_drawdown': '-25%',
        'longest_losing_streak': '7 losses in a row'
    },
    'year_2': {
        'bets': 35,
        'win_rate': '40%',
        'roi': '9%',
        'profit': '+$540 on $6,000 wagered',
        'note': 'Edge might degrade as market adjusts'
    }
}

# Reality Check:
expected_emotions = {
    'confidence': 'High after 5-1 start',
    'doubt': 'Crushing after 1-7 slide',
    'discipline': 'Required to stick to system',
    'patience': 'Months between profitable bets'
}
```

---

## 🎲 Real-World Underdog Examples

### Example 1: Classic Value Underdog

```
Fight: Sean Strickland (+170) vs Israel Adesanya (-200)
Date: September 2023
Result: STRICKLAND WINS! (huge upset)

Analysis:
- Public: 85% on Adesanya (name value)
- Your Model: 44% Strickland (saw defensive style advantage)
- Bookmaker: +170 = 37% implied
- Your Edge: 7%
- EV: +18.8% per dollar

Outcome: ✅ Win at +170 odds
Lesson: Public overrates star power
```

### Example 2: Avoid the Trap

```
Fight: CM Punk (+250) vs Mickey Gall (-300)
Date: September 2016
Result: GALL WINS easily

Analysis:
- Public: 60% on CM Punk (celebrity factor)
- Your Model: 18% Punk (no MMA experience)
- Bookmaker: +250 = 28.6% implied
- Your Edge: -10.6% (model says Punk even worse!)
- EV: NEGATIVE

Outcome: ✅ SKIP (avoided losing bet)
Lesson: Not all underdogs have value
```

### Example 3: The Sweet Spot

```
Fight: Merab Dvalishvili (+135) vs Henry Cejudo (-155)
Date: February 2024
Result: MERAB WINS

Analysis:
- Public: 70% on Cejudo (former champion)
- Your Model: 48% Merab (close fight, work rate advantage)
- Bookmaker: +135 = 42.6% implied
- Your Edge: 5.4%
- EV: +11.2% per dollar

Outcome: ✅ Win at +135 odds
Lesson: Slight underdogs in close matchups = value
```

---

## 🛠️ Complete Workflow

### Day-to-Day Usage:

```bash
# 1. Upcoming event announced
EVENT="UFC-320"

# 2. Generate predictions
python predict.py --event $EVENT

# 3. Get current odds
# (Manual: Visit BestFightOdds.com or use API)
# Save to: data/odds/ufc_320_odds.csv

# 4. Run edge analysis
python scripts/analyze_event_edges.py \
  --event $EVENT \
  --odds-file data/odds/ufc_320_odds.csv \
  --focus underdogs

# Output:
# Fight 1: Jon Jones vs Tom Aspinall
#   Jones: -250 (No edge)
#   Aspinall: +210 (3% edge - marginal)
#   → SKIP
#
# Fight 2: Sean O'Malley vs Merab Dvalishvili
#   O'Malley: -180 (No edge)
#   Merab: +160 (8% edge - BET!)
#   → BET MERAB: 3% of bankroll

# 5. Place bets (if edge exists)
# 6. Track results
# 7. Update model with new data
```

---

## ⚠️ Warnings and Reality Checks

### 1. **Sample Size Matters**

```python
# After 10 underdog bets: 7-3 (70%)
status = "Too early to know if edge is real"

# After 50 underdog bets: 21-29 (42%)
status = "Getting meaningful, but still small sample"

# After 100 underdog bets: 42-58 (42%)
if roi > 8%:
    status = "✅ Real edge likely exists"
else:
    status = "❌ No edge, got lucky early"
```

### 2. **Variance is BRUTAL**

```python
underdog_variance = {
    'worst_streak': '10 losses in a row (will happen!)',
    'typical_drawdown': '20-30%',
    'max_drawdown': '40-50% (even with edge)',
    'time_to_recover': '2-6 months',
    'emotional_toll': 'HIGH (stick to system!)'
}

# You WILL experience:
- Weeks with no bets (no edge found)
- Losing $500 in one night (3 underdogs lose)
- Questioning everything after 1-9 stretch
- Wanting to quit during drawdown

# Discipline is KEY!
```

### 3. **Edge Degrades**

```python
edge_degradation = {
    'year_1': '8% ROI (finding inefficiencies)',
    'year_2': '5% ROI (market adjusts)',
    'year_3': '2% ROI (edge shrinks)',
    'year_4': '0% ROI (market caught up)',
}

# What to do:
- Constantly update model
- Find new angles
- Adapt to market changes
```

---

## 📚 Complete Usage Guide

### 1. Basic Edge Validation

```bash
# Run the validator with demo data
python scripts/validate_edge.py

# Output shows:
# - Scenario 1: Model with 5% edge → ROI: +8.3%
# - Scenario 2: Model with no edge → ROI: -1.2%
```

### 2. Analyze Your Predictions

```python
from scripts.validate_edge import analyze_underdog_strategy
import pandas as pd

# Load your predictions (you need to create this file)
df = pd.read_csv('data/predictions/predictions_with_odds.csv')

# Run underdog analysis
results = analyze_underdog_strategy(df)

# Results tell you:
# - Best odds range to target
# - Optimal model probability threshold
# - Expected ROI
# - Number of bets per year
```

### 3. Find Your Sweet Spot

```python
# Test different strategies
strategies = {
    'conservative': {
        'min_prob': 0.45,  # Only bet near-even underdogs
        'min_edge': 0.07,  # 7% minimum edge
        'odds_max': 180,   # +180 max
        'expected': '5-10 bets/year, 15% ROI, low variance'
    },
    'moderate': {
        'min_prob': 0.40,  # Bet moderate underdogs
        'min_edge': 0.05,  # 5% minimum edge
        'odds_max': 220,   # +220 max
        'expected': '15-25 bets/year, 10% ROI, medium variance'
    },
    'aggressive': {
        'min_prob': 0.35,  # Bet bigger underdogs
        'min_edge': 0.04,  # 4% minimum edge
        'odds_max': 280,   # +280 max
        'expected': '30-50 bets/year, 8% ROI, HIGH variance'
    }
}

# Test each and pick the one with:
# 1. Highest ROI
# 2. Acceptable variance for your risk tolerance
# 3. Enough betting opportunities
```

---

## 🏆 Success Criteria

### After 100 Underdog Bets:

```python
def evaluate_underdog_success(results):
    """Determine if your underdog strategy is working"""
    
    criteria = {
        'roi': results['roi'] > 5,           # At least 5% ROI
        'win_rate': results['win_rate'] > 35, # At least 35% win rate
        'profit': results['total_profit'] > 0, # Overall profitable
        'sample_size': results['n_bets'] > 100, # Enough data
    }
    
    if all(criteria.values()):
        return "✅ SUCCESS: Continue with underdog strategy"
    elif results['roi'] > 0 and results['n_bets'] > 50:
        return "⚠️  MARGINAL: Need more data, continue tracking"
    else:
        return "❌ FAILURE: No edge on underdogs, stop betting"
```

### Realistic Targets:

| Metric | Minimum (Survival) | Good | Excellent |
|--------|-------------------|------|-----------|
| **Win Rate** | 35% | 40% | 45% |
| **ROI** | 3% | 8% | 15% |
| **Profit Factor** | 1.1 | 1.3 | 1.5+ |
| **Max Drawdown** | -40% | -25% | -15% |
| **Bets/Year** | 20 | 30 | 50 |

---

## 💡 Advanced Underdog Tactics

### 1. **Line Movement Strategy**

```python
# Watch how odds move
opening_line = +165
closing_line = +145  # Moved toward underdog

# Sharp money is on underdog!
# Your model agrees → STRONG BET

vs.

opening_line = +165
closing_line = +185  # Moved away from underdog

# Public driving line
# Your model still likes underdog → STILL BET (better odds!)
```

### 2. **Style-Based Underdog Value**

```python
# Your model might be better at specific underdogs:
underdog_types = {
    'wrestler_vs_striker': {
        'example': 'Wrestler is underdog vs striker',
        'market_bias': 'Strikers more exciting',
        'your_edge': 'Model weights grappling properly'
    },
    'volume_puncher_underdog': {
        'example': 'High-output fighter is underdog',
        'market_bias': 'Power punchers overhyped',
        'your_edge': 'Volume wins decisions'
    },
    'grinder_underdog': {
        'example': 'Cardio-heavy fighter is underdog',
        'market_bias': 'Flashy fighters overvalued',
        'your_edge': 'Late-round performance prediction'
    }
}
```

### 3. **Selective Aggression**

```python
# Not all underdogs are equal
bet_sizing = {
    'small_underdog_big_edge': {
        'example': '+140 with 10% edge',
        'size': '5% of bankroll',
        'reason': 'High probability, great value'
    },
    'medium_underdog_good_edge': {
        'example': '+180 with 7% edge',
        'size': '3% of bankroll',
        'reason': 'Good value, moderate risk'
    },
    'big_underdog_small_edge': {
        'example': '+240 with 5% edge',
        'size': '2% of bankroll',
        'reason': 'High variance, minimum edge'
    }
}
```

---

## 🔍 What the Validator Tells You

When you run the validator, you get:

### Output Example:

```
============================================================
UNDERDOG STRATEGY ANALYSIS
============================================================

Found 89 underdog opportunities

--- Edge by Odds Range ---

+100 to +150 (slight underdogs):
  Fights: 34
  Avg Edge: +4.2%
  Win Rate: 43.1%
  ROI: +9.8%

+150 to +200 (moderate underdogs):
  Fights: 28
  Win Rate: 39.3%
  Avg Edge: +6.1%
  ROI: +14.2%

+200 to +300 (big underdogs):
  Fights: 19
  Win Rate: 31.6%
  Avg Edge: +2.8%
  ROI: +3.1%

+300+ (huge underdogs):
  Fights: 8
  Win Rate: 25.0%
  Avg Edge: -1.2%
  ROI: -8.4%

--- Optimal Underdog Threshold ---

Bet when model prob >= 40%:
  Bets: 32
  Win Rate: 46.9%
  ROI: +16.8%

Bet when model prob >= 35%:
  Bets: 51
  Win Rate: 41.2%
  ROI: +11.4%

============================================================
✅ BEST UNDERDOG STRATEGY:
  Bet underdogs when model probability >= 40%
  Expected ROI: 16.8%
  Win Rate: 46.9%
  Bets per year: ~32
============================================================
```

### Interpreting This:

```python
if best_roi > 10%:
    print("🎉 JACKPOT: Real edge on underdogs!")
    print("Focus on: +150 to +200 range, model prob >= 40%")
    
elif best_roi > 5%:
    print("✅ Good: Modest edge exists")
    print("Be selective, stick to high confidence bets")
    
elif best_roi > 0%:
    print("⚠️  Marginal: Need more data")
    print("Paper trade for 6 months")
    
else:
    print("❌ No edge: Don't bet")
    print("Model isn't beating market on underdogs")
```

---

## 🎯 Final Recommendations

### For Underdog-Focused Betting:

1. **Start Small**
   ```bash
   bankroll = $500-1000
   bet_size = 2-5% per bet
   max_3_bets_at_once = True
   ```

2. **Be Selective**
   ```python
   # Don't bet every underdog
   # Only bet when:
   edge > 5% and model_prob > 40% and odds in [120, 220]
   
   # This means:
   # - Most events: 0 bets
   # - Some events: 1 bet
   # - Rare events: 2-3 bets
   ```

3. **Track Everything**
   ```python
   # Log every bet:
   bet_log = {
       'date': '2025-11-27',
       'fighter': 'Merab Dvalishvili',
       'odds': +160,
       'model_prob': 0.46,
       'edge': 0.074,
       'stake': $50,
       'result': 'WIN',
       'profit': +$80,
       'notes': 'Volume > power matchup'
   }
   ```

4. **Accept Variance**
   ```python
   # You WILL have:
   0-8_stretch = "Happens even with edge"
   down_30_percent = "Normal for underdog betting"
   months_without_bets = "Sometimes no value exists"
   
   # Stay disciplined!
   ```

5. **Validate Continuously**
   ```bash
   # After every 25 bets
   python scripts/validate_edge.py --update-analysis
   
   # If edge disappears:
   stop_betting_immediately()
   reassess_model()
   ```

---

## 📞 Quick Start Commands

```bash
# 1. Demo the validator
python scripts/validate_edge.py

# 2. Analyze your predictions
python scripts/validate_edge.py --data your_predictions.csv --focus underdogs

# 3. Find optimal underdog threshold
python scripts/validate_edge.py --optimize-thresholds --underdog-only

# 4. Generate recommendations for upcoming event
python predict.py --event UFC-320 --underdog-analysis
```

---

## 🎯 Bottom Line

**Underdog betting is where you're most likely to find edge.**

### Your Action Plan:

1. ✅ Build your AutoGluon model (66% accuracy)
2. ✅ Run edge validator on historical data
3. ✅ **Focus specifically on underdogs** (+120 to +220 range)
4. ✅ Find your optimal threshold (likely 40-45% model probability)
5. ⚠️ **If ROI > 5%**: Paper trade 50 bets
6. ⚠️ **If still profitable**: Start with $500-1000 real money
7. ✅ **Track religiously** and adjust as needed

**Remember**: Even without edge, you've built something awesome! 🥊

But if you DO find edge in underdogs... that's where the magic happens! 🐕💰

---

See `EDGE_VALIDATOR_GUIDE.md` for complete technical details.

