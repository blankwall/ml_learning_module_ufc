# Interactive HTML Evaluation Reports

## Overview

The HTML report provides a beautiful, interactive visualization of your model's performance across all 2025 UFC events.

## Features

- 📊 **Event-by-Event Breakdown**: Each UFC event is a collapsible section
- ✅ **Color-Coded Results**: Green (correct), Red (incorrect), Yellow (close call)
- 📈 **Visual Probability Bars**: See model confidence at a glance
- 🎯 **Edge Analysis**: Compare model predictions to market odds
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile

## Quick Start

### Option 1: Auto-Generate During Evaluation

The HTML report is automatically generated when you run the evaluation script:

```bash
python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2025_odds.csv \
  --min-year 2025 \
  --output-dir reports
```

This will create:
- `reports/eval_data_TIMESTAMP.csv` (raw data)
- `reports/model_evaluation_TIMESTAMP.html` (interactive report)

### Option 2: Generate from Existing Data

If you already have evaluation data, generate the report with:

```bash
# Using the quick script (finds latest eval_data automatically)
./scripts/generate_report.sh

# Or manually specify the eval data
python -m evaluation.generate_html_report \
  --eval-data reports/eval_data_20251212_095654.csv \
  --output reports/my_report.html \
  --min-year 2025
```

## Understanding the Report

### Header Section

Shows overall statistics:
- **Overall Accuracy**: Percentage of correct predictions
- **Correct Predictions**: X/Y fights predicted correctly
- **Events Analyzed**: Number of UFC events
- **Model Version**: Which model was used

### Event Sections

Each event is collapsible and shows:

**Event Header:**
- Event name (e.g., "UFC Fight Night: Royval vs. Kape")
- Event date
- Number of fights
- Event accuracy (color-coded)

**Fight Details:**
- **Fight**: Both fighters' names
- **Model Prediction**: Who the model picked and confidence level
- **Market Odds**: What the betting market implied
- **Edge**: Model vs market difference
- **Actual Winner**: Who actually won
- **Result**: ✓ (correct), ✗ (incorrect), ~ (correct but close)

### Color Coding

**Row Colors:**
- 🟢 **Green**: Correct prediction with high confidence (>60%)
- 🟡 **Yellow**: Correct prediction but low confidence (<60%)
- 🔴 **Red**: Incorrect prediction

**Event Accuracy Colors:**
- 🟢 **Green**: ≥80% accuracy
- 🟡 **Orange**: 60-79% accuracy
- 🔴 **Red**: <60% accuracy

**Edge Colors:**
- 🟢 **Green**: Positive edge (model more confident than market)
- 🔴 **Red**: Negative edge (market more confident than model)
- ⚪ **Gray**: Neutral (model and market agree)

## Use Cases

### 1. Post-Event Analysis

After each UFC event, generate the report to:
- See which fights you predicted correctly
- Identify patterns in your misses
- Find where model had edge over market

### 2. Model Comparison

Generate reports for different models to compare:

```bash
# Model A (baseline without 2025)
python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2025_odds.csv \
  --min-year 2025 \
  --output-dir reports/model_a

# Model B (with 2025 data)
python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2025_odds.csv \
  --min-year 2025 \
  --output-dir reports/model_b

# Now compare:
# reports/model_a/model_evaluation_TIMESTAMP.html
# reports/model_b/model_evaluation_TIMESTAMP.html
```

### 3. Betting Review

Use the report to review your betting decisions:
- Did you bet on the fights with highest edge?
- Were your losses mostly on low-confidence picks?
- Which events were most profitable?

### 4. Stakeholder Presentation

Share the report with:
- Betting partners
- Investors
- Friends interested in your model

The professional design makes it easy to demonstrate your model's performance.

## Customization

### Change Colors

Edit `evaluation/generate_html_report.py` and modify the `<style>` section:

```python
# Find these lines and change colors:
.row-correct {
    background: #e8f5e9 !important;  # Light green
    border-left: 4px solid #4caf50;  # Green
}
```

### Add More Metrics

Add columns to the fights table:

```python
# In the <thead> section, add:
<th>New Column</th>

# In the <tbody> section, add:
<td>{new_value}</td>
```

### Change Event Sorting

By default, events are sorted by date (oldest first). To change:

```python
# In generate_html_report function:
events = events.sort_values("accuracy", ascending=False)  # Best accuracy first
# Or:
events = events.sort_values("event_date", ascending=False)  # Newest first
```

## Troubleshooting

### Report is blank or missing events

**Problem**: No data for specified year
**Solution**: Check that you have evaluation data for 2025

```bash
python -c "import pandas as pd; df = pd.read_csv('reports/eval_data_TIMESTAMP.csv'); print(df['event_year'].unique())"
```

### Event names show as "Event 123"

**Problem**: Database connection issue
**Solution**: Ensure your database path is correct in `database/db_manager.py`

### HTML doesn't open automatically

**Solution**: Manually open the file:

```bash
# macOS
open reports/model_evaluation_2025.html

# Linux
xdg-open reports/model_evaluation_2025.html

# Windows
start reports/model_evaluation_2025.html

# Or copy the path and paste in browser:
file:///Users/yourname/code/ufc_analysis_v2/reports/model_evaluation_2025.html
```

### Colors don't match expectations

**Problem**: Different interpretation of "correct"
**Solution**: Check the definition in the code:

```python
# A prediction is correct if:
correct = (model_prob_f1 >= 0.5) == target
# Where target = 1 means f1 won, target = 0 means f2 won
```

## Examples

### Example 1: Perfect Event

```
UFC 300: Pereira vs. Hill    April 13, 2025    13/13 Fights    100% ✓
```

All 13 fights predicted correctly! Click to expand and see details.

### Example 2: Close Call Event

```
UFC Fight Night: Burns vs. Brady    March 8, 2025    8/11 Fights    73% ~
```

8 out of 11 correct. Some fights were close calls (low confidence but still correct).

### Example 3: Tough Event

```
UFC 298: Volkanovski vs. Topuria    Feb 17, 2025    6/12 Fights    50% ✗
```

Only 50% accuracy. Click to see which fights were missed and why.

## Advanced Tips

### 1. Screen Recording for Presentations

Record a screen capture while clicking through the report:
- Shows interactivity
- Demonstrates model performance
- Professional presentation

### 2. Export to PDF

Print the report to PDF for archival:
1. Open HTML in browser
2. Expand all events (click each header)
3. Print → Save as PDF

### 3. Share via Web Hosting

Upload the HTML file to:
- GitHub Pages
- Netlify
- AWS S3 + CloudFront
- Your own web server

No backend needed - it's a standalone HTML file!

### 4. Embed in Notion/Confluence

Some tools allow embedding HTML:
- Upload to file hosting
- Use iframe to embed
- Share with team

## Performance

The HTML report is optimized for:
- **Speed**: Loads instantly even with 100+ fights
- **Size**: Typically <200KB per event
- **Compatibility**: Works in all modern browsers
- **Mobile**: Responsive design, touch-friendly

## Future Enhancements

Possible improvements (contributions welcome!):

- [ ] Add charts (win rate over time, accuracy by weight class)
- [ ] Filter fights by weight class, accuracy, edge
- [ ] Export individual events to separate pages
- [ ] Dark mode toggle
- [ ] Search/filter functionality
- [ ] Comparison mode (side-by-side two models)
- [ ] Bet tracking integration
- [ ] Real-time updates during events

## Credits

Built with:
- Pure HTML/CSS/JavaScript (no dependencies!)
- Gradient styling inspired by UFC branding
- Responsive design for all devices

---

**Questions or suggestions?** Check the main README or open an issue!

