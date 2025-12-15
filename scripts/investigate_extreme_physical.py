#!/usr/bin/env python3
"""
Investigate Extreme Physical Differences
Finds and analyzes fights with extreme height/reach differences to identify data quality issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from database.db_manager import DatabaseManager
from features.matchup_features import MatchupFeatureExtractor
from database.schema import Fighter, Fight

def investigate_extreme_physical():
    """Find and analyze fights with extreme physical differences"""
    db = DatabaseManager()
    session = db.get_session()
    
    logger.info("Extracting features for fights...")
    extractor = MatchupFeatureExtractor(session)
    
    # Get all completed fights
    fights = session.query(Fight).filter(Fight.result != None).all()
    
    print("\n" + "="*80)
    print("EXTREME PHYSICAL DIFFERENCES INVESTIGATION")
    print("="*80)
    
    extreme_cases = []
    
    for fight in fights:
        try:
            features = extractor.extract_matchup_features(
                fight.fighter_1_id,
                fight.fighter_2_id
            )
            
            height_diff = features.get('height_advantage', 0)
            reach_diff = features.get('reach_advantage', 0)
            
            # Flag extreme differences
            if abs(height_diff) > 50:  # More than 50cm difference
                extreme_cases.append({
                    'fight_id': fight.id,
                    'fighter_1_id': fight.fighter_1_id,
                    'fighter_2_id': fight.fighter_2_id,
                    'fighter_1_name': fight.fighter_1.name if fight.fighter_1 else 'Unknown',
                    'fighter_2_name': fight.fighter_2.name if fight.fighter_2 else 'Unknown',
                    'height_diff': height_diff,
                    'reach_diff': reach_diff,
                    'f1_height': features.get('f1_height_cm', 'N/A'),
                    'f2_height': features.get('f2_height_cm', 'N/A'),
                    'f1_reach': features.get('f1_reach_inches', 'N/A'),
                    'f2_reach': features.get('f2_reach_inches', 'N/A'),
                })
            elif abs(reach_diff) > 20:  # More than 20 inch difference
                extreme_cases.append({
                    'fight_id': fight.id,
                    'fighter_1_id': fight.fighter_1_id,
                    'fighter_2_id': fight.fighter_2_id,
                    'fighter_1_name': fight.fighter_1.name if fight.fighter_1 else 'Unknown',
                    'fighter_2_name': fight.fighter_2.name if fight.fighter_2 else 'Unknown',
                    'height_diff': height_diff,
                    'reach_diff': reach_diff,
                    'f1_height': features.get('f1_height_cm', 'N/A'),
                    'f2_height': features.get('f2_height_cm', 'N/A'),
                    'f1_reach': features.get('f1_reach_inches', 'N/A'),
                    'f2_reach': features.get('f2_reach_inches', 'N/A'),
                })
        except Exception as e:
            continue
    
    if not extreme_cases:
        print("\n✅ No extreme physical differences found!")
        session.close()
        return
    
    df = pd.DataFrame(extreme_cases)
    
    print(f"\n⚠️  Found {len(df)} fights with extreme physical differences")
    print("\n" + "-"*80)
    print("EXTREME HEIGHT DIFFERENCES (>50cm):")
    print("-"*80)
    
    height_extreme = df[df['height_diff'].abs() > 50].sort_values('height_diff', key=abs, ascending=False)
    if len(height_extreme) > 0:
        for idx, row in height_extreme.head(10).iterrows():
            print(f"\nFight ID: {row['fight_id']}")
            print(f"  {row['fighter_1_name']} vs {row['fighter_2_name']}")
            print(f"  Height Difference: {row['height_diff']:.1f} cm ({row['height_diff']/2.54:.1f} inches)")
            print(f"  F1 Height: {row['f1_height']} cm")
            print(f"  F2 Height: {row['f2_height']} cm")
            
            # Get actual fighter data from database
            f1 = session.query(Fighter).filter_by(id=row['fighter_1_id']).first()
            f2 = session.query(Fighter).filter_by(id=row['fighter_2_id']).first()
            if f1 and f2:
                print(f"  DB F1 Height: {f1.height_cm} cm")
                print(f"  DB F2 Height: {f2.height_cm} cm")
                if f1.height_cm and f2.height_cm:
                    db_diff = f1.height_cm - f2.height_cm
                    print(f"  DB Height Diff: {db_diff:.1f} cm")
                    if abs(db_diff - row['height_diff']) > 1:
                        print(f"  ⚠️  MISMATCH: Feature diff ({row['height_diff']:.1f}) != DB diff ({db_diff:.1f})")
    else:
        print("  None found")
    
    print("\n" + "-"*80)
    print("EXTREME REACH DIFFERENCES (>20 inches):")
    print("-"*80)
    
    reach_extreme = df[df['reach_diff'].abs() > 20].sort_values('reach_diff', key=abs, ascending=False)
    if len(reach_extreme) > 0:
        for idx, row in reach_extreme.head(10).iterrows():
            print(f"\nFight ID: {row['fight_id']}")
            print(f"  {row['fighter_1_name']} vs {row['fighter_2_name']}")
            print(f"  Reach Difference: {row['reach_diff']:.1f} inches")
            print(f"  F1 Reach: {row['f1_reach']} inches")
            print(f"  F2 Reach: {row['f2_reach']} inches")
            
            # Get actual fighter data from database
            f1 = session.query(Fighter).filter_by(id=row['fighter_1_id']).first()
            f2 = session.query(Fighter).filter_by(id=row['fighter_2_id']).first()
            if f1 and f2:
                print(f"  DB F1 Reach: {f1.reach_inches} inches")
                print(f"  DB F2 Reach: {f2.reach_inches} inches")
                if f1.reach_inches and f2.reach_inches:
                    db_diff = f1.reach_inches - f2.reach_inches
                    print(f"  DB Reach Diff: {db_diff:.1f} inches")
                    if abs(db_diff - row['reach_diff']) > 1:
                        print(f"  ⚠️  MISMATCH: Feature diff ({row['reach_diff']:.1f}) != DB diff ({db_diff:.1f})")
    else:
        print("  None found")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"\nHeight Differences:")
    print(f"  Min: {df['height_diff'].min():.1f} cm")
    print(f"  Max: {df['height_diff'].max():.1f} cm")
    print(f"  Mean: {df['height_diff'].mean():.1f} cm")
    print(f"  Std: {df['height_diff'].std():.1f} cm")
    
    print(f"\nReach Differences:")
    print(f"  Min: {df['reach_diff'].min():.1f} inches")
    print(f"  Max: {df['reach_diff'].max():.1f} inches")
    print(f"  Mean: {df['reach_diff'].mean():.1f} inches")
    print(f"  Std: {df['reach_diff'].std():.1f} inches")
    
    # Check for data quality issues
    print("\n" + "="*80)
    print("DATA QUALITY CHECKS")
    print("="*80)
    
    missing_data = 0
    null_heights = 0
    null_reaches = 0
    
    for idx, row in df.iterrows():
        f1 = session.query(Fighter).filter_by(id=row['fighter_1_id']).first()
        f2 = session.query(Fighter).filter_by(id=row['fighter_2_id']).first()
        
        if f1 and f2:
            if f1.height_cm is None or f2.height_cm is None:
                null_heights += 1
            if f1.reach_inches is None or f2.reach_inches is None:
                null_reaches += 1
        else:
            missing_data += 1
    
    print(f"\nMissing fighter data: {missing_data}")
    print(f"Null heights: {null_heights}")
    print(f"Null reaches: {null_reaches}")
    
    if null_heights > 0 or null_reaches > 0:
        print("\n⚠️  Some fighters have missing physical data - this could cause calculation issues")
    
    session.close()

if __name__ == "__main__":
    investigate_extreme_physical()

