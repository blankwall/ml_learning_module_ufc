#!/usr/bin/env python3
"""
Compare predictions between two models

Usage:
    python scripts/compare_models.py \
        --fighter-1 "Jalin Turner" \
        --fighter-2 "Edson Barboza" \
        --model-a xgboost_model \
        --model-b xgboost_model_with_2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pandas as pd
from loguru import logger

from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.matchup_features import MatchupFeatureExtractor
from features.feature_pipeline import FeaturePipeline
from models.xgboost_model import XGBoostModel


def resolve_fighter(session, name: str) -> Fighter:
    """Simple name lookup with ILIKE match."""
    fighter = (
        session.query(Fighter)
        .filter(Fighter.name.ilike(f"%{name}%"))
        .first()
    )
    if not fighter:
        raise ValueError(f"Fighter not found in DB: {name}")
    return fighter


def predict_with_model(
    model_name: str,
    fighter_1_id: int,
    fighter_2_id: int,
    fighter_1_name: str,
    fighter_2_name: str,
    session,
    matchup_extractor
) -> dict:
    """Get prediction from a specific model."""
    
    # Load model
    xgb_model = XGBoostModel()
    try:
        xgb_model.load_model(model_name)
    except FileNotFoundError:
        logger.error(f"Model not found: {model_name}")
        logger.info("Available models in models/saved/:")
        saved_dir = Path("models/saved")
        if saved_dir.exists():
            for f in saved_dir.glob("*.json"):
                if not f.name.endswith("_features.json"):
                    logger.info(f"  - {f.stem}")
        raise
    
    # Load the *matching* feature pipeline for this model.
    # Each model can have a different feature list + scaler.
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline(model_name=model_name)

    # Extract features
    features = matchup_extractor.extract_matchup_features(fighter_1_id, fighter_2_id)
    features["is_title_fight"] = 0
    
    # Prepare and predict
    X_df = pd.DataFrame([features])
    X_scaled, _ = pipeline.prepare_features(X_df, fit_scaler=False)
    
    proba = xgb_model.predict(X_scaled, use_calibrated=False)
    p_f1 = float(proba[0])
    p_f2 = 1.0 - p_f1
    
    return {
        "model_name": model_name,
        "fighter_1": fighter_1_name,
        "fighter_2": fighter_2_name,
        "prob_f1": p_f1,
        "prob_f2": p_f2,
        "predicted_winner": fighter_1_name if p_f1 > 0.5 else fighter_2_name,
        "confidence": abs(p_f1 - 0.5) * 2  # 0 to 1 scale
    }


def main():
    parser = argparse.ArgumentParser(description="Compare predictions between two models")
    parser.add_argument("--fighter-1", required=True, help="First fighter name")
    parser.add_argument("--fighter-2", required=True, help="Second fighter name")
    parser.add_argument(
        "--model-a",
        default="xgboost_model",
        help="First model name (default: xgboost_model)"
    )
    parser.add_argument(
        "--model-b",
        default="xgboost_model_with_2025",
        help="Second model name (default: xgboost_model_with_2025)"
    )
    
    args = parser.parse_args()
    
    # Initialize
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        # Resolve fighters
        f1 = resolve_fighter(session, args.fighter_1)
        f2 = resolve_fighter(session, args.fighter_2)
        
        logger.info(f"Matched: {f1.name} vs {f2.name}")

        # Create matchup extractor
        matchup_extractor = MatchupFeatureExtractor(session)
        
        # Get predictions from both models
        pred_a = predict_with_model(
            args.model_a, f1.id, f2.id, f1.name, f2.name,
            session, matchup_extractor
        )
        
        pred_b = predict_with_model(
            args.model_b, f1.id, f2.id, f1.name, f2.name,
            session, matchup_extractor
        )
        
        # Print comparison
        print("\n" + "=" * 80)
        print(f"MODEL COMPARISON: {f1.name} vs {f2.name}")
        print("=" * 80)
        
        print(f"\n{args.model_a.upper()}:")
        print(f"  {f1.name}: {pred_a['prob_f1']:.1%}")
        print(f"  {f2.name}: {pred_a['prob_f2']:.1%}")
        print(f"  Predicted Winner: {pred_a['predicted_winner']}")
        print(f"  Confidence: {pred_a['confidence']:.1%}")
        
        print(f"\n{args.model_b.upper()}:")
        print(f"  {f1.name}: {pred_b['prob_f1']:.1%}")
        print(f"  {f2.name}: {pred_b['prob_f2']:.1%}")
        print(f"  Predicted Winner: {pred_b['predicted_winner']}")
        print(f"  Confidence: {pred_b['confidence']:.1%}")
        
        # Show differences
        diff_f1 = pred_b['prob_f1'] - pred_a['prob_f1']
        diff_f2 = pred_b['prob_f2'] - pred_a['prob_f2']
        
        print(f"\nDIFFERENCE ({args.model_b} - {args.model_a}):")
        print(f"  {f1.name}: {diff_f1:+.1%}")
        print(f"  {f2.name}: {diff_f2:+.1%}")
        
        if pred_a['predicted_winner'] != pred_b['predicted_winner']:
            print(f"\n⚠️  MODELS DISAGREE!")
            print(f"    {args.model_a} picks: {pred_a['predicted_winner']}")
            print(f"    {args.model_b} picks: {pred_b['predicted_winner']}")
        else:
            print(f"\n✓ Both models agree: {pred_a['predicted_winner']} wins")
        
        print("=" * 80 + "\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

