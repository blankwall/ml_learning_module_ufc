#!/usr/bin/env python3
"""
Feature Distribution Validator
Checks feature distributions for outliers, anomalies, and data quality issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from database.db_manager import DatabaseManager
from features.matchup_features import MatchupFeatureExtractor
from features.registry import FeatureRegistry

def validate_feature_distributions():
    """Check feature distributions for anomalies"""
    db = DatabaseManager()
    session = db.get_session()
    
    logger.info("Extracting features for sample fighters...")
    extractor = MatchupFeatureExtractor(session)
    
    # Get a sample of fights
    from database.schema import Fight
    fights = session.query(Fight).filter(Fight.result != None).limit(100).all()
    
    all_features = []
    for fight in fights:
        try:
            features = extractor.extract_matchup_features(
                fight.fighter_1_id, 
                fight.fighter_2_id
            )
            all_features.append(features)
        except Exception as e:
            logger.warning(f"Error extracting features for fight {fight.id}: {e}")
            continue
    
    if not all_features:
        logger.error("No features extracted")
        session.close()
        return
    
    df = pd.DataFrame(all_features)
    
    print("\n" + "="*80)
    print("FEATURE DISTRIBUTION VALIDATION")
    print("="*80)
    
    issues = []
    
    # Check for extreme outliers
    for col in df.select_dtypes(include=[np.number]).columns:
        values = df[col].dropna()
        if len(values) == 0:
            continue
        
        # Skip metadata columns
        if col in ['fight_id', 'event_id', 'fighter_1_id', 'fighter_2_id', 'target']:
            continue
        
        # Check for extreme values
        q99 = values.quantile(0.99)
        q1 = values.quantile(0.01)
        median = values.median()
        
        # Flag if 99th percentile is > 10x median (for positive values)
        if median > 0 and q99 > median * 10:
            issues.append(f"{col}: Extreme high values (99th percentile {q99:.2f} vs median {median:.2f})")
        
        # Check for negative values where they shouldn't exist
        if values.min() < -0.1 and col not in ['diff', 'decline', 'vs_career', 'trend']:
            if 'diff' not in col.lower() and 'decline' not in col.lower():
                issues.append(f"{col}: Has negative values (min: {values.min():.3f})")
        
        # Check for infinite values
        if np.isinf(values).any():
            issues.append(f"{col}: Contains infinite values")
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} potential distribution issues:")
        for issue in issues[:30]:
            print(f"  • {issue}")
        if len(issues) > 30:
            print(f"  ... and {len(issues) - 30} more")
    else:
        print("\n✅ No distribution issues found!")
    
    # Show summary statistics for key features
    print("\n" + "="*80)
    print("KEY FEATURE STATISTICS")
    print("="*80)
    
    key_features = [
        'time_decayed_win_rate_diff',
        'opponent_quality_score_diff',
        'striking_output_diff',
        'f1_opponent_quality_score',
        'f2_opponent_quality_score',
        'f1_sig_strikes_landed_per_min_lifetime',
        'f2_sig_strikes_landed_per_min_lifetime',
    ]
    
    for feat in key_features:
        if feat in df.columns:
            values = df[feat].dropna()
            if len(values) > 0:
                print(f"\n{feat}:")
                print(f"  Mean: {values.mean():.4f}")
                print(f"  Median: {values.median():.4f}")
                print(f"  Std: {values.std():.4f}")
                print(f"  Min: {values.min():.4f}, Max: {values.max():.4f}")
                print(f"  5th percentile: {values.quantile(0.05):.4f}")
                print(f"  95th percentile: {values.quantile(0.95):.4f}")
    
    session.close()
    return len(issues) == 0

if __name__ == "__main__":
    success = validate_feature_distributions()
    sys.exit(0 if success else 1)

