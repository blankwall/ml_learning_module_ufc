#!/usr/bin/env python3
"""
Test Known Fighters
Validate features against fighters with known characteristics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from features.matchup_features import MatchupFeatureExtractor
from loguru import logger

def test_known_fighters():
    """Test features with fighters who have known characteristics"""
    db = DatabaseManager()
    session = db.get_session()
    
    extractor = MatchupFeatureExtractor(session)
    
    # Test cases: fighters with known characteristics
    test_cases = [
        {
            "name": "Elite fighter who lost to elite opponent",
            "fighter": "Sean Strickland",
            "expected": {
                "opponent_quality_score": "> 0.4",  # Should be positive despite losses
                "avg_lost_to_opponent_win_rate": "> 0.7",  # Lost to elite fighters
            }
        },
        {
            "name": "Undefeated fighter",
            "fighter": None,  # Will need to find one
            "expected": {
                "win_rate_last_3": "= 1.0",
                "current_loss_streak": "= 0",
            }
        },
    ]
    
    print("\n" + "="*80)
    print("KNOWN FIGHTER VALIDATION")
    print("="*80)
    
    from database.schema import Fighter
    
    # Test Strickland
    strickland = session.query(Fighter).filter(Fighter.name.ilike('%Sean Strickland%')).first()
    if strickland:
        print(f"\nTesting: {strickland.name}")
        print(f"  Record: {strickland.wins}-{strickland.losses}-{strickland.draws}")
        
        # Get features
        from features.fighter_features import FighterFeatureExtractor
        fighter_extractor = FighterFeatureExtractor(session)
        features = fighter_extractor.extract_features(strickland.id)
        
        print(f"\n  Opponent Quality Features:")
        print(f"    opponent_quality_score: {features.get('opponent_quality_score', 'N/A')}")
        print(f"    avg_lost_to_opponent_win_rate: {features.get('avg_lost_to_opponent_win_rate', 'N/A')}")
        print(f"    avg_beaten_opponent_win_rate: {features.get('avg_beaten_opponent_win_rate', 'N/A')}")
        
        # Validate expectations
        opp_quality = features.get('opponent_quality_score', 0)
        lost_wr = features.get('avg_lost_to_opponent_win_rate', 0)
        
        if opp_quality > 0.4:
            print(f"    ✅ opponent_quality_score is positive ({opp_quality:.3f})")
        else:
            print(f"    ⚠️  opponent_quality_score might be too low ({opp_quality:.3f})")
        
        if lost_wr > 0.7:
            print(f"    ✅ Lost to elite opponents ({lost_wr:.3f} win rate)")
        else:
            print(f"    ⚠️  Lost to opponents with {lost_wr:.3f} win rate (expected > 0.7)")
    
    session.close()

if __name__ == "__main__":
    test_known_fighters()

