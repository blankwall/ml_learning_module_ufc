You’re already in the right ballpark now (Talbott favored, years_since_last_win_diff showing up as a top feature), so anything else will be **incremental**, not a magic switch to 80–90% for Talbott. That said, there are a few **“obvious next” decline/recency things** you don’t yet encode explicitly:

### 1. Time‑windowed recency instead of just “last N fights”

- **Idea**: Add features that look at a **time window** instead of a fight-count window:
  - `win_rate_last_3_years`, `win_rate_last_2_years`
  - `wins_last_3_years`, `losses_last_3_years`
- **Why**: Cejudo has old wins that still help his career win rate and last_5; what really matters is “what has he done since 2020”.

### 2. Explicit long‑layoff / comeback features

You already have `days_since_last_fight`, but you can make it more informative:

- **Binary flags**:
  - `long_layoff_over_1yr`, `long_layoff_over_2yr`
  - `age_over_35_and_long_layoff` (older comeback after big gap)
- And matchup diffs: `long_layoff_over_1yr_diff`, etc.  
This directly tags “38‑year‑old coming off a big layoff” as a bad sign vs a 27‑year‑old active prospect.

### 3. Time‑decayed performance metrics

- **Idea**: For each fighter, compute **recency‑weighted** win rate and finish rates:
  - e.g. weight fight \(i\) by `exp(-lambda * years_ago)`, then compute:
    - `time_decayed_win_rate`
    - `time_decayed_finish_rate`
- **Why**: Makes old wins from 2015–2018 almost irrelevant compared to post‑2020 performance.

### 4. Trend of recent performance stats (not just level)

You already have `recent_sig_strike_diff_last_3` etc; you can add:

- `trend_sig_strike_diff_last_5` (slope of sig-strike diff over last 5)
- `trend_knockdown_diff_last_5`
- `trend_control_time_diff_last_5`
  
These capture “each recent fight is a little worse than the last”, which is classic decline.

### 5. Activity vs age interaction

- New per‑fighter features:
  - `age_x_days_since_last_fight = age * days_since_last_fight`
  - `age_x_fights_in_last_year = age * fights_in_last_year`  
Older + very inactive (high product) is worse than either alone; for someone like Cejudo this interaction is exactly the worry.

If you want to push this matchup further toward Talbott, I’d start with **(1) 3‑year time‑window win/loss features** and **(2) long‑layoff / age×layoff interaction**, because they speak directly to “hasn’t won since 2020 and is older now.”

---

### 6. Early-finish / KO power profiling (IMPLEMENTED: core per-fighter + differentials)

- Per-fighter features focused on early finishing power:
  - `first_round_finish_rate` (share of wins that end in round 1)
  - `first_round_ko_rate` (share of KO/TKO wins that are in round 1)
  - `early_finish_rate_last_3/5` (fraction of recent wins that are early finishes, e.g. rounds 1–2)
- Matchup differentials:
  - `first_round_finish_rate_diff`
  - `first_round_ko_rate_diff`
  - `early_finish_rate_last_3_diff`, `early_finish_rate_last_5_diff`
- Why: fighters like Manuel Torres are extremely live as dogs because of huge early stopping power; these features should help the model respect those profiles more.

### 7. Small-sample / uncertainty flags (NOT YET IMPLEMENTED)

- Per-fighter:
  - `num_fights_last_3_years` (already derivable but not explicit)
  - `total_fights` threshold flags such as `low_sample_total_fights` (e.g. <= 5–7) and `low_sample_recent_fights` (<= 3 in last 2–3 years)
- Matchup:
  - `low_sample_recent_fights_diff`
  - `low_sample_total_fights_diff`
- Why: when a fighter is a very powerful but unproven finisher with a small sample, the model should avoid overconfident 75/25 style probabilities and lean toward more uncertainty.

### 8. More advanced time-decayed power metrics (NOT YET IMPLEMENTED)

- Per-fighter, using time-decay (e.g. `exp(-lambda * years_ago)`):
  - `time_decayed_win_rate`
  - `time_decayed_finish_rate`
  - `time_decayed_ko_rate`
- Matchup:
  - `time_decayed_win_rate_diff`
  - `time_decayed_finish_rate_diff`
  - `time_decayed_ko_rate_diff`
- Why: helps down-weight very old knockouts and wins while up-weighting current form, especially important for aging vets vs surging prospects.


---


The model is already reading a lot of the right signals (years_since_last_win_diff is now a *top* feature, Talbott has better recent win/finish rates, volume, age, etc.), so to pull this fight further apart you mainly need to:

### 1. Stop over‑rewarding Henry’s old résumé

Right now your **opponent‑quality / experience block** is still giving him a ton of respect:

- Top features: `opponent_quality_score_diff`, `avg_beaten_opponent_total_fights`, `avg_beaten_opponent_win_rate_diff`.
- These are career‑scope; they essentially say “Cejudo beat a lot of really good guys, with long records”.

To damp that for aging, declining fighters:

- **Make opponent‑quality recent-only**:
  - In `_extract_opponent_quality_features`, restrict to fights in the **last N years** (e.g. 3–5), not the whole career, when computing:
    - `avg_opponent_win_rate`
    - `avg_beaten_opponent_win_rate`
    - `avg_opponent_total_fights`
    - `opponent_quality_score`
  - Optionally keep both:
    - `avg_beaten_opponent_win_rate_recent_3y`
    - `opponent_quality_score_recent_3y`
  - Then **drop the all‑time versions from training** (exclude their columns when you build `training_data.csv` or in `FeaturePipeline`), so the model is forced to care about *recent* schedule strength.

### 2. Make age × decline explicitly toxic

Cejudo’s decline is already encoded:

- `fights_since_last_win = 3`
- `years_since_last_win ≈ 5.6`
- `losses_since_last_win = 3` (all decisions)
- `win_rate_last_3 = 0.0`, `recent_vs_career_win_rate` strongly negative.

What’s missing is an **age interaction** that says “this is much worse at 38 than at 27”.

Add per‑fighter interaction features (cheap to compute):

- `age_x_years_since_last_win = age * years_since_last_win`
- `age_x_fights_since_last_win = age * fights_since_last_win`
- `age_x_recent_vs_career_decline = age * max(0, -recent_vs_career_win_rate)`
- Then matchup diffs like:
  - `age_x_years_since_last_win_diff`
  - `age_x_fights_since_last_win_diff`

These will make the model learn patterns like: “old + long time since last win + multiple recent losses” is a much worse profile than “young + small recent skid”.

### 3. Make KO / finishing power recency‑aware only

You’re right that **career‑long KO/finish features** can make old legends look great:

- We already added `early_finish_rate_last_3` / `last_5`, which are good.
- But features like `first_round_finish_rate`, `finish_rate`, `ko_rate` are currently career‑wide.

To avoid “prime Cejudo” propping up “2025 Cejudo”:

- **Either**:
  - Recompute `first_round_finish_rate` and `ko_rate` **only over the last N fights or last 3 years**, same way you did for `win_rate_last_3_years`.
- **Or (simpler / stronger)**:
  - Keep only the **recent** variants in the training set:
    - `finish_rate_last_3`, `finish_rate_last_5`
    - `finish_rate_last_3_years`
    - `early_finish_rate_last_3/5`
  - Drop the global `finish_rate`, `ko_rate`, `first_round_finish_rate` columns from `training_data.csv` / feature pipeline.

That way, KO power is judged by **what they’ve done lately**, not by KOs 8–10 years ago.

### 4. Training-time tweaks (if you’re willing to change training)

Two levers that will systematically push fights like this further toward Talbott:

- **Recency‑weighted sample weights** when training:
  - For each training row, compute years since fight date and set:
    - `sample_weight = exp(-lambda * years_ago)` with, say, `lambda ≈ 0.25–0.35`.
  - This makes more recent fights dominate the trees; old “prime Cejudo” data becomes weak evidence.
- **Monotonic constraints** in XGBoost on key features:
  - Constrain model so that:
    - Increasing `years_since_last_win_diff` (Cejudo more stale vs Talbott) can only **lower** Cejudo’s win prob.
    - Increasing `win_rate_last_3_diff` and `finish_rate_last_3_diff` in Talbott’s favor can only **raise** his win prob.
  - This clamps trees against learning weird counter‑patterns where old résumé occasionally overrides obvious recent decline.

If you apply (2) and (3) in code, and (4) in training, you should see this matchup move from ~57/43 toward something more like low‑60s/upper‑30s for Talbott without blowing up other spots.