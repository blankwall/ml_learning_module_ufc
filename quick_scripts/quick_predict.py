#!/usr/bin/env python3
"""
Quick Predict - Fast predictions using best single model

Much faster than full ensemble for quick predictions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from autogluon.tabular import TabularPredictor
from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.matchup_features import MatchupFeatureExtractor
from features.feature_pipeline import FeaturePipeline
import pandas as pd
from loguru import logger
import argparse


def _select_ensemble_best_model(predictor: TabularPredictor):
    """
    Select the top model from the AutoGluon leaderboard (typically a weighted ensemble).
    
    This restores the original \"best\" behavior for maximum predictive quality.
    """
    leaderboard = predictor.leaderboard(silent=True)
    best_model = leaderboard.iloc[0]['model']
    return best_model, leaderboard


def quick_predict(fighter_1_name: str, fighter_2_name: str, title_fight: bool = False):
    """Make a prediction using the best (typically ensemble) AutoGluon model"""
    
    # Load model
    predictor = TabularPredictor.load('models/saved/autogluon')
    
    # Use the top leaderboard model (often a weighted ensemble) for best quality
    best_model, leaderboard = _select_ensemble_best_model(predictor)
    logger.info(f"Using ensemble/best model for prediction: {best_model}")
    
    # Load feature pipeline (skip DB initialization for faster inference)
    # NOTE: AutoGluon models are trained on a specific feature set + scaler; if you retrain
    # XGBoost and overwrite the legacy pipeline artifacts, this can drift. Consider saving
    # per-model pipeline artifacts for AutoGluon as well if you hit mismatches.
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline()
    
    # Find fighters
    db = DatabaseManager()
    session = db.get_session()
    
    fighter_1 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_1_name}%')).first()
    fighter_2 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_2_name}%')).first()
    
    if not fighter_1:
        logger.error(f"Fighter not found: {fighter_1_name}")
        return
    if not fighter_2:
        logger.error(f"Fighter not found: {fighter_2_name}")
        return
    
    logger.info(f"Matched: {fighter_1.name} vs {fighter_2.name}")
    
    # Extract features
    extractor = MatchupFeatureExtractor(session)
    features = extractor.extract_matchup_features(fighter_1.id, fighter_2.id)
    features['is_title_fight'] = 1 if title_fight else 0
    
    # Prepare
    X_df = pd.DataFrame([features])
    X_scaled, _ = pipeline.prepare_features(X_df, fit_scaler=False)
    
    # Predict using best model only (much faster!)
    proba_df = predictor.predict_proba(X_scaled, model=best_model)
    
    # AutoGluon returns a DataFrame with one row and columns equal to class labels.
    # For our binary setup with labels {0, 1}, grab that single row robustly.
    if isinstance(proba_df, pd.DataFrame):
        proba_row = proba_df.iloc[0]
    else:
        # Fallback: convert to Series for consistent handling
        proba_row = pd.Series(proba_df[0] if getattr(proba_df, "ndim", 1) == 2 else proba_df)
    
    # Extract win probabilities for fighter_1 (label 1) and fighter_2 (label 0)
    if 1 in proba_row.index and 0 in proba_row.index:
        p_f2 = float(proba_row.loc[0])
        p_f1 = float(proba_row.loc[1])
    elif 1 in proba_row.index:
        p_f1 = float(proba_row.loc[1])
        p_f2 = 1.0 - p_f1
    else:
        # As a last resort, treat the max probability as fighter_1
        p_f1 = float(proba_row.max())
        p_f2 = 1.0 - p_f1
    
    prediction = 1 if p_f1 > 0.5 else 0
    
    # Display
    fight_type = "TITLE FIGHT (5 rounds)" if title_fight else "Non-title (3 rounds)"
    print("\n" + "="*60)
    print(f"PREDICTION: {fighter_1.name} vs {fighter_2.name}")
    print(f"Fight Type: {fight_type}")
    print("="*60)
    print(f"{fighter_1.name}: {p_f1*100:.1f}% chance to win")
    print(f"{fighter_2.name}: {p_f2*100:.1f}% chance to win")
    print("")
    if prediction == 1:
        print(f"⭐ Predicted Winner: {fighter_1.name}")
    else:
        print(f"⭐ Predicted Winner: {fighter_2.name}")
    print("="*60)
    
    session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Quick UFC Fight Prediction')
    parser.add_argument('--fighter-1', type=str, required=True, help='First fighter name')
    parser.add_argument('--fighter-2', type=str, required=True, help='Second fighter name')
    parser.add_argument('--title-fight', action='store_true', help='Is this a title fight?')
    
    args = parser.parse_args()
    
    quick_predict(args.fighter_1, args.fighter_2, args.title_fight)

