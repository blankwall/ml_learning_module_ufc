import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    brier_score_loss,
)
from sklearn.model_selection import train_test_split

# Ensure project root is on sys.path so we can import `models` and `features`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.xgboost_model import XGBoostModel
from features.feature_pipeline import FeaturePipeline
def evaluate_slices(
    data_path: str,
    model_name: str = "xgboost_model",
    high_thr: float = 0.65,
    low_thr: float = 0.35,
):
    # Load pipeline (scaler + feature names) and dataset
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline()
    df = pipeline.load_dataset(data_path)

    # Prepare features using existing scaler (no refit)
    X, y = pipeline.prepare_features(df, fit_scaler=False)

    # Recreate the same train/test split used in training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Load model
    xgb_model = XGBoostModel()
    xgb_model.load_model(model_name)

    # Predictions on test set
    proba = xgb_model.predict(X_test, use_calibrated=False)
    y_pred = (proba > 0.5).astype(int)

    # Overall metrics (sanity check)
    overall_acc = accuracy_score(y_test, y_pred)
    overall_logloss = log_loss(y_test, proba)
    overall_brier = brier_score_loss(y_test, proba)

    print("=== Overall test metrics ===")
    print(f"Accuracy:   {overall_acc:.3f}")
    print(f"Log Loss:   {overall_logloss:.4f}")
    print(f"Brier:      {overall_brier:.4f}")
    print()

    # Favorites slice: model very confident in fighter 1
    fav_mask = proba >= high_thr
    if fav_mask.any():
        fav_acc = accuracy_score(y_test[fav_mask], y_pred[fav_mask])
        fav_logloss = log_loss(y_test[fav_mask], proba[fav_mask])
        fav_brier = brier_score_loss(y_test[fav_mask], proba[fav_mask])
        print(f"=== Favorites slice (p >= {high_thr:.2f}) ===")
        print(f"Count:      {fav_mask.sum()}")
        print(f"Accuracy:   {fav_acc:.3f}")
        print(f"Log Loss:   {fav_logloss:.4f}")
        print(f"Brier:      {fav_brier:.4f}")
        print()
    else:
        print(f"No test examples with p >= {high_thr:.2f}")
        print()

    # Underdogs slice: very low probability for fighter 1
    dog_mask = proba <= low_thr
    if dog_mask.any():
        dog_acc = accuracy_score(y_test[dog_mask], y_pred[dog_mask])
        dog_logloss = log_loss(y_test[dog_mask], proba[dog_mask])
        dog_brier = brier_score_loss(y_test[dog_mask], proba[dog_mask])
        print(f"=== Underdogs slice (p <= {low_thr:.2f}) ===")
        print(f"Count:      {dog_mask.sum()}")
        print(f"Accuracy:   {dog_acc:.3f}")
        print(f"Log Loss:   {dog_logloss:.4f}")
        print(f"Brier:      {dog_brier:.4f}")
        print()
    else:
        print(f"No test examples with p <= {low_thr:.2f}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate model on probability slices")
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/processed/training_data.csv",
        help="Path to training dataset CSV",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="xgboost_model",
        help="Base name of saved model (without extension)",
    )
    parser.add_argument(
        "--high-thr",
        type=float,
        default=0.65,
        help="Threshold for favorites slice (p >= high_thr)",
    )
    parser.add_argument(
        "--low-thr",
        type=float,
        default=0.35,
        help="Threshold for underdogs slice (p <= low_thr)",
    )

    args = parser.parse_args()
    evaluate_slices(
        data_path=args.data_path,
        model_name=args.model_name,
        high_thr=args.high_thr,
        low_thr=args.low_thr,
    )


if __name__ == "__main__":
    main()