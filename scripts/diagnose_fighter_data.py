#!/usr/bin/env python3
"""
Diagnostic script to check fighter data quality and feature calculations.
Shows fight history, date ordering, and key feature values.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime
from database.db_manager import DatabaseManager
from features.registry import FeatureBuilder
from loguru import logger
import argparse


def diagnose_fighter(session, feature_builder, fighter_name: str):
    """Diagnose a single fighter's data quality."""
    from database.schema import Fighter
    
    fighter = session.query(Fighter).filter(Fighter.name.ilike(f'%{fighter_name}%')).first()
    if not fighter:
        logger.error(f"Fighter not found: {fighter_name}")
        return
    
    print(f"\n{'='*80}")
    print(f"FIGHTER: {fighter.name} (ID: {fighter.id})")
    print(f"{'='*80}")
    print(f"Record: {fighter.wins}-{fighter.losses}-{fighter.draws}")
    print(f"Striking: {fighter.sig_strikes_landed_per_min:.2f} landed/min, "
          f"{fighter.sig_strikes_absorbed_per_min:.2f} absorbed/min")
    
    # Get fight history (as used by model)
    fight_history = feature_builder.get_fight_history(fighter.id)
    
    print(f"\nFight History (Total: {len(fight_history)} fights)")
    print("-" * 80)
    
    if len(fight_history) == 0:
        print("  No fights found in database")
        return
    
    # Check date parsing
    if 'event_date_parsed' in fight_history.columns:
        dates = fight_history['event_date_parsed'].dropna()
        if len(dates) > 1:
            is_sorted = (dates.diff() <= pd.Timedelta(0)).all()
            print(f"  Date sorting: {'✓ Correctly sorted (descending)' if is_sorted else '✗ NOT sorted correctly'}")
    
    print("\n  Last 10 fights (most recent first):")
    for idx, row in fight_history.head(10).iterrows():
        date_parsed = row.get('event_date_parsed', None)
        date_str = row.get('event_date', 'Unknown')
        result = row.get('result', 'Unknown')
        method = row.get('method', '')
        
        date_display = date_parsed.strftime('%Y-%m-%d') if date_parsed else date_str
        result_symbol = '✓' if result == 'win' else '✗' if result == 'loss' else '='
        print(f"    {result_symbol} {date_display}: {result.upper()} {method}")
    
    # Calculate win rates
    last_3 = fight_history.head(3)
    last_5 = fight_history.head(5)
    last_10 = fight_history.head(10)
    
    win_rate_3 = (last_3['result'] == 'win').sum() / len(last_3) if len(last_3) > 0 else 0
    win_rate_5 = (last_5['result'] == 'win').sum() / len(last_5) if len(last_5) > 0 else 0
    win_rate_10 = (last_10['result'] == 'win').sum() / len(last_10) if len(last_10) > 0 else 0
    
    print(f"\n  Win Rates:")
    print(f"    Last 3:  {win_rate_3:.1%} ({last_3['result'].eq('win').sum()}/{len(last_3)})")
    print(f"    Last 5:  {win_rate_5:.1%} ({last_5['result'].eq('win').sum()}/{len(last_5)})")
    print(f"    Last 10: {win_rate_10:.1%} ({last_10['result'].eq('win').sum()}/{len(last_10)})")
    
    # Check for date issues
    if 'event_date_parsed' in fight_history.columns:
        dates = fight_history['event_date_parsed'].dropna()
        if len(dates) > 0:
            most_recent = dates.max()
            oldest = dates.min()
            now = datetime.now()
            days_since_last = (now - most_recent).days if most_recent else None
            
            print(f"\n  Date Range:")
            print(f"    Most recent: {most_recent.strftime('%Y-%m-%d') if most_recent else 'Unknown'}")
            print(f"    Oldest: {oldest.strftime('%Y-%m-%d') if oldest else 'Unknown'}")
            if days_since_last is not None:
                print(f"    Days since last fight: {days_since_last}")
                if days_since_last < 0:
                    print(f"    ⚠️  WARNING: Most recent fight is in the future!")


def main():
    parser = argparse.ArgumentParser(description='Diagnose fighter data quality')
    parser.add_argument('fighters', nargs='+', help='Fighter names to diagnose')
    
    args = parser.parse_args()
    
    db = DatabaseManager()
    session = db.get_session()
    feature_builder = FeatureBuilder(session)
    
    try:
        for fighter_name in args.fighters:
            diagnose_fighter(session, feature_builder, fighter_name)
    finally:
        session.close()
    
    print(f"\n{'='*80}")
    print("Diagnosis complete")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

