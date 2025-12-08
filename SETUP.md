# UFC Betting Engine - Setup Guide

## Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- 8GB+ RAM for training models
- OpenAI or Anthropic API key (optional, for LLM analysis)

## Installation

### 1. Clone and Setup Environment

```bash
cd /Users/tylerbohan/code/ufc_analysis_v2

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Optional: For LLM-based analysis
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: For PostgreSQL (default uses SQLite)
DB_PASSWORD=your_db_password_here
```

### 3. Initialize Project Structure

```bash
# Create necessary directories
mkdir -p data/{raw,processed,predictions}
mkdir -p models/saved
mkdir -p logs
```

## Usage Workflow

### Phase 1: Data Collection

#### Step 1: Scrape Fighter Data

```bash
# Test with a single fighter
python scrapers/fighter_scraper.py --mode single --fighter-id 64a50dad704d1d49

# Scrape all fighters (this will take several hours due to rate limiting)
python scrapers/fighter_scraper.py --mode all --output data/processed/fighters.json
```

#### Step 2: Scrape Event Data

```bash
# Parse the existing UFC 319 event
python scrapers/event_scraper.py --mode file --file ufc_319.html

# Scrape all events (also takes several hours)
python scrapers/event_scraper.py --mode all --output data/processed/events.json
```

#### Step 3: Scrape Detailed Fight Statistics

**IMPORTANT:** After scraping events, you must scrape the detailed fight statistics (round-by-round data):

```bash
# Scrape detailed stats for all fights from the events file
# This will take several hours as it visits each fight detail page
python scrapers/event_scraper.py --mode fight-details \
  --events-file data/processed/events.json \
  --output data/processed/fight_details.json
```

This extracts critical data like:
- Round-by-round strike statistics
- Significant strikes by position (distance, clinch, ground)
- Strikes to head, body, and legs
- Takedown attempts and success rates
- Submission attempts
- Control time
- Knockdowns

### Phase 2: Database Setup

```bash
# Populate database from scraped data
python database/db_manager.py --populate \
  --fighters-file data/processed/fighters.json \
  --events-file data/processed/events.json \
  --fight-details-file data/processed/fight_details.json

# Check database stats
python database/db_manager.py --stats
```

Expected output:
```
Database Statistics:
  Fighters: 3000+
  Events: 500+
  Fights: 6000+
  Predictions: 0
```

### Phase 3: Feature Engineering ⚠️ **REQUIRED**

**Important**: Feature engineering is **always required**, even if using AutoGluon!

AutoGluon doesn't create features - it optimizes models using the features you provide.

```bash
# Create training dataset with 100+ engineered features
python features/feature_pipeline.py --create

# Prepare features for training (scaling, preprocessing)
python features/feature_pipeline.py --prepare
```

This creates:
- `data/processed/training_data.csv` - Raw training data with 100+ features
- `data/processed/prepared_data.csv` - Scaled and ready for ML
- `models/saved/feature_scaler.pkl` - Saved feature pipeline

**Features Created:**
- Physical attributes (height, reach, age differences)
- Career statistics (striking, grappling, defense)
- Rolling statistics (last 3, 5, 10 fights)
- Momentum indicators (win streaks, recent form)
- Matchup features (style advantages, common opponents)
- 100+ total features for ML models

### Phase 4: Train Models

You have **two options**: AutoGluon (recommended) or Manual Models

#### Option A: AutoGluon (Recommended) 🎯

**Best choice for most users** - Automatic model selection and tuning

```bash
# Install AutoGluon (one time)
pip install autogluon.tabular

# Train (1 hour for best quality)
python models/autogluon_model.py --train --time-limit 3600 --quality best_quality

# Evaluate
python models/autogluon_model.py --evaluate
```

**What AutoGluon Does:**
- Automatically trains 10-20 different model types
- Tunes hyperparameters for each model
- Creates multi-level ensembles
- Selects the best performing combination
- Typically achieves 2-5% better accuracy than manual models

**Expected Results:**
- Training time: 1-2 hours
- Accuracy: ~66% (2-4% better than manual)
- ROC AUC: ~0.72

See `AUTOGLUON_GUIDE.md` for detailed information.

#### Option B: Manual Models (Educational)

**Good for learning** - Full control over each model

##### Train XGBoost Model (Recommended)

```bash
# Train XGBoost model (takes 1-5 minutes)
python -m models.xgboost_model --train --evaluate --show-importance

# With custom parameters
python -m models.xgboost_model --train --evaluate \
    --n-estimators 200 \
    --max-depth 6 \
    --learning-rate 0.1

# Hyperparameter tuning (takes 30-60 mins)
python -m models.xgboost_model --train --tune --cv-folds 5

# Cross-validation only
python -m models.xgboost_model --cross-validate --cv-folds 5

# Check calibration
python -m models.xgboost_model --train --check-calibration --save-plots
```

Expected training time: 10-30 minutes

##### Train Neural Network

```bash
python models/neural_net.py --train --evaluate
```

Expected training time: 20-60 minutes (faster with GPU)

#### Which Should You Use?

| Use Case | Recommendation |
|----------|----------------|
| **Production betting system** | ✅ XGBoost |
| **Full control & interpretability** | ✅ XGBoost |
| **Fast training (minutes)** | ✅ XGBoost |
| **Feature importance analysis** | ✅ XGBoost |
| **Learning & improving** | ✅ XGBoost |
| **Understanding predictions** | ✅ XGBoost |

**Recommendation**: Use XGBoost for production betting. Fast, interpretable, and gives you full control.

**See `XGBOOST_GUIDE.md` for complete XGBoost documentation.**

### Phase 5: Generate Predictions

#### Predict Specific Fight

```bash
# By fighter names
python predict.py --fighter-1 "Khamzat Chimaev" --fighter-2 "Dricus Du Plessis"

# Using ensemble model directly
python models/ensemble.py --predict --fighter-1 1 --fighter-2 2
```

#### Predict Entire Event

```bash
python predict.py --event UFC-319
```

### Phase 6: Backtesting

```bash
# Run backtest on historical data
python backtesting/backtest_engine.py --start-date 2020-01-01 --end-date 2024-12-31
```

This will:
- Generate predictions for all historical fights
- Simulate betting strategy
- Calculate ROI, win rate, max drawdown
- Save results to `data/predictions/backtest_results_*.csv`

### Phase 7: Launch Dashboard

```bash
# Start Streamlit dashboard
streamlit run dashboard/app.py
```

The dashboard will be available at: http://localhost:8501

## Troubleshooting

### Issue: "No module named 'database'"

**Solution**: Make sure you're in the project root directory and your virtual environment is activated.

### Issue: "Models not found"

**Solution**: Train the models first using the commands in Phase 4.

### Issue: "Database empty"

**Solution**: Run the scraper and populate the database (Phase 1-2).

### Issue: "Out of memory during training"

**Solution**: Reduce batch size in `config/config.yaml`:
```yaml
models:
  neural_net:
    batch_size: 16  # Reduce from 32
```

### Issue: Rate limiting from UFCStats.com

**Solution**: The scraper has built-in rate limiting (1 second between requests). If you still get blocked, increase the `rate_limit` in config.yaml.

## Quick Test Run

For a quick test with minimal data:

```bash
# 1. Parse the included UFC 319 event
python scrapers/event_scraper.py --mode file --file ufc_319.html

# 2. Populate database
python database/db_manager.py --populate --events-file data/processed/events.json

# 3. Check stats
python database/db_manager.py --stats

# 4. Create features (still needed!)
python features/feature_pipeline.py --create --prepare

# 5. Train quick model (10 minute AutoGluon test)
python models/autogluon_model.py --train --time-limit 600 --quality good_quality

# 6. Launch dashboard
streamlit run dashboard/app.py
```

## Next Steps

1. **Collect More Data**: Run full scraping to get comprehensive fighter database
2. **Feature Engineering**: Always run feature pipeline first (required!)
3. **Train Models**: Use AutoGluon for best results, or manual models for learning
4. **Add Betting Odds**: Integrate odds scraper for real edge detection
5. **Optimize Strategy**: Tune betting parameters in config.yaml
6. **Monitor Performance**: Track predictions vs actual results

### Recommended Workflow:
```bash
# 1. Data Collection
./collect_data.sh  # Runs all scraping steps

# 2. Feature Engineering (REQUIRED)
python features/feature_pipeline.py --create --prepare

# 3. Model Training (CHOOSE ONE)
# Option A: AutoGluon (best results)
python models/autogluon_model.py --train --time-limit 3600

# Option B: Manual models (learning/control)
python models/baseline_models.py --train --evaluate

# 4. Generate Predictions
python predict.py --fighter-1 "Fighter A" --fighter-2 "Fighter B"

# 5. Launch Dashboard
streamlit run dashboard/app.py
```

## Project Structure Reference

```
ufc_analysis_v2/
├── config/              # Configuration files
├── scrapers/           # Web scraping modules
├── database/           # Database schema and management  
├── features/           # Feature engineering
├── models/             # ML models
├── backtesting/        # Backtesting framework
├── dashboard/          # Streamlit dashboard
├── data/               # Data storage
│   ├── raw/           # Cached HTML
│   ├── processed/     # Cleaned data
│   └── predictions/   # Model outputs
├── logs/              # Application logs
└── models/saved/      # Trained models
```

## Tips for Best Results

1. **Data Quality**: More data = better predictions. Run full scraping.
2. **Feature Engineering**: The quality of features matters most.
3. **Model Ensemble**: Use ensemble for best predictions.
4. **Conservative Betting**: Start with small stakes and proven edge.
5. **Track Everything**: Log all predictions and results.

## Support

For issues or questions:
1. Check logs in `logs/ufc_engine.log`
2. Review configuration in `config/config.yaml`
3. Verify database with `--stats` flag

## Disclaimer

This tool is for **educational and research purposes only**. 

- Past performance does not guarantee future results
- Betting involves substantial risk of loss
- Always gamble responsibly and within your means
- Check local laws regarding sports betting

**Use at your own risk.**

