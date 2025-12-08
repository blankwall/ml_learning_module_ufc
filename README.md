# UFC Betting Engine 🥊

An advanced UFC fight prediction and betting analysis system using web scraping, machine learning, and LLM-based analysis.

## Project Overview

This system aims to gain an edge on UFC betting odds by:
1. **Data Collection**: Scraping comprehensive fighter stats and fight history from UFCStats.com
2. **Feature Engineering**: Creating predictive features from historical fight data
3. **ML Models**: Building ensemble models including XGBoost, Neural Networks, and LLM analysis
4. **Odds Analysis**: Comparing predictions against betting lines to identify value bets
5. **Backtesting**: Validating model performance on historical fights

## Project Structure

```
ufc_analysis_v2/
├── scrapers/              # Web scraping modules
│   ├── fighter_scraper.py    # Scrape individual fighter pages
│   ├── event_scraper.py      # Scrape event and fight data
│   └── odds_scraper.py       # Scrape betting odds (future)
├── database/              # Database schema and management
│   ├── schema.py            # SQLAlchemy models
│   ├── db_manager.py        # Database operations
│   └── migrations/          # Database migrations
├── features/              # Feature engineering
│   ├── fighter_features.py  # Fighter-level features
│   ├── matchup_features.py  # Fight matchup features
│   └── rolling_stats.py     # Time-series features
├── models/                # ML models
│   ├── baseline_models.py   # XGBoost, Random Forest
│   ├── neural_net.py        # Deep learning models
│   ├── llm_analyzer.py      # LLM-based analysis
│   └── ensemble.py          # Model ensembling
├── backtesting/           # Backtesting framework
│   ├── backtest_engine.py   # Run historical predictions
│   └── metrics.py           # Performance metrics
├── dashboard/             # Visualization and UI
│   ├── app.py              # Streamlit dashboard
│   └── components/         # Dashboard components
├── data/                  # Data storage
│   ├── raw/               # Raw scraped HTML
│   ├── processed/         # Cleaned data
│   └── predictions/       # Model outputs
├── config/                # Configuration files
│   └── config.yaml        # Project settings
├── notebooks/             # Jupyter notebooks for analysis
└── tests/                 # Unit tests
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Phase 1: Data Collection
```bash
# Scrape all fighters
python scrapers/fighter_scraper.py --mode all

# Scrape specific event
python scrapers/event_scraper.py --event-id UFC-319

# Update database
python database/db_manager.py --populate
```

### Phase 2: Model Training
```bash
# Train baseline models
python models/baseline_models.py --train

# Train neural network
python models/neural_net.py --epochs 100
```

### Phase 3: Generate Predictions
```bash
# Predict upcoming fights
python predict.py --event "UFC-320"
```

### Phase 4: Launch Dashboard
```bash
streamlit run dashboard/app.py
```

## Data Sources

- **UFCStats.com**: Fighter stats, fight history, event data
- **BestFightOdds.com**: Historical and current betting lines (future)
- **Tapology.com**: Additional fighter rankings and news (future)

## Model Architecture

### 1. Feature Pipeline
- Fighter career statistics (strikes, takedowns, submissions)
- Rolling averages (last 3, 5, 10 fights)
- Opponent-adjusted metrics
- Matchup-specific features (reach advantage, age difference)
- Momentum indicators (win streaks, finish rates)

### 2. ML Models
- **AutoGluon** (Recommended): Automated ML that trains 10-20 models automatically
- **XGBoost**: Tree-based model for structured features
- **Neural Network**: Deep learning for complex patterns
- **LLM Analyzer**: GPT-4 for qualitative fight analysis
- **Ensemble**: Weighted combination of all models

### 3. Edge Detection
- Compare model predictions vs. betting lines
- Calculate expected value (EV) for each bet
- Identify profitable betting opportunities

## Performance Metrics

- **Accuracy**: Overall prediction accuracy
- **Log Loss**: Probabilistic prediction quality
- **ROI**: Return on investment for betting strategy
- **Calibration**: Prediction reliability at different confidence levels

## Development Roadmap

- [x] Phase 1: Data Scraping Infrastructure
- [ ] Phase 2: Database Design
- [ ] Phase 3: Feature Engineering
- [ ] Phase 4: Baseline ML Models
- [ ] Phase 5: Advanced Models & LLM Integration
- [ ] Phase 6: Odds Integration & Edge Detection
- [ ] Phase 7: Backtesting Framework
- [ ] Phase 8: Production Dashboard

## 📚 Documentation

### Getting Started
- **[SETUP.md](SETUP.md)** - Complete installation and setup guide
- **[WORKFLOW.md](WORKFLOW.md)** - Visual guide to the project workflow
- **[DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md)** - Step-by-step data collection

### Model Strategy
- **[AUTOGLUON_GUIDE.md](AUTOGLUON_GUIDE.md)** - Using AutoGluon for automated ML
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete technical documentation

### Betting Strategy 🎯
- **[VALIDATION_WORKFLOW.md](VALIDATION_WORKFLOW.md)** - ⭐ **START HERE: Dual-track validation strategy**
- **[UNDERDOG_STRATEGY.md](UNDERDOG_STRATEGY.md)** - Why underdogs are where edge exists
- **[EDGE_VALIDATOR_GUIDE.md](EDGE_VALIDATOR_GUIDE.md)** - How to validate if you have real edge
- **[NO_EDGE_GUIDE.md](NO_EDGE_GUIDE.md)** - What to do if model doesn't beat the market

## ⚠️ Reality Check: Does This Actually Work?

**Important**: Having a 66% accurate model doesn't guarantee betting profits!

```
Your Model: 66% accurate ✅
Bookmakers: ~65% accurate ⚠️
Your Edge: Maybe 1-2% (not enough!) ❌
```

### 🎯 Key Insight: Edge is Fight-by-Fight

You don't bet EVERY fight - you find specific fights where your model disagrees with the market:

```python
UFC Event (10 fights):
├─ Fight 1: Your model 65%, Market 52% → 13% EDGE! ✅ BET
├─ Fight 2: Your model 48%, Market 48% → No edge ❌ SKIP
├─ Fight 3: Your model 41%, Market 45% → No edge ❌ SKIP
└─ Fight 4: Your model 58%, Market 52% → 6% EDGE! ✅ BET

Result: Bet 2 out of 10 fights (selective!)
```

### 🧪 Validation Strategy: The Dual-Track Approach

**Before betting ANY money, validate your edge-finding system TWO ways:**

```bash
# Track 1: Backtest on last 100 completed fights
python scripts/backtest_last_100.py

# Track 2: Paper trade upcoming 50 fights
python scripts/paper_trade_tracker.py
```

**Only bet real money if BOTH tracks show 5%+ ROI!**

**Read**: [VALIDATION_WORKFLOW.md](VALIDATION_WORKFLOW.md) for complete guide.

**Most likely outcome**: Your model works well but doesn't beat the market. That's OK! It's still a valuable learning project.

## Contributing

This is a research project. Key areas for improvement:
- Additional data sources
- Novel feature engineering
- Advanced model architectures
- Real-time odds monitoring

## Disclaimer

This tool is for **research and educational purposes only**. 

⚠️ **BETTING WARNING**: Most ML models, even accurate ones, do NOT beat bookmaker odds. The betting market is highly efficient. Only bet if you've validated real edge over 100+ fights. Betting involves risk. Always gamble responsibly and within your means. Past performance does not guarantee future results.

## License

MIT License - See LICENSE file for details

