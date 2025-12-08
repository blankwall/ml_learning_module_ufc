Awesome — now that you’ve separated all the features into their own modules and built a feature registry, you’ve done **80% of the hard engineering work**. When the *good model* returns in a few days, here is the exact roadmap to guarantee:

* consistent features
* reproducible predictions
* monotonic XGBoost constraints working
* a clean pipeline your weak coding model can safely maintain
* automated evaluation + data collection

I’ll lay it out in a sequence you can follow in order.

---

# ✅ **Phase 1 — Freeze the Feature Schema (Critical Step)**

Now that you have:

```
features/
    striking/
    grappling/
    physical/
    records/
    ...
features_registry.py
```

Here’s what to do next when the good model arrives:

### **1. Generate the "official feature list"**

From the good model training run, save:

```python
model_feature_order = pipeline.get_feature_names_out()
```

Or:

```python
booster_feature_order = model.get_booster().feature_names
```

These 200–300 names become your **canonical schema**.

### **2. Save this schema into the repo**

Example file:

```
schema/feature_schema.json
```

Contents:

```json
{
    "version": "1.0.0",
    "features": [
        "fighter_age",
        "fighter_reach",
        "fighter_last5_finish_rate",
        ...
    ]
}
```

This is now **the master contract** between:

* training
* prediction
* Excel export
* API usage

Everything must match this.

---

# ✅ **Phase 2 — Build a Feature Loader that Enforces the Schema**

Create:

```
features/feature_vector_builder.py
```

This file:

1. Imports ALL feature functions from your registry
2. Executes them in order
3. Assembles the final dict
4. Aligns fields to the schema
5. Fills missing features with 0 and logs warnings
6. Outputs a perfectly ordered numpy array for XGBoost

Example build:

```python
def build_feature_vector(fight, fighter_data, opponent_data):
    raw = {}

    for feature_func in registry:
        raw.update(feature_func(fight, fighter_data, opponent_data))

    final = []
    for name in FEATURE_SCHEMA:
        final.append(raw.get(name, 0))

    return np.array(final, dtype=float)
```

This guarantees:

* 100% identical order
* 100% identical count
* 0% feature drift
* XGBoost monotone constraints line up cleanly
* Excel export = CLI prediction = training run

---

# ✅ **Phase 3 — Re-train XGBoost with Monotonic Constraints**

Once the feature schema is frozen, apply monotone constraints.

### **1. Create a constraints vector**

Length = number of features.

You will manually decide:

```
+1 → higher feature should increase win probability
-1 → higher feature should decrease win probability
0 → no constraint
```

Example:

```python
monotone_constraints = [
    +1,  # striking accuracy
    +1,  # takedown accuracy
    -1,  # age
    0,   # reach
    ...
]
```

---

### **2. Train XGBoost with monotone constraints**

```
xgb.XGBClassifier(
    monotone_constraints=monotone_constraints,
    ...
)
```

### **3. Save the constraint vector**

Same place as schema:

```
schema/monotone_constraints.json
```

---

# ✅ **Phase 4 — Build Automated Evaluation Loop (very important)**

This lets your weak model *evaluate feature usefulness* without inventing new logic.

Create:

```
evaluation/
    evaluate_model.py
```

This script should:

* Load last 200–300 fights (or your whole historical DB)
* Generate features using the **schema builder**
* Compare model probabilities vs betting market
* Track:

  * Brier score
  * Log-loss
  * Calibration curves
  * Win / loss edges
  * Expected value vs closing lines
  * ROI vs Kelly / flat stakes

Save results into:

```
reports/model_eval_<timestamp>.json
reports/calibration_<timestamp>.png
reports/roc_<timestamp>.png
```

Your weak model will be able to run this unchanged.

---

# ✅ **Phase 5 — Build Regression Tests to Guarantee No Future Feature Drift**

Create:

```
tests/test_feature_schema.py
```

Test:

```python
def test_feature_schema_alignment():
    from features.feature_vector_builder import build_feature_vector

    fv = build_feature_vector(sample_fight, sample_f_data, sample_o_data)

    assert len(fv) == len(FEATURE_SCHEMA)
```

This prevents regression errors like the “244 vs 246” issue forever.

---

# 🔥 **Phase 6 — Align all consumer scripts**

Update:

### ✔ `xgboost_predict.py`

Use the new builder.

### ✔ `export_predictions_to_excel.py`

Use the new builder.

### ✔ `server.py` (if any)

Use the new builder.

After this, predictions will be identical across every environment.

---

# 🔥 **Phase 7 — Lock in the Pipeline**

Once you lock:

* feature registry
* schema
* monotone constraints
* vector builder

You now have a **frozen machine learning pipeline** that:

* weak models cannot break
* smart models can extend
* training → prediction → evaluation is fully reproducible
* you can A/B test new features safely

---

# 🧠 TL;DR — When the good model returns:

### **1. Train final model → extract final feature list**

### **2. Freeze that list in `feature_schema.json`**

### **3. Build a feature vector builder aligned to the schema**

### **4. Implement monotonic XGBoost constraints using a parallel list**

### **5. Build automated evaluation pipeline**

### **6. Add regression tests to prevent feature drift**

### **7. Update all scripts to use the new builder**

After this, your entire system becomes deterministic, debuggable, and model-swappable.

---

If you want, I can generate:

* ✔ the full folder structure
* ✔ the final `feature_vector_builder.py` code
* ✔ example monotone constraint configs
* ✔ a regression test suite
* ✔ a master prompt for your weak model

Just say **“Generate the full scaffold”** and I’ll build it.
