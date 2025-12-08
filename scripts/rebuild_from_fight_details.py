#!/usr/bin/env python3
"""
Rebuild database using ONLY fight_details.json
This has the correct winner data, unlike events.json
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from loguru import logger
from database.db_manager import DatabaseManager
from database.schema import Fighter, Event, Fight, FightStats, Base
from sqlalchemy import create_engine

def rebuild_database():
    """Rebuild database from scratch using fight_details.json"""
    
    # Load data
    logger.info("Loading JSON files...")
    
    with open('data/processed/fighters.json') as f:
        fighters_data = json.load(f)
    
    with open('data/processed/events.json') as f:
        events_data = json.load(f)
    
    with open('data/processed/fight_details.json') as f:
        fight_details_data = json.load(f)
    
    # Create fight_details lookup
    fight_details_by_id = {d['fight_id']: d for d in fight_details_data}
    
    logger.info(f"Loaded {len(fighters_data)} fighters")
    logger.info(f"Loaded {len(events_data)} events")
    logger.info(f"Loaded {len(fight_details_data)} fight details")
    
    # Initialize database
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        # 1. Add all fighters
        logger.info("Adding fighters...")
        fighter_map = {}  # fighter_id -> Fighter object
        
        for i, fighter_data in enumerate(fighters_data, 1):
            if i % 500 == 0:
                logger.info(f"  Processed {i}/{len(fighters_data)} fighters")
                session.commit()
            
            fighter = db.add_fighter(session, fighter_data)
            fighter_map[fighter.fighter_id] = fighter
        
        session.commit()
        logger.success(f"Added {len(fighters_data)} fighters")
        
        # 2. Add events (without fights for now)
        logger.info("Adding events...")
        event_map = {}  # event_id -> Event object
        
        for i, event_data in enumerate(events_data, 1):
            if i % 50 == 0:
                logger.info(f"  Processed {i}/{len(events_data)} events")
                session.commit()
            
            event = db.add_event(session, event_data)
            event_map[event.event_id] = event
        
        session.commit()
        logger.success(f"Added {len(events_data)} events")
        
        # 3. Add fights using fight_details.json (has correct winners!)
        logger.info("Adding fights from fight_details.json...")
        
        added_fights = 0
        skipped_fights = 0
        
        for i, detail in enumerate(fight_details_data, 1):
            if i % 500 == 0:
                logger.info(f"  Processed {i}/{len(fight_details_data)} fights")
                session.commit()
            
            try:
                # Get event
                event_id = detail.get('event_id')
                event = event_map.get(event_id)
                
                if not event:
                    skipped_fights += 1
                    continue
                
                # Get fighters by their IDs in fight_details.json
                f1_id = detail.get('fighter_1_id')
                f2_id = detail.get('fighter_2_id')
                
                fighter_1 = fighter_map.get(f1_id)
                fighter_2 = fighter_map.get(f2_id)
                
                if not fighter_1 or not fighter_2:
                    skipped_fights += 1
                    continue
                
                # Determine winner from fight_details
                f1_result = detail.get('fighter_1_result', '')
                f2_result = detail.get('fighter_2_result', '')
                
                if f1_result == 'W':
                    result = 'fighter_1'
                    winner_id = fighter_1.id
                elif f2_result == 'W':
                    result = 'fighter_2'
                    winner_id = fighter_2.id
                elif f1_result == 'D' or f2_result == 'D':
                    result = 'draw'
                    winner_id = None
                elif f1_result == 'NC' or f2_result == 'NC':
                    result = 'no_contest'
                    winner_id = None
                else:
                    result = None
                    winner_id = None
                
                # Create fight
                fight = Fight(
                    fight_id=detail.get('fight_id'),
                    event_id=event.id,
                    fighter_1_id=fighter_1.id,
                    fighter_2_id=fighter_2.id,
                    weight_class=None,  # Not in fight_details.json
                    is_title_fight=False,  # Not in fight_details.json
                    result=result,
                    method=detail.get('method'),
                    method_detail=detail.get('method_details'),
                    round_finished=detail.get('round'),
                    time=detail.get('time'),
                    fight_detail_url=detail.get('url'),
                    winner_id=winner_id
                )
                
                session.add(fight)
                session.flush()
                
                # Add fight stats
                fight_stats = FightStats(
                    fight_id=fight.id,
                    fighter_1_totals=detail.get('totals', {}).get('fighter_1'),
                    fighter_2_totals=detail.get('totals', {}).get('fighter_2'),
                    significant_strikes=detail.get('significant_strikes')
                )
                session.add(fight_stats)
                
                added_fights += 1
                
            except Exception as e:
                logger.error(f"Error adding fight {detail.get('fight_id')}: {e}")
                skipped_fights += 1
                continue
        
        session.commit()
        logger.success(f"Added {added_fights} fights (skipped {skipped_fights})")
        
        # 4. Verify distribution
        logger.info("\nVerifying fight result distribution...")
        from sqlalchemy import func
        
        total = session.query(Fight).count()
        f1_wins = session.query(Fight).filter(Fight.result == 'fighter_1').count()
        f2_wins = session.query(Fight).filter(Fight.result == 'fighter_2').count()
        draws = session.query(Fight).filter(Fight.result == 'draw').count()
        
        logger.info(f"Total fights: {total}")
        logger.info(f"Fighter 1 wins: {f1_wins} ({f1_wins/total*100:.1f}%)")
        logger.info(f"Fighter 2 wins: {f2_wins} ({f2_wins/total*100:.1f}%)")
        logger.info(f"Draws: {draws} ({draws/total*100:.1f}%)")
        
        if f2_wins == 0:
            logger.error("❌ PROBLEM: No fighter_2 wins! Something is still wrong.")
        elif f1_wins > total * 0.7:
            logger.warning("⚠️  WARNING: Fighter 1 win rate seems high")
        else:
            logger.success("✅ Fight distribution looks correct!")
        
    finally:
        session.close()


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("REBUILDING DATABASE FROM FIGHT_DETAILS.JSON")
    logger.info("=" * 60)
    
    # Delete old database
    db_path = Path('data/ufc_database.db')
    if db_path.exists():
        logger.info("Deleting old database...")
        db_path.unlink()
    
    rebuild_database()
    
    logger.success("\n" + "=" * 60)
    logger.success("DATABASE REBUILD COMPLETE!")
    logger.success("=" * 60)

