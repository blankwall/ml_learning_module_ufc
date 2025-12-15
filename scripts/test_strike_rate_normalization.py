#!/usr/bin/env python3
"""
Test script to verify strike rate normalization is working correctly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from database.db_manager import DatabaseManager
from features.striking import extract_striking_features
from database.schema import Fighter

def test_strike_rate_normalization():
    """Test that strike rates sum to ~1.0"""
    db = DatabaseManager()
    session = db.get_session()
    
    # Get a few fighters with fight history
    fighters = session.query(Fighter).filter(
        Fighter.fights_as_fighter_1.any()
    ).limit(10).all()
    
    print("Testing strike rate normalization...")
    print("="*60)
    
    issues = []
    
    for fighter in fighters:
        features = extract_striking_features(fighter)
        
        if not features:
            continue
        
        # Check last_3 rates
        head_3 = features.get('head_strike_rate_last_3', 0)
        body_3 = features.get('body_strike_rate_last_3', 0)
        leg_3 = features.get('leg_strike_rate_last_3', 0)
        sum_3 = head_3 + body_3 + leg_3
        
        # Check lifetime rates
        head_life = features.get('head_strike_rate_lifetime', 0)
        body_life = features.get('body_strike_rate_lifetime', 0)
        leg_life = features.get('leg_strike_rate_lifetime', 0)
        sum_life = head_life + body_life + leg_life
        
        # Check position rates last_3
        dist_3 = features.get('distance_strike_rate_last_3', 0)
        clinch_3 = features.get('clinch_strike_rate_last_3', 0)
        ground_3 = features.get('ground_strike_rate_last_3', 0)
        pos_sum_3 = dist_3 + clinch_3 + ground_3
        
        # Check position rates lifetime
        dist_life = features.get('distance_strike_rate_lifetime', 0)
        clinch_life = features.get('clinch_strike_rate_lifetime', 0)
        ground_life = features.get('ground_strike_rate_lifetime', 0)
        pos_sum_life = dist_life + clinch_life + ground_life
        
        # Report issues
        if sum_3 > 0.1 and (sum_3 > 1.1 or sum_3 < 0.9):
            issues.append(f"{fighter.name}: Target area last_3 sum = {sum_3:.3f}")
        
        if sum_life > 0.1 and (sum_life > 1.1 or sum_life < 0.9):
            issues.append(f"{fighter.name}: Target area lifetime sum = {sum_life:.3f}")
        
        if pos_sum_3 > 0.1 and (pos_sum_3 > 1.1 or pos_sum_3 < 0.9):
            issues.append(f"{fighter.name}: Position last_3 sum = {pos_sum_3:.3f}")
        
        if pos_sum_life > 0.1 and (pos_sum_life > 1.1 or pos_sum_life < 0.9):
            issues.append(f"{fighter.name}: Position lifetime sum = {pos_sum_life:.3f}")
    
    session.close()
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} normalization issues:")
        for issue in issues[:20]:
            print(f"  • {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("\n✅ All strike rates normalized correctly!")
    
    print("="*60)
    return len(issues) == 0

if __name__ == "__main__":
    success = test_strike_rate_normalization()
    sys.exit(0 if success else 1)

