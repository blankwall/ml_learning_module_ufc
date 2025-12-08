# Edge Validator Guide - Finding Value in UFC Underdogs

## 🎯 Why Focus on Underdogs?

**Underdogs are where the edge lives.**

### The Market Inefficiency:

```
Public Betting Behavior:
- 70% of bets go to favorites
- Bookmakers shade odds to balance action
- Favorites become overpriced
- Underdogs become underpriced

Result: VALUE IN UNDERDOGS
```

### Real Example:

```python
# Fighter A (Favorite): -200 odds
public_bets = 75%  # Heavy public money
bookmaker_adjustment = "Shade odds higher"
true_odds = -150  # Should be this
market_odds = -200  # Actual odds (worse for bettor)
→ NO VALUE

# Fighter B (Underdog): +175 odds  
public_bets = 25%  # Light public money
bookmaker_adjustment = "Shade odds lower"
true_odds = +150  # Should be this
market_odds = +175  # Actual odds (better for bettor)
→ VALUE! ✅
```

---

## 📊 Edge Validator Overview

The `validate_edge.py` script helps you:
1. ✅ Calculate edge vs bookmaker odds
2. ✅ Simulate betting results
3. ✅ Find profitable scenarios (especially underdogs)
4. ✅ Determine if your model has real edge

---

## 🚀 Quick Start

### Basic Usage:

```python
from scripts.validate_edge import calculate_edge, simulate_betting_results
import pandas as pd

# Your model's predictions
predictions = pd.DataFrame({
    'model_prob': [0.45, 0.38, 0.52, 0.35],  # Your win probabilities
    'actual_result': [1, 0, 1, 1],  # 1=won, 0=lost
    'bookmaker_odds': [+150, +200, +120, +180],  # American odds
    'is_underdog': [True, True, True, True]
})

# Simulate betting
results = simulate_betting_results(
    predictions, 
    min_edge=0.05,  # Only bet with 5%+ edge
    initial_bankroll=10000
)

print(f"ROI: {results['roi']:.2f}%")
print(f"Has Edge: {results['has_edge']}")
```

---

## 🎲 Understanding Edge Calculation

### The Formula:

```python
def calculate_edge(model_probability, bookmaker_odds):
    """
    Edge = Your Probability - Market's Implied Probability
    """
    # Convert odds to probability
    if bookmaker_odds > 0:  # Underdog odds
        implied_prob = 100 / (bookmaker_odds + 100)
    else:  # Favorite odds
        implied_prob = abs(bookmaker_odds) / (abs(bookmaker_odds) + 100)
    
    # Calculate edge
    edge = model_probability - implied_prob
    
    return edge
```

### Examples:

#### Example 1: Underdog with Edge ✅
```python
your_model = 0.45  # You think underdog has 45% chance
odds = +150        # Bookmaker offers +150
implied = 0.40     # +150 implies 40%
edge = 0.45 - 0.40 = 0.05  # 5% EDGE!

Expected Value = (0.45 × 1.50) - (0.55 × 1.00) = 0.125
→ For every $1 bet, expect $0.125 profit
→ BET! ✅
```

#### Example 2: Underdog with NO Edge ❌
```python
your_model = 0.38  # You think underdog has 38% chance
odds = +200        # Bookmaker offers +200
implied = 0.33     # +200 implies 33%
edge = 0.38 - 0.33 = 0.05  # 5% edge

BUT: Your model says 38%, which is still LOW
Expected Value = (0.38 × 2.00) - (0.62 × 1.00) = 0.14
→ Positive EV, but high variance
→ BET SMALL or PASS
```

#### Example 3: Favorite (Skip) ❌
```python
your_model = 0.68  # You think favorite has 68% chance
odds = -200        # Bookmaker offers -200
implied = 0.67     # -200 implies 67%
edge = 0.68 - 0.67 = 0.01  # Only 1% edge

Expected Value = (0.68 × 0.50) - (0.32 × 1.00) = 0.02
→ Tiny edge, not worth the juice
→ SKIP (focus on underdogs) ❌
```

---

## 🐕 Underdog Betting Strategy

### Why Underdogs Have More Edge:

1. **Public Bias** - Casual bettors love favorites
2. **Recency Bias** - Recent wins inflate favorite's odds
3. **Name Recognition** - Famous fighters overvalued
4. **MMA Variance** - One punch changes everything (helps underdogs)
5. **Bookmaker Shading** - They need favorites bet heavily

### The Underdog Edge Thesis:

```python
underdog_advantages = {
    'market_inefficiency': 'Favorites overpriced by public',
    'better_odds': '+200 vs -200 (same 1% edge = 2x value)',
    'variance_benefit': 'Upsets happen ~35-40% in MMA',
    'less_juice': 'Underdog line has less vig',
    'psychological': 'Market underestimates upset potential'
}
```

### When to Bet Underdogs:

```python
bet_underdog_when = {
    'edge': 'Edge > 5%',
    'model_confidence': 'Your prob > 35%',  # Don't bet hopeless dogs
    'odds_range': '+120 to +250',  # Sweet spot
    'style_advantage': 'Underdog has stylistic edge',
    'public_heavy_on_favorite': 'More than 70% public bets'
}

avoid_when = {
    'huge_underdog': 'Odds > +300 (too risky)',
    'low_model_confidence': 'Your prob < 30%',
    'no_edge': 'Edge < 3%',
    'trap_fight': 'Line movement toward underdog (sharp money)'
}
```

---

## 📈 Using the Edge Validator

### Step 1: Prepare Your Data

```python
import pandas as pd
from database.db_manager import DatabaseManager

# Load your predictions and results
db = DatabaseManager()
session = db.get_session()

# Get historical fights with your predictions
predictions_data = []

for fight in historical_fights:
    # Get your model's prediction
    model_prob = your_model.predict(fight)
    
    # Get actual result
    actual_result = 1 if fight.winner == fight.fighter_1 else 0
    
    # Get odds (you need to source this separately)
    # For now, estimate based on win probability
    if model_prob > 0.5:
        odds = -1 * (model_prob / (1 - model_prob)) * 100
        is_underdog = False
    else:
        odds = ((1 - model_prob) / model_prob) * 100
        is_underdog = True
    
    predictions_data.append({
        'fight_id': fight.id,
        'fighter_name': fight.fighter_1.name,
        'model_prob': model_prob,
        'actual_result': actual_result,
        'bookmaker_odds': odds,
        'is_underdog': is_underdog
    })

df = pd.DataFrame(predictions_data)
```

### Step 2: Filter for Underdogs

```python
# Focus on underdogs only
underdogs = df[df['is_underdog'] == True].copy()

print(f"Total fights: {len(df)}")
print(f"Underdog opportunities: {len(underdogs)}")
print(f"Underdog win rate: {underdogs['actual_result'].mean():.2%}")
```

### Step 3: Run Edge Analysis

```python
from scripts.validate_edge import simulate_betting_results, analyze_edge_by_scenario

# Simulate betting on underdogs only
results = simulate_betting_results(
    underdogs,
    min_edge=0.05,  # 5% minimum edge
    initial_bankroll=10000
)

print("\n=== UNDERDOG BETTING RESULTS ===")
print(f"Bets Placed: {results['bets_placed']}")
print(f"Bets Won: {results['bets_won']}")
print(f"Win Rate: {results['win_rate']:.1f}%")
print(f"Total Profit: ${results['total_profit']:,.2f}")
print(f"ROI: {results['roi']:.2f}%")
print(f"Final Bankroll: ${results['final_bankroll']:,.2f}")
print(f"\nHas Edge: {'✅ YES' if results['has_edge'] else '❌ NO'}")
```

### Step 4: Analyze by Confidence Level

```python
# Find your sweet spot
scenarios = analyze_edge_by_scenario(underdogs)

print("\n=== EDGE BY SCENARIO ===")
print(scenarios.to_string(index=False))

# Example output:
#                 scenario  n_bets  accuracy  avg_model_prob  potential_edge
#  Confidence >= 35%          45      0.42          0.38           0.05
#  Confidence >= 40%          28      0.46          0.42           0.08
#  Confidence >= 45%          12      0.50          0.47           0.12
#  Betting underdogs         89      0.39          0.35           0.02
```

### Step 5: Find Optimal Strategy

```python
# Test different thresholds
thresholds = [0.30, 0.35, 0.40, 0.45]
results_by_threshold = []

for threshold in thresholds:
    subset = underdogs[underdogs['model_prob'] >= threshold]
    
    if len(subset) < 10:
        continue
    
    results = simulate_betting_results(subset, min_edge=0.05)
    
    results_by_threshold.append({
        'threshold': threshold,
        'n_bets': results['bets_placed'],
        'win_rate': results.get('win_rate', 0),
        'roi': results.get('roi', 0),
        'profit': results.get('total_profit', 0)
    })

best_strategy = pd.DataFrame(results_by_threshold)
print("\n=== OPTIMAL THRESHOLD ===")
print(best_strategy.to_string(index=False))

# Find best ROI
best = best_strategy.loc[best_strategy['roi'].idxmax()]
print(f"\n✅ BEST STRATEGY:")
print(f"   Bet underdogs when model prob >= {best['threshold']:.0%}")
print(f"   Expected ROI: {best['roi']:.2f}%")
print(f"   Bets per year: ~{best['n_bets']}")
```

---

## 💡 Practical Examples

### Example 1: Finding Underdog Value

```python
# Fighter: Sean Strickland (Underdog)
# Opponent: Israel Adesanya (Favorite)

model_analysis = {
    'strickland_prob': 0.42,  # Your model gives 42%
    'bookmaker_odds': +165,    # Bookmaker offers +165
    'implied_prob': 0.377,     # +165 implies 37.7%
    'edge': 0.042,             # 4.2% edge
}

# Calculate EV
ev = (0.42 × 1.65) - (0.58 × 1.00)
print(f"Expected Value: ${ev:.2f} per $1 bet")
# Output: Expected Value: $0.11 per $1 bet

# Decision
if model_analysis['edge'] > 0.04:
    print("✅ BET: Value on underdog Strickland")
    stake = kelly_criterion(0.42, 1.65) * 0.25  # 25% Kelly
    print(f"Recommended stake: {stake:.1%} of bankroll")
```

### Example 2: Avoiding False Value

```python
# Fighter: Paddy Pimblett (Underdog)
# Opponent: Lightweight contender

model_analysis = {
    'pimblett_prob': 0.28,  # Your model gives 28%
    'bookmaker_odds': +250,  # Bookmaker offers +250
    'implied_prob': 0.286,   # +250 implies 28.6%
    'edge': -0.006,          # NEGATIVE edge
}

# Your model thinks he's WORSE than bookmaker
print("❌ SKIP: No edge, model agrees with market")
print("Even though he's underdog, he's rightfully so")
```

### Example 3: Sweet Spot Underdog

```python
# Fighter: Merab Dvalishvili (Slight Underdog)
# Opponent: Former champion

model_analysis = {
    'merab_prob': 0.48,     # Your model gives 48% (almost even)
    'bookmaker_odds': +135,  # Bookmaker offers +135
    'implied_prob': 0.426,   # +135 implies 42.6%
    'edge': 0.054,           # 5.4% edge!
}

print("✅ BET: Significant edge on slight underdog")
print("This is the sweet spot - good chance + good odds")

# Calculate optimal bet size
kelly = (0.48 × 2.35 - 1) / 1.35
print(f"Full Kelly: {kelly:.1%}")
print(f"Quarter Kelly (safer): {kelly * 0.25:.1%}")
```

---

## 🎯 Underdog-Specific Metrics

### Key Metrics to Track:

```python
underdog_metrics = {
    'overall_win_rate': 'Should be 35-45%',
    'roi': 'Should be > 5%',
    'avg_edge_per_bet': 'Should be > 4%',
    'win_rate_at_high_confidence': 'When prob > 40%, should be > 45%',
    'variance': 'Will be higher than favorites (expect swings)',
}
```

### Success Criteria for Underdog Strategy:

```python
# After 100 underdog bets:
success_criteria = {
    'minimum_roi': 5%,           # At least 5% ROI
    'minimum_win_rate': 35%,     # At least 35% win rate
    'minimum_bets': 100,         # Need 100+ bets to verify
    'max_drawdown': -30%,        # Can handle 30% drawdown
    'profit_factor': 1.3,        # $1.30 won per $1 lost
}

# If you hit these, you have real edge!
```

---

## 📊 Complete Workflow

### Full Underdog Analysis Pipeline:

```python
#!/usr/bin/env python3
"""
Complete underdog edge analysis workflow
"""

import pandas as pd
from scripts.validate_edge import (
    calculate_edge, 
    simulate_betting_results,
    analyze_edge_by_scenario
)

# 1. Load your data
print("Step 1: Loading predictions...")
df = pd.read_csv('data/processed/predictions_with_odds.csv')

# 2. Filter for underdogs
print("Step 2: Filtering for underdogs...")
underdogs = df[df['bookmaker_odds'] > 0].copy()
underdogs['is_underdog'] = True

print(f"Found {len(underdogs)} underdog opportunities")

# 3. Calculate edge for each
print("Step 3: Calculating edge...")
underdogs['edge'] = underdogs.apply(
    lambda row: calculate_edge(row['model_prob'], row['bookmaker_odds']),
    axis=1
)

# 4. Filter for positive edge
print("Step 4: Finding positive edge bets...")
value_dogs = underdogs[underdogs['edge'] > 0.05]
print(f"Found {len(value_dogs)} value underdog bets (>5% edge)")

# 5. Simulate betting
print("\nStep 5: Simulating betting results...")
results = simulate_betting_results(
    value_dogs,
    min_edge=0.05,
    initial_bankroll=10000
)

# 6. Display results
print("\n" + "="*60)
print("UNDERDOG BETTING ANALYSIS RESULTS")
print("="*60)
print(f"Total Opportunities: {len(underdogs)}")
print(f"Value Bets (>5% edge): {len(value_dogs)}")
print(f"Bets Placed: {results['bets_placed']}")
print(f"Bets Won: {results['bets_won']}")
print(f"Win Rate: {results.get('win_rate', 0):.1f}%")
print(f"Total Profit: ${results.get('total_profit', 0):,.2f}")
print(f"ROI: {results.get('roi', 0):.2f}%")
print(f"Final Bankroll: ${results.get('final_bankroll', 0):,.2f}")
print("="*60)

# 7. Recommendations
if results['has_edge'] and results['roi'] > 5:
    print("\n✅ RECOMMENDATION: Bet underdogs with this strategy")
    print(f"   Expected annual ROI: ~{results['roi']:.1f}%")
    print(f"   Bet ~{len(value_dogs)} underdogs per year")
    print(f"   Use {(results['avg_edge_per_bet'] * 0.25):.1%} of bankroll per bet")
elif results['has_edge'] and results['roi'] > 0:
    print("\n⚠️  RECOMMENDATION: Marginal edge, paper trade first")
    print(f"   ROI only {results['roi']:.1f}%, need more data")
else:
    print("\n❌ RECOMMENDATION: No edge detected on underdogs")
    print("   Do not bet real money")
    print("   Consider: Model improvement or other strategies")

# 8. Save results
value_dogs.to_csv('data/predictions/underdog_value_bets.csv', index=False)
print(f"\n💾 Saved value bets to: data/predictions/underdog_value_bets.csv")
```

---

## 🏆 Success Stories (Hypothetical)

### Profile 1: The Underdog Specialist

```python
strategy = {
    'focus': 'Underdogs between +120 and +200',
    'model_threshold': '40%+ win probability',
    'min_edge': '5%',
    'results_over_100_bets': {
        'win_rate': '43%',
        'roi': '12.5%',
        'profit': '+$2,500 on $20k wagered'
    }
}

print("✅ Profitable underdog bettor")
print("Edge came from: Better style matchup analysis than market")
```

### Profile 2: The Value Hunter

```python
strategy = {
    'focus': 'Any underdog with 8%+ edge',
    'model_threshold': '35%+ win probability',
    'selective': 'Only ~20 bets per year',
    'results': {
        'win_rate': '38%',
        'roi': '18%',
        'profit': '+$1,800 on $10k wagered'
    }
}

print("✅ Highly selective, high ROI")
print("Edge came from: Waiting for big inefficiencies")
```

---

## ⚠️ Common Mistakes

### 1. **Betting Every Underdog**
```python
# BAD:
if fighter_is_underdog:
    bet()  # ❌ This loses money!

# GOOD:
if fighter_is_underdog and edge > 5% and model_prob > 35%:
    bet()  # ✅ Selective value betting
```

### 2. **Chasing High Odds**
```python
# BAD:
"Fighter is +400, huge payout!"  # ❌ Low probability

# GOOD:
"Fighter is +175, I have them at 45%"  # ✅ Real value
```

### 3. **Ignoring Sample Size**
```python
# BAD:
# 10-2 record on underdogs → "I'm profitable!"  # ❌ Too small

# GOOD:
# 43-57 record (43%) on underdogs over 100 bets
# ROI: +8.5% → "I might have edge, continue tracking"  # ✅
```

---

## 📚 Resources

### Files in This Project:

- `scripts/validate_edge.py` - Main validation script
- `NO_EDGE_GUIDE.md` - What to do if no edge found
- `backtesting/backtest_engine.py` - Full historical backtesting
- `WORKFLOW.md` - Complete system workflow

### External Resources:

- **Get Historical Odds**: BestFightOdds.com (manual research)
- **Underdog Strategy**: Look for public betting percentages
- **Line Movement**: Track opening vs closing lines
- **Sharp Money**: See where professional money goes

---

## 🎯 Quick Reference

### Commands:

```bash
# Run edge validator
python scripts/validate_edge.py

# Run full backtest with odds
python backtesting/backtest_engine.py

# Generate predictions for upcoming event
python predict.py --event UFC-320 --focus-underdogs
```

### Key Thresholds:

```python
underdog_strategy = {
    'bet_when': {
        'model_prob': '>= 35%',
        'edge': '>= 5%',
        'odds_range': '+120 to +250'
    },
    'position_size': '25% Kelly (conservative)',
    'max_bet': '5% of bankroll',
    'min_bankroll': '$1,000 to start'
}
```

---

## ✅ Action Plan

1. **Run your model on historical fights**
2. **Get actual bookmaker odds** (research or scraper)
3. **Focus on underdogs** (+100 or better)
4. **Run edge validator** on underdog subset
5. **If ROI > 5%**: Paper trade for 50 bets
6. **If still profitable**: Start with $500-1000 bankroll
7. **Track every bet** meticulously
8. **Reassess after 100 bets**

Good luck finding value in the underdogs! 🐕🥊

