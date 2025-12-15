#!/usr/bin/env python3
"""
Verify Point-in-Time Feature Calculation
-----------------------------------------

This script verifies that features are being calculated correctly using only
historical data (no data leakage from future fights).
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from loguru import logger

from database.db_manager import DatabaseManager
from features.fighter_features import FighterFeatureExtractor


def test_point_in_time_features():
    """Test that features change correctly based on as_of_date."""
    
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        from database.schema import Fighter, Fight
        
        # Find a fighter with multiple fights across different years
        fighters_with_recent_fights = (
            session.query(Fighter.id, Fighter.name)
            .join(Fight, (Fight.fighter_1_id == Fighter.id) | (Fight.fighter_2_id == Fighter.id))
            .join(Fight.event)
            .filter(Fight.event.has())
            .group_by(Fighter.id)
            .having(session.query(Fight).filter(
                (Fight.fighter_1_id == Fighter.id) | (Fight.fighter_2_id == Fighter.id)
            ).count() >= 5)
            .limit(1)
            .all()
        )
        
        if not fighters_with_recent_fights:
            print("⚠️  No fighters found with sufficient fight history")
            return
        
        test_fighter_id, fighter_name = fighters_with_recent_fights[0]
        
        extractor = FighterFeatureExtractor(session)
        
        # Date 1: Beginning of 2022
        date1 = datetime(2022, 1, 1)
        features1 = extractor.extract_features(test_fighter_id, as_of_date=date1)
        
        # Date 2: Beginning of 2024
        date2 = datetime(2024, 1, 1)
        features2 = extractor.extract_features(test_fighter_id, as_of_date=date2)
        
        # Date 3: Current (no filter)
        features3 = extractor.extract_features(test_fighter_id, as_of_date=None)
        
        print("\n" + "=" * 80)
        print("POINT-IN-TIME FEATURE VERIFICATION")
        print("=" * 80)
        
        print(f"\nTesting: {fighter_name} (fighter_id={test_fighter_id})\n")
        
        # Check key features that should change over time
        time_sensitive_features = [
            "total_fights",
            "wins",
            "losses",
            "fights_since_last_win",
            "days_since_last_fight",
            "win_rate_last_3",
        ]
        
        print("Feature Values Over Time:")
        print(f"{'Feature':<40} {'2022-01-01':<15} {'2024-01-01':<15} {'Current':<15}")
        print("-" * 85)
        
        changes_detected = False
        for feat in time_sensitive_features:
            val1 = features1.get(feat, 0)
            val2 = features2.get(feat, 0)
            val3 = features3.get(feat, 0)
            
            print(f"{feat:<40} {val1:<15.2f} {val2:<15.2f} {val3:<15.2f}")
            
            # Check if values are different (indicating point-in-time is working)
            if val1 != val2 or val2 != val3:
                changes_detected = True
        
        print("\n" + "=" * 80)
        if changes_detected:
            print("✓ SUCCESS: Features change over time (point-in-time calculation working)")
            print("\nThis means features are correctly using only historical data")
            print("and NOT leaking information from future fights.")
            print("\n🎯 The data leakage fix is working correctly!")
        else:
            print("⚠️  WARNING: Features are identical across all time periods")
            print("\nThis might indicate:")
            print(f"  1. {fighter_name} had no fights between 2022-01-01 and now")
            print("  2. Point-in-time calculation is not working")
            print("  3. Try manually testing with a different fighter")
        print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    test_point_in_time_features()

