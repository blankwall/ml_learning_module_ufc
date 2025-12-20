#!/usr/bin/env python3
"""
Compare predictions between xgboost_predict.py and export_predictions_to_excel.py
to identify why they differ.
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
from datetime import datetime


def compare_predictions(fighter_1_name: str, fighter_2_name: str, title_fight: bool = False, model_name: str = "xgboost_model"):
    """Compare predictions using both methods"""
    
    # Load model and pipeline
    logger.info("Loading XGBoost model and feature pipeline...")
    xgb_model = XGBoostModel()
    xgb_model.load_model(model_name)
    
    pipeline = FeaturePipeline(initialize_db=False)
    pipeline.load_pipeline(model_name=model_name)
    
    # Get database session
    db = DatabaseManager()
    session = db.get_session()
    
    # Method 1: xgboost_predict.py approach
    logger.info("\n" + "="*60)
    logger.info("METHOD 1: xgboost_predict.py approach")
    logger.info("="*60)
    
    fighter_1_method1 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_1_name}%')).first()
    fighter_2_method1 = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_2_name}%')).first()
    
    if not fighter_1_method1:
        logger.error(f"Fighter not found: {fighter_1_name}")
        session.close()
        return
    if not fighter_2_method1:
        logger.error(f"Fighter not found: {fighter_2_name}")
        session.close()
        return
    
    logger.info(f"Matched: {fighter_1_method1.name} (ID: {fighter_1_method1.id}) vs {fighter_2_method1.name} (ID: {fighter_2_method1.id})")
    
    extractor_method1 = MatchupFeatureExtractor(session)
    features_method1 = extractor_method1.extract_matchup_features(fighter_1_method1.id, fighter_2_method1.id)
    features_method1['is_title_fight'] = 1 if title_fight else 0
    
    X_df_method1 = pd.DataFrame([features_method1])
    X_scaled_method1, _ = pipeline.prepare_features(X_df_method1, fit_scaler=False)
    
    proba_method1 = xgb_model.predict(X_scaled_method1, use_calibrated=False)
    p_f1_method1 = float(proba_method1[0])
    p_f2_method1 = 1.0 - p_f1_method1
    
    logger.info(f"Prediction Method 1: {fighter_1_method1.name}: {p_f1_method1*100:.1f}%, {fighter_2_method1.name}: {p_f2_method1*100:.1f}%")
    
    # Method 2: export_predictions_to_excel.py approach
    logger.info("\n" + "="*60)
    logger.info("METHOD 2: export_predictions_to_excel.py approach")
    logger.info("="*60)
    
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
    
    f1_method2 = resolve_fighter(session, fighter_1_name)
    f2_method2 = resolve_fighter(session, fighter_2_name)
    
    logger.info(f"Matched: {f1_method2.name} (ID: {f1_method2.id}) vs {f2_method2.name} (ID: {f2_method2.id})")
    
    matchup_extractor_method2 = MatchupFeatureExtractor(session)
    features_method2 = matchup_extractor_method2.extract_matchup_features(f1_method2.id, f2_method2.id)
    features_method2["is_title_fight"] = 1 if title_fight else 0
    
    X_df_method2 = pd.DataFrame([features_method2])
    X_scaled_method2, _ = pipeline.prepare_features(X_df_method2, fit_scaler=False)
    
    proba_method2 = xgb_model.predict(X_scaled_method2, use_calibrated=False)
    p_f1_method2 = float(proba_method2[0])
    p_f2_method2 = 1.0 - p_f1_method2
    
    logger.info(f"Prediction Method 2: {f1_method2.name}: {p_f1_method2*100:.1f}%, {f2_method2.name}: {p_f2_method2*100:.1f}%")
    
    # Compare results
    logger.info("\n" + "="*60)
    logger.info("COMPARISON")
    logger.info("="*60)
    
    # Check if same fighters were matched
    if fighter_1_method1.id != f1_method2.id:
        logger.warning(f"⚠️  DIFFERENT FIGHTERS MATCHED FOR FIGHTER 1!")
        logger.warning(f"   Method 1: {fighter_1_method1.name} (ID: {fighter_1_method1.id})")
        logger.warning(f"   Method 2: {f1_method2.name} (ID: {f1_method2.id})")
    else:
        logger.info(f"✓ Same fighter matched for fighter 1: {fighter_1_method1.name} (ID: {fighter_1_method1.id})")
    
    if fighter_2_method1.id != f2_method2.id:
        logger.warning(f"⚠️  DIFFERENT FIGHTERS MATCHED FOR FIGHTER 2!")
        logger.warning(f"   Method 1: {fighter_2_method1.name} (ID: {fighter_2_method1.id})")
        logger.warning(f"   Method 2: {f2_method2.name} (ID: {f2_method2.id})")
    else:
        logger.info(f"✓ Same fighter matched for fighter 2: {fighter_2_method1.name} (ID: {fighter_2_method1.id})")
    
    # Compare predictions
    diff_f1 = abs(p_f1_method1 - p_f1_method2)
    diff_f2 = abs(p_f2_method1 - p_f2_method2)
    
    logger.info(f"\nPrediction Differences:")
    logger.info(f"  Fighter 1 probability difference: {diff_f1*100:.4f}%")
    logger.info(f"  Fighter 2 probability difference: {diff_f2*100:.4f}%")
    
    if diff_f1 > 0.001 or diff_f2 > 0.001:
        logger.warning(f"⚠️  PREDICTIONS DIFFER by more than 0.1%!")
    else:
        logger.info(f"✓ Predictions are essentially identical (difference < 0.1%)")
    
    # Compare feature dictionaries
    logger.info(f"\nFeature Comparison:")
    logger.info(f"  Method 1 feature count: {len(features_method1)}")
    logger.info(f"  Method 2 feature count: {len(features_method2)}")
    
    # Find differences in features
    keys1 = set(features_method1.keys())
    keys2 = set(features_method2.keys())
    
    only_in_method1 = keys1 - keys2
    only_in_method2 = keys2 - keys1
    
    if only_in_method1:
        logger.warning(f"⚠️  Features only in Method 1: {only_in_method1}")
    if only_in_method2:
        logger.warning(f"⚠️  Features only in Method 2: {only_in_method2}")
    
    # Compare feature values
    common_keys = keys1.intersection(keys2)
    different_values = []
    
    for key in sorted(common_keys):
        val1 = features_method1[key]
        val2 = features_method2[key]
        
        # Handle NaN comparisons
        import math
        if isinstance(val1, float) and isinstance(val2, float):
            if math.isnan(val1) and math.isnan(val2):
                continue
            if math.isnan(val1) or math.isnan(val2):
                different_values.append((key, val1, val2))
                continue
        
        if val1 != val2:
            # For floats, check if difference is significant
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if abs(val1 - val2) > 1e-10:
                    different_values.append((key, val1, val2))
            else:
                different_values.append((key, val1, val2))
    
    if different_values:
        logger.warning(f"\n⚠️  Found {len(different_values)} features with different values:")
        for key, val1, val2 in different_values[:20]:  # Show first 20
            logger.warning(f"   {key}: Method1={val1}, Method2={val2}")
        if len(different_values) > 20:
            logger.warning(f"   ... and {len(different_values) - 20} more")
    else:
        logger.info(f"✓ All feature values are identical")
    
    # Compare scaled features
    logger.info(f"\nScaled Feature Comparison:")
    logger.info(f"  Method 1 scaled shape: {X_scaled_method1.shape}")
    logger.info(f"  Method 2 scaled shape: {X_scaled_method2.shape}")
    
    if X_scaled_method1.shape == X_scaled_method2.shape:
        diff_scaled = (X_scaled_method1.values - X_scaled_method2.values)
        max_diff = abs(diff_scaled).max()
        logger.info(f"  Max difference in scaled features: {max_diff:.10f}")
        
        if max_diff > 1e-6:
            logger.warning(f"⚠️  Scaled features differ!")
            # Find which features differ most
            diff_abs = abs(diff_scaled[0])
            max_idx = diff_abs.argmax()
            feature_names = X_scaled_method1.columns.tolist()
            logger.warning(f"   Largest difference in feature: {feature_names[max_idx]} (diff: {diff_abs[max_idx]:.10f})")
        else:
            logger.info(f"✓ Scaled features are essentially identical")
    else:
        logger.warning(f"⚠️  Scaled feature shapes differ!")
    
    session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare predictions between two methods')
    parser.add_argument('--fighter-1', type=str, required=True, help='First fighter name')
    parser.add_argument('--fighter-2', type=str, required=True, help='Second fighter name')
    parser.add_argument('--title-fight', action='store_true', help='Is this a title fight?')
    parser.add_argument('--model-name', type=str, default='xgboost_model', help='XGBoost model name (default: xgboost_model)')
    
    args = parser.parse_args()
    
    compare_predictions(args.fighter_1, args.fighter_2, args.title_fight, model_name=args.model_name)

