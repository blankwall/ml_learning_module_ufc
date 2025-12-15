# HTML Report Example

## ✅ Your Report is Ready!

**Location**: `reports/model_evaluation_2025.html`

**To open**: Copy and paste this into your browser's address bar:
```
file:///Users/tylerbohan/code/ufc_analysis_v2/reports/model_evaluation_2025.html
```

Or in Terminal:
```bash
open reports/model_evaluation_2025.html
```

## What You'll See

### 1. Header (Top of Page)

```
🥊 UFC Model Evaluation Report
2025 Season Performance Analysis

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Overall Accuracy│ Correct Preds   │ Events Analyzed │ Model Version   │
│      69.5%      │    171/246      │       15        │      2025       │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 2. Event List (Collapsible Sections)

```
▼ UFC Fight Night: Royval vs. Kape    December 13, 2025    11/13 Fights    84% ✓
  
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Fight            │ Model Pred │ Market │ Edge  │ Winner  │ Result   │
  ├────────────────────────────────────────────────────────────────────────┤
  │ Giga Chikadze    │ 83.2% ████ │ 72.6%  │ +10.6%│ Giga    │    ✓     │  🟢
  │ vs               │            │        │       │         │          │
  │ Kevin Vallejos   │            │        │       │         │          │
  ├────────────────────────────────────────────────────────────────────────┤
  │ Brandon Royval   │ 61.6% ███  │ 28.6%  │ +33.0%│ Brandon │    ✓     │  🟢
  │ vs               │            │        │       │         │          │
  │ Manel Kape       │            │        │       │         │          │
  ├────────────────────────────────────────────────────────────────────────┤
  │ Amanda Lemos     │ 63.5% ███  │ 41.2%  │ +22.4%│ Gillian │    ✗     │  🔴
  │ vs               │            │        │       │         │          │
  │ Gillian Robertson│            │        │       │         │          │
  └────────────────────────────────────────────────────────────────────────┘


▼ UFC 310: Pantoja vs. Asakura    December 7, 2025    10/13 Fights    77% ~

▼ UFC Fight Night: Moreno vs. Albazi    November 30, 2025    8/11 Fights    73%

▼ UFC 309: Jones vs. Miocic    November 16, 2025    10/13 Fights    77%
```

### 3. Color Coding

**Green Rows** (Correct Prediction):
- Model correctly predicted the winner
- High confidence (>60%)
- Example: Predicted Chikadze at 83%, Chikadze won ✓

**Yellow Rows** (Close Call):
- Model correctly predicted the winner
- Low confidence (<60%)
- Example: Predicted Fighter A at 52%, Fighter A won ~

**Red Rows** (Incorrect):
- Model predicted wrong winner
- Example: Predicted Lemos at 63%, Robertson won ✗

### 4. Interactive Features

**Click any event header** to expand/collapse:
```
▼ UFC Fight Night: Royval vs. Kape    [Click to collapse]
  [...fights visible...]

▶ UFC 310: Pantoja vs. Asakura        [Click to expand]
  [...fights hidden...]
```

**Probability Bars**:
```
Model:  ████████████████████ 83.2%  (Blue bar)
Market: █████████████ 72.6%         (Gray bar)
```

**Edge Indicators**:
- `+10.6%` in green = Model more confident than market
- `-5.2%` in red = Market more confident than model
- `0.0%` in gray = Model and market agree

## Report Statistics

Based on your current evaluation:

- **Overall Accuracy**: 69.5% (171 correct out of 246 fights)
- **Events Covered**: 15 UFC events in 2025
- **Best Event**: Multiple events at 84%+ accuracy
- **Toughest Event**: Events around 50-60% accuracy

## How to Use This Report

### For Model Improvement

1. **Find patterns in red rows** (incorrect predictions):
   - Same weight class losing often? → Add weight-class features
   - Low edge fights losing? → Increase minimum edge threshold
   - Upsets failing? → Improve upset detection features

2. **Check yellow rows** (close calls):
   - Correct but low confidence = luck or skill?
   - If many yellow rows → Model is well-calibrated
   - If few yellow rows → Model might be overconfident

3. **Review green rows** (correct high confidence):
   - What features drove these correct picks?
   - Can you identify more fights like these?

### For Betting Strategy

1. **Calculate profitability by event**:
   - Which events were most profitable?
   - Did high-edge picks perform better?
   - Were favorites or underdogs more accurate?

2. **Review bet sizing**:
   - Did you bet on all high-edge fights?
   - Should you have skipped low-confidence picks?
   - Were there filters you should apply?

3. **Compare model to market**:
   - Green edges (model > market) = profitable?
   - Red edges (market > model) = unprofitable?
   - What edge threshold maximizes profit?

### For Presentations

1. **Screenshot the header** for overall stats
2. **Expand best events** to show model's strengths
3. **Discuss learning** from incorrect predictions
4. **Share the HTML file** (it's standalone, works offline)

## Next Steps After Reviewing

1. **Identify Weak Spots**:
```bash
# Which weight classes did worst?
# Which fighters fooled the model?
# What features were misleading?
```

2. **Improve Features**:
```python
# Add features targeting weak spots
# Remove features that didn't help
# Test new feature combinations
```

3. **Retrain and Compare**:
```bash
# Train new model
# Generate new report
# Compare side-by-side
```

4. **Update Betting Strategy**:
```
# Adjust edge thresholds
# Add filters for weak categories
# Increase stakes in strong categories
```

## Sharing the Report

### Via Email
- Just attach the HTML file
- Recipients can open directly in browser
- No installation or server needed

### Via Cloud
- Upload to Dropbox/Google Drive
- Share link
- Others can download and view

### Via Website
- Upload to GitHub Pages (free)
- Gets a public URL like: `username.github.io/ufc-model-report.html`
- Professional presentation

### Via Screenshot
- Take screenshots of key sections
- Share in Slack/Discord/Twitter
- Great for quick updates

## Tips & Tricks

### Find Specific Fights
Use Ctrl+F (Cmd+F on Mac) to search:
- Fighter names: "Brandon Royval"
- Event names: "UFC 310"
- Dates: "December 7"

### Print to PDF
1. Expand all events you want
2. File → Print
3. Save as PDF
4. Now you have an archival copy

### Compare Two Models
Generate two reports and open side-by-side:
- Left: Model A (without 2025 data)
- Right: Model B (with 2025 data)
- Compare predictions fight-by-fight

### Mobile Viewing
The report is fully responsive:
- Open on phone/tablet
- Tap to expand events
- Scroll and zoom as needed

---

**Enjoy exploring your model's performance! 🚀**

For more details, see `docs/HTML_REPORTS.md`

