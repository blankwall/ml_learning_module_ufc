# Quick Start: Betting with Your Model

## ✅ **You're Ready to Start!**

Your model:
- 70% accuracy (legitimate, no data leakage)
- 22% ROI on 2025 holdout
- Beats market on disagreements

## 🚀 **3-Step Setup (Next 30 Minutes)**

### Step 1: Train Production Model

```bash
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

⏱️ Takes ~3-5 minutes

### Step 2: Generate Predictions for Dec 13

```bash
python scripts/export_predictions_to_excel.py \
  --input data/predictions/upcoming_fights_fight_night_royval_kape.csv \
  --output data/predictions/dec13_picks.xlsx \
  --model-name xgboost_model_with_2025
```

⏱️ Takes ~30 seconds

### Step 3: Filter for Best Bets

Open `dec13_picks.xlsx` and filter for:
- `edge_f1 > 8%` OR `edge_f2 > 8%`
- `risk_notes` = empty
- NOT middleweight

⏱️ Takes 2 minutes

## 🎯 **Betting Rules (Simple Version)**

### Bet Size Formula:

```
edge = model_prob - market_prob
kelly = edge / (decimal_odds - 1)
bet_amount = bankroll × kelly × 0.25
```

**Or use this simple table:**

| Edge | Bet Size (% of Bankroll) |
|------|--------------------------|
| 8-10% | 1% |
| 10-15% | 2% |
| 15-20% | 3% |
| 20%+ | 4% (max) |

### Example:

```
Bankroll: $1,000
Fight: Chikadze (+185) vs Vallejos (-225)
Model: 55% Chikadze, Market: 35% Chikadze
Edge: 20%
Bet: $40 on Chikadze at +185
```

## ⚠️ **Don't Bet If:**

- ❌ Edge < 8%
- ❌ `risk_notes` has a warning
- ❌ Middleweight fight
- ❌ Model predicting underdog AND confidence < 65%
- ❌ Model A and Model B disagree by >15%

## 📊 **Track Every Bet:**

| Date | Fighter | Odds | Model % | Edge | Bet $ | Result | Profit |
|------|---------|------|---------|------|-------|--------|--------|
| 12/13 | Chikadze | +185 | 55% | +20% | $40 | ? | ? |

After 20+ bets, calculate your real ROI and compare to the model's 22%.

## 🎓 **Learn As You Go:**

### After First 10 Bets:
- Which weight classes did best?
- Did high-edge bets perform better?
- Any patterns in losses?

### After 30 Bets:
- Calculate actual ROI
- If ROI < 10%: Review betting filters
- If ROI > 15%: You're doing great, continue!

### After 100 Bets:
- You have enough data for statistical significance
- Deep dive into what's working
- Add features targeting your weak spots
- Scale up if profitable

## 🏆 **Success Metrics:**

**Week 1:** Make 5-10 bets, track results
**Month 1:** 30-50 bets, ROI > 10%
**Month 3:** 100+ bets, ROI > 12%
**Month 6:** 250+ bets, ROI stable at 10-15%

## 🔧 **Quick Commands:**

### Compare Two Models:
```bash
python scripts/compare_models.py \
  --fighter-1 "Fighter A" \
  --fighter-2 "Fighter B" \
  --model-a xgboost_model \
  --model-b xgboost_model_with_2025
```

### Single Fight Deep Dive:
```bash
python xgboost_predict.py \
  --fighter-1 "Fighter A" \
  --fighter-2 "Fighter B" \
  --model-name xgboost_model_with_2025
```

### Whole Card Preview:
```bash
python -m evaluation.preview_upcoming_fights \
  --input upcoming_card.csv \
  --model-name xgboost_model_with_2025
```

## 💡 **Pro Tips:**

1. **Start Small**: Bet $10-20 per fight until you have 50 bets of data
2. **Trust the Process**: 22% ROI will have variance; some weeks you'll lose
3. **Don't Cherry-Pick**: Bet all qualifying spots, not just "feeling" ones
4. **Track Everything**: Data is how you improve
5. **Update Monthly**: Retrain Model B after each month of new fights
6. **Keep Model A**: Always maintain your clean holdout benchmark

## 🚨 **Red Flags (Stop Betting):**

- Real ROI < 0% after 30 bets (you're losing money)
- Real ROI < 5% after 100 bets (not beating vig)
- Losing >60% of your bankroll (risk of ruin)
- Model and market always agree (no edge)

---

**Your model is ready. Start with the 3-step setup above, make a few small bets on Dec 13, and see how it performs!** 🥊💰

For detailed strategies, see `docs/BETTING_GUIDE.md`.

