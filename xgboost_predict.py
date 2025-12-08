#!/usr/bin/env python3
"""
XGBoost Quick Predict - Fast predictions using XGBoost model
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.matchup_features import MatchupFeatureExtractor
from features.feature_pipeline import FeaturePipeline
from models.xgboost_model import XGBoostModel
import pandas as pd
from loguru import logger
import argparse


def xgboost_predict(fighter_1_name: str, fighter_2_name: str, title_fight: bool = False):
    """Make a prediction using XGBoost model"""
    
    # Load model
    logger.info("Loading XGBoost model...")
    xgb_model = XGBoostModel()
    
    try:
        xgb_model.load_model('xgboost_model')
    except FileNotFoundError:
        logger.error("XGBoost model not found. Please train first:")
        logger.error("  python -m models.xgboost_model --train")
        return
    
    # Load feature pipeline
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline()
    
    # Find fighters
    db = DatabaseManager()
    session = db.get_session()
    
    fighter_1 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_1_name}%')).first()
    fighter_2 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_2_name}%')).first()
    
    if not fighter_1:
        logger.error(f"Fighter not found: {fighter_1_name}")
        session.close()
        return
    if not fighter_2:
        logger.error(f"Fighter not found: {fighter_2_name}")
        session.close()
        return
    
    logger.info(f"Matched: {fighter_1.name} vs {fighter_2.name}")
    
    # Extract features
    extractor = MatchupFeatureExtractor(session)
    features = extractor.extract_matchup_features(fighter_1.id, fighter_2.id)
    features['is_title_fight'] = 1 if title_fight else 0
    

        # DEBUG: inspect some key features for this matchup
    debug_keys = [
        "f1_wins", "f1_losses", "f2_wins", "f2_losses",
        "f1_win_rate_last_3", "f2_win_rate_last_3",
        "f1_win_rate_last_5", "f2_win_rate_last_5",
        "f1_age", "f2_age",
        "round_3_win_rate_diff",
        "takedown_matchup",
        "striking_differential",
        "recent_form_diff",
        "f1_recent_finish_losses_last_2", "f2_recent_finish_losses_last_2",
        "f1_recent_finish_loss_last_fight", "f2_recent_finish_loss_last_fight",
        "f1_recent_finish_loss_ratio_last_2", "f2_recent_finish_loss_ratio_last_2",
        "f1_recent_sig_strike_diff_last_3", "f2_recent_sig_strike_diff_last_3",
        "f1_recent_knockdown_diff_last_3", "f2_recent_knockdown_diff_last_3",
    ]
    print("\n[DEBUG] Key features for this matchup:")
    for k in debug_keys:
        if k in features:
            print(f"  {k}: {features[k]}")
    print("")

    
    # Prepare features
    X_df = pd.DataFrame([features])
    X_scaled, _ = pipeline.prepare_features(X_df, fit_scaler=False)
    
    # Predict
    proba = xgb_model.predict(X_scaled, use_calibrated=False)
    p_f1 = float(proba[0])
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
    print("")
    
    # Show key factors
    importance_df = xgb_model.get_feature_importance(top_n=5)
    print("Top 5 Most Important Features in Model:")
    for idx, row in importance_df.iterrows():
        print(f"  {idx+1}. {row['feature']}")
    print("")
    
    session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XGBoost UFC Fight Prediction')
    parser.add_argument('--fighter-1', type=str, required=True, help='First fighter name')
    parser.add_argument('--fighter-2', type=str, required=True, help='Second fighter name')
    parser.add_argument('--title-fight', action='store_true', help='Is this a title fight?')
    
    args = parser.parse_args()
    
    xgboost_predict(args.fighter_1, args.fighter_2, args.title_fight)

