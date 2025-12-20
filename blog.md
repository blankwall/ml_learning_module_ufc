# UFC Fight Prediction as Applied ML Research: From Scraping to ROI-Driven Backtesting

### Why I built this
Predicting MMA is hard: small samples per fighter, noisy outcomes, stylistic non-linearities, and markets that move quickly. I built this as an **applied ML research system**—not just a notebook—designed to answer a practical question:

**Can I build a reproducible UFC prediction engine that produces calibrated win probabilities and supports disciplined, testable betting strategies?**

What follows is what I built, why it’s structured the way it is, and what I learned.

---

### 1) Data collection: scraping UFCStats into a usable dataset
The foundation is high-quality structured data. I pulled comprehensive fight history and fighter stats from UFCStats.com, including:

- **Events & bouts** (who fought, when, weight class, method, rounds, title fights)
- **Fighter profiles** (height, reach, stance, etc.)
- **Fight-level stats** that allow building meaningful performance indicators over time

The key decision here was to make scraping **repeatable** and to separate raw ingestion from derived datasets. Scrapers write raw artifacts, which I can re-parse later without re-hitting the source.

---

### 2) A database that actually supports modeling
Scraped data isn’t model-ready until it’s **linked and queryable**.

I implemented a SQLite database with a clean schema (fighters, events, fights, fight stats). One important lesson I ran into early: UFC event datasets can have **naming collisions** and ordering assumptions (e.g., “fighter_1 is always the winner” in certain sources).

To avoid contaminating the dataset with incorrect joins, I used a simplified and robust population approach that focuses on:

- **Fights** as the atomic truth
- **Events** as metadata attached to fights
- Fighter IDs and normalized names to reduce mismatch risk

Result: a DB I can reliably query for “all bouts up to date X” and “fighter history prior to fight Y,” which is essential for point-in-time ML.

---

### 3) Feature engineering: 299 features, designed for real matchups
The core of predictive performance comes from good features. I engineered **299 features** spanning:

- **Career baseline stats**: striking volume/accuracy/defense, takedowns, submissions, durability
- **Recency features**: rolling last-3 / last-5 / last-N windows, momentum, trend signals
- **Opponent-quality features**: quality-adjusted measures, opponent win-rate aggregates
- **Matchup deltas**: age/height/reach advantages, style and archetype flags
- **Outcome-shape indicators**: finish rates, early-finish risk, round-3 performance

This is the part that makes it “research”: every feature was added with a hypothesis (“what signal could matter?”), then validated by:

- distribution checks
- leakage checks
- fight-level sanity tests
- impact on evaluation and calibration

---

### 4) The feature schema contract: preventing silent drift
One of the easiest ways to accidentally break an ML system is **feature drift caused by column order mismatch** between training and inference.

I solved that with an explicit schema strategy:

- A canonical `schema/feature_schema.json` defines the master list/order
- Feature generation and inference align to that schema
- The pipeline saves model-specific artifacts (`feature_names`, scaler) so models don’t overwrite each other

This avoids the classic failure mode: “same features, different order → different model behavior.”

---

### 5) Model choice: why XGBoost (and why it works here)
I chose **XGBoost** because UFC prediction is fundamentally a structured tabular problem:

- mixed feature types (continuous, binary flags, ratios)
- non-linear interactions (style matchups, aging curves, recency vs career)
- missingness patterns that themselves carry meaning (debut fighters / sparse histories)

XGBoost gives me:

- strong performance on tabular data
- interpretability hooks (feature importance, contribution analysis)
- stability under feature scaling and noisy distributions
- controlled regularization (depth, learning rate, subsample/colsample) to reduce overfit

I trained models with deliberate hyperparameter choices that bias toward generalization:

- moderate tree depth
- lower learning rate
- subsampling for robustness

I also support a clean naming convention so I can keep models distinct:

- `xgboost_model`: intended as **pre-2025** (evaluation / holdout integrity)
- `xgboost_model_with_2025`: includes 2025 data (best for *future* predictions, but must be evaluated carefully)

---

### 6) Evaluation as a product: reproducible reports, not screenshots
I built a full evaluation pipeline that outputs:

- a CSV with fight-level predictions, odds mapping, and metadata
- a JSON summary report
- an HTML report with interactive filtering and summary stats (including underdog metrics)

The evaluation system emphasizes **market-aware scoring**, not just accuracy:

- Brier score / log loss (probability quality)
- calibration curves (confidence reliability)
- AUC (ranking quality)
- betting-relevant summaries (edges, underdog hit rate, ROI simulations)

---

### 7) Data leakage: treat it as a first-class research constraint
UFCStats “current averages” can leak future information if you use them naïvely. A fighter’s career accuracy today includes fights that weren’t known at prediction time.

So I treat point-in-time correctness as a core constraint:

- training data is built from historical fight records
- evaluation supports stricter point-in-time modes to avoid “future-informed stabilization”
- I debugged and fixed real feature bugs (e.g., unit consistency in striking-derived metrics) when they were discovered

This is what makes results worth trusting: when performance moves, we can trace why.

---

### 8) Backtesting: strategies, not vibes
Once you have calibrated probabilities, the next step is a disciplined decision layer.

I built a sophisticated backtesting loop that can simulate strategies on an `eval_data_*.csv` file, including:

- one bet per fight
- configurable strategy selection
- confidence filtering (`min_p`) as a “hold off” mechanism
- flat stake sizing (simple, interpretable)

One example EV winner methodology:

```bash
./.venv/bin/python scripts/backtest_betting_strategy.py \
  --eval-data reports_strict/eval_data_20251216_093142.csv \
  --strategy best_ev \
  --min-p $p \
  --flat-stake 1 \
  --symmetric
```

Example outcome from this approach:

- **eval fights**: 151  
- **bets placed**: 151  
- **total staked**: 151.000 units  
- **total profit**: 18.920 units  
- **ROI**: **12.530%**  
- **bet win rate**: 61.589%  

The important research takeaway: **accuracy is not the objective**. Profitability depends on pricing, calibration, and decision discipline.

---

### 9) What the model actually uses: top features (XGBoost importance)
XGBoost is a great fit here because it naturally captures non-linear interactions (style matchups, aging curves, recency vs baseline) while still giving you a clear look into what the model is leaning on.

From `models/saved/xgboost_model_with_2025_feature_importance.csv`, the most important features are heavily concentrated in a few intuitive buckets:

- **Striking control & differential**
  - `f1_striking_volume_control`, `f2_striking_volume_control`
  - `f1_striking_differential`, `f2_striking_differential`
  - `striking_accuracy_diff`, `striking_output_diff`, `striking_defense_diff`

  These represent whether a fighter consistently *wins the striking exchanges*—not just raw output, but who controls the pace and damage differential.

- **Power / damage events**
  - `f1_knockdowns_lifetime`, `f2_knockdowns_lifetime`

  Knockdowns are sparse but high-signal. In practice, they proxy for “fight-ending power” and the ability to meaningfully change a fight with one sequence.

- **Grappling and anti-grappling**
  - `takedown_ability_diff`, `takedown_defense_diff`, `takedown_matchup`
  - `f1_submission_avg_per_15min`, `f2_submission_avg_per_15min`
  - `f1_ground_strike_rate_lifetime`, `f2_ground_strike_rate_lifetime`
  - `f1_ground_output_per_min_lifetime`, `f2_ground_output_per_min_lifetime`

  This cluster is the “can you impose grappling?” question—plus whether the opponent can stop it, and what happens once fights hit the mat.

- **Aging & recency**
  - `age_difference`
  - `f1_days_since_last_fight`, `f2_days_since_last_fight`
  - `f1_age_x_days_since_last_fight`, `f2_age_x_days_since_last_fight`

  This bucket captures the reality that layoffs and aging aren’t linear. A 34-year-old coming off a long layoff is not the same as a 26-year-old doing the same.

- **Opponent quality**
  - `avg_opponent_win_rate_diff`, `opponent_quality_score_diff`
  - `time_decayed_win_rate_adj_opp_quality_diff`

  This is how I avoid over-crediting padded records. The model is explicitly trying to separate “wins” from “wins against real competition.”

The main pattern: the model is not doing anything magical—it’s combining **control (striking/grappling), power (knockdowns), recency/age effects, and opponent-adjusted performance** into a non-linear decision rule that’s hard to express manually but easy for tree ensembles to learn.

---

### 9) What I accomplished (summary)
This project is now a full pipeline that supports real research iteration:

- **Scraped UFCStats data** into repeatable raw artifacts
- **Built a queryable database** of fighters, fights, and events
- **Engineered 299 features** designed around recency, opponent quality, and matchup deltas
- **Implemented a schema contract** to ensure feature consistency across training/inference
- **Trained XGBoost models** and iterated on feature correctness and stability
- **Built evaluation + HTML reporting** to make results inspectable and reproducible
- **Added backtesting tooling** to convert probabilities into testable betting strategies

---

### 10) Where this goes next
The “next research-level upgrades” are straightforward:

- **Walk-forward validation** (choose thresholds on early events → test on later events)
- **Better market modeling** (closing lines, line-shopping, vigorish handling)
- **Probability calibration** improvements (especially around underdog tails)
- **Feature-level interpretability** (systematic SHAP-based audits and drift checks)
- **More robust point-in-time features** (explicit as-of-date computation everywhere)

The system is now built to support those upgrades without breaking reproducibility—and that’s the real milestone.


