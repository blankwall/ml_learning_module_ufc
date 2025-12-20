Ok now I want to create a readme that actually how to use the model 

update the readme with the below information, ignore everything in the readme already

UPDATE tbhis 

BE MORE OF ML RESEARCH PROJECT LESS BETTING FOCUSED

```
# UFC Betting Engine 🥊

An advanced UFC fight prediction and betting analysis system using web scraping, machine learning, and LLM-based analysis.

## Project Overview

This system aims to gain an edge on UFC betting odds by:
1. **Data Collection**: Scraping comprehensive fighter stats and fight history from UFCStats.com
2. **Feature Engineering**: Creating predictive features from historical fight data
3. **ML Models**: Building ensemble models including XGBoost, Neural Networks, and LLM analysis
4. **Odds Analysis**: Comparing predictions against betting lines to identify value bets
5. **Backtesting**: Validating model performance on historical fights
```


This is the correct way to populate the db

we had a collision in naming where events always have fighter 1 win and the ids were not mapping properly so we used this simple db populater focusing on fights themselves instead of the events data 

quick_scripts/populate_db_simple.py

## Project Structure

HIGH LEVEL OVERVIEW OF STRUCTURE NOT SUPER FOCUSED

# UPDATE INSTALL TO USE UV
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

# crete new feature set 

python -m features.feature_pipeline --create --feature-set full



# train the model with 2025 data

 python -m models.xgboost_model \                                                                                     
  --train \                                                             
  --evaluate \                        
  --check-calibration \
  --save-plots \
  --export-schema \
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \
  --learning-rate 0.05 \
  --subsample 0.8 \
  --colsample-bytree 0.8 \
--model-name xgboost_model_with_2025

# train the model without 2025 data for evaluation

python -m models.xgboost_model \
  --train \
  --evaluate \
  --check-calibration \
  --save-plots \
  --export-schema \
  --holdout-from-year 2025 \                    
  --data-path data/processed/training_data.csv \
  --n-estimators 200 \
  --max-depth 4 \       
  --learning-rate 0.05 \
  --subsample 0.8 \       
  --colsample-bytree 0.8


xgboost_model does not contain 2025 data to prevent leakage
xgboost_model_with_2025 is used for prediciting and betting on future events

@predict a single fight 

python xgboost_predict.py --fighter-1 "CAIO BORRALHO" --fighter-2 "Reinier De Ridder" --model xgboost_model_with_2025

remember the ordering is important, all predictions are based on fighter 1, so you may need to swap the fighters if you want to predict the other way.

#evaluate the model for 2025 data
./.venv/bin/python -m evaluation.evaluate_model \
  --data-path data/processed/training_data.csv \
  --odds-path ufc_2025_odds.csv \
  --min-year 2025 \
  --output-dir reports4 \
  --odds-date-tolerance-days 5 \
  --model-name xgboost_model_pre2025 \
  --strict-point-in-time

Evaluation run on 2025+
Optional: --strict-point-in-time to zero out the known leaky base striking/grappling columns during evaluation

here is details on the leakage we found

You’re right about the shape of it: it’s not the “model literally sees the result of the fight it’s predicting” kind of leakage.
But it’s still real leakage, and it can be very impactful, especially for exactly the cases you mention (1–2 fights of history):
What’s leaking: “current” UFCStats-derived career averages stored on the fighters table (and in features/striking.py it can also iterate all linked fights without an as-of-date cut). Those values can implicitly include future fights, so the model is getting a more mature/accurate estimate of the fighter than you’d have at the time.
Why it matters more with sparse history: with 0–2 prior fights, a small amount of “future-informed stabilization” (e.g., true-ish striking accuracy, takedown defense) can dominate the feature vector and swamp the uncertainty you’d actually have pre-fight.


now backtesting the model

(ufc_analysis_v2) ➜  ufc_analysis_v2 git:(feature_refactor) ✗   ./.venv/bin/python scripts/backtest_betting_strategy.py \
    --eval-data reports_strict/eval_data_20251216_093142.csv \
    --strategy best_ev \
    --min-p 0.5 \
    --flat-stake 1 \
    --symmetric; \
> 

================================================================================
BETTING BACKTEST (one bet per fight)
================================================================================
eval fights:         151
bets placed:         66
total staked:        66.000 units
total profit:        21.814 units
ROI:                33.051%
bet win rate:        48.485%
avg EV per unit:     0.5321
avg edge (no-vig):   0.1758


or backtesting on the most recent card  (can you ensure all these files are linked so it is easy to get to themm)


(ufc_analysis_v2) ➜  ufc_analysis_v2 git:(feature_refactor) ✗ python scripts/backtest_manual_card.py --input data/predictions/royval_kape_20251213_results.csv --strategy winner --model-name xgboost_model_with_2025 --min-ev 0.01 --flat-stake 1 --output-csv data/predictions/royval_kape_20251213_results_with_model.csv 
2025-12-20 07:20:29.331 | INFO     | scripts.export_predictions_to_excel:add_model_predictions:217 - Loading XGBoost model 'xgboost_model_with_2025' and feature pipeline...
2025-12-20 07:20:29.344 | SUCCESS  | models.xgboost_model:load_model:469 - Loaded model from models/saved/xgboost_model_with_2025.json
2025-12-20 07:20:29.345 | SUCCESS  | features.feature_pipeline:load_pipeline:187 - Loaded feature pipeline from models/saved (model_name=xgboost_model_with_2025)
2025-12-20 07:20:29.357 | INFO     | database.db_manager:__init__:64 - Database initialized: sqlite:///data/ufc_database.db
2025-12-20 07:20:29.474 | INFO     | features.feature_pipeline:prepare_features:79 - Preparing features for training...
2025-12-20 07:20:29.476 | SUCCESS  | features.feature_pipeline:prepare_features:124 - Prepared 299 features
2025-12-20 07:20:29.546 | INFO     | features.feature_pipeline:prepare_features:79 - Preparing features for training...
2025-12-20 07:20:29.548 | SUCCESS  | features.feature_pipeline:prepare_features:124 - Prepared 299 features
2025-12-20 07:20:29.610 | INFO     | features.feature_pipeline:prepare_features:79 - Preparing features for training...
2025-12-20 07:20:29.612 | SUCCESS  | features.feature_pipeline:prepare_features:124 - Prepared 299 features
2025-12-20 07:20:29.629 | INFO     | features.feature_pipeline:prepare_features:79 - Preparing features for training...
2025-12-20 07:20:29.631 | SUCCESS  | features.feature_pipeline:prepare_features:124 - Prepared 299 features
2025-12-20 07:20:29.664 | INFO     | features.feature_pipeline:prepare_features:79 - Preparing features for training...
2025-12-20 07:20:29.666 | SUCCESS  | features.feature_pipeline:prepare_features:124 - Prepared 299 features

================================================================================
MANUAL CARD BACKTEST | model=xgboost_model_with_2025 | strategy=winner (bet predicted winner) | stake=1u
================================================================================
rows:      5
bets:      5
  fighter_1_name   fighter_2_name  fighter_1_odds  fighter_2_odds  model_p_f1_pct  model_p_f2_pct     ev_f1     ev_f2         bet_name  bet_side    bet_ev   profit
  Brandon Royval       Manel Kape             250            -300            21.4            78.6 -0.251000  0.048000       Manel Kape fighter_2  0.048000 0.333333
   Giga Chikadze   Kevin Vallejos             225            -265            45.9            54.1  0.491750 -0.254849   Kevin Vallejos fighter_2 -0.254849 0.377358
Melquizael Costa Morgan Charriere            -108            -112            64.8            35.2  0.248000 -0.333714 Melquizael Costa fighter_1  0.248000 0.925926
  Steven Asplund      Sean Sharaf            -205             175            71.7            28.3  0.066756 -0.221750   Steven Asplund fighter_1  0.066756 0.487805
    Luana Santos   Melissa Croden            -140             120            59.4            40.6  0.018286 -0.106800     Luana Santos fighter_1  0.018286 0.714286




    ### 1. Feature Pipeline
- Fighter career statistics (strikes, takedowns, submissions)
- Rolling averages (last 3, 5, 10 fights)
- Opponent-adjusted metrics
- Matchup-specific features (reach advantage, age difference)
- Momentum indicators (win streaks, finish rates)


### 2. ML Models
- **XGBoost**: Tree-based model for structured features


### 3. Edge Detection
- Compare model predictions vs. betting lines
- Calculate expected value (EV) for each bet
- Identify profitable betting opportunities


DO NOT INCLUDE ANYTHING ON BETTING OR HOW TO USE THIS MODEL TO MAKE MONEY THIS IS PURELY ACADEMIC