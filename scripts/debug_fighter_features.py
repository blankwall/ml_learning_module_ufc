#!/usr/bin/env python3
"""
Debug script to inspect individual fighter features
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from features.fighter_features import FighterFeatureExtractor
from loguru import logger

def debug_fighter_features(fighter_name: str):
    db = DatabaseManager()
    session = db.get_session()
    
    from database.schema import Fighter
    fighter = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_name}%')).first()
    
    if not fighter:
        logger.error(f"Fighter not found: {fighter_name}")
        return
    
    extractor = FighterFeatureExtractor(session)
    features = extractor.extract_features(fighter.id)
    
    print(f"\n{'='*80}")
    print(f"FEATURES FOR: {fighter.name}")
    print(f"{'='*80}\n")
    
    print("Time-Decayed Features:")
    print(f"  time_decayed_win_rate: {features.get('time_decayed_win_rate', 'N/A')}")
    print(f"  time_decayed_win_rate_adj_opp_quality: {features.get('time_decayed_win_rate_adj_opp_quality', 'N/A')}")
    
    print("\nOpponent Quality:")
    print(f"  avg_opponent_win_rate: {features.get('avg_opponent_win_rate', 'N/A')}")
    print(f"  avg_beaten_opponent_win_rate: {features.get('avg_beaten_opponent_win_rate', 'N/A')}")
    print(f"  avg_lost_to_opponent_win_rate: {features.get('avg_lost_to_opponent_win_rate', 'N/A')}")
    print(f"  opponent_quality_score: {features.get('opponent_quality_score', 'N/A')}")
    
    print("\nRecent Form:")
    print(f"  win_rate_last_3: {features.get('win_rate_last_3', 'N/A')}")
    print(f"  win_rate_last_5: {features.get('win_rate_last_5', 'N/A')}")
    print(f"  recent_form_score: {features.get('recent_form_score', 'N/A')}")
    
    print("\nActivity:")
    print(f"  days_since_last_fight: {features.get('days_since_last_fight', 'N/A')}")
    print(f"  activity_rate: {features.get('activity_rate', 'N/A')}")
    
    session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_fighter_features.py <fighter_name>")
        sys.exit(1)
    
    debug_fighter_features(sys.argv[1])

