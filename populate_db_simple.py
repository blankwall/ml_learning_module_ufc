#!/usr/bin/env python3
"""
Simple database populator using fight_details.json as the source of truth

This avoids all the complexity of events.json where winners are always listed first.
"""

import json
from loguru import logger
from database.db_manager import DatabaseManager
from database.schema import Fighter, Event, Fight, FightStats
from datetime import datetime

def main():
    logger.info("=" * 80)
    logger.info("SIMPLE DATABASE POPULATOR - Using fight_details.json as source")
    logger.info("=" * 80)
    
    db = DatabaseManager("config/config.yaml")
    
    # Reset database
    logger.warning("\nResetting database...")
    db.reset_database()
    
    session = db.get_session()
    
    try:
        # Load fighters
        logger.info("\nStep 1: Loading fighters...")
        with open('data/processed/fighters.json', 'r') as f:
            fighters_data = json.load(f)
        
        for i, fighter_data in enumerate(fighters_data, 1):
            db.add_fighter(session, fighter_data)
            if i % 100 == 0:
                session.commit()
                logger.info(f"  Processed {i}/{len(fighters_data)} fighters")
        
        session.commit()
        logger.success(f"Loaded {len(fighters_data)} fighters")
        
        # Load events (for dates/locations)
        logger.info("\nStep 2: Loading events...")
        with open('data/processed/events.json', 'r') as f:
            events_data = json.load(f)
        
        event_lookup = {}  # event_id -> {date, location}
        for event_data in events_data:
            event = db.add_event(session, event_data)
            session.flush()
            event_lookup[event.event_id] = {
                'db_event': event,
                'fights_data': {}  # fight_detail_id -> weight_class, is_title_fight
            }
            # Store weight class and title fight info for each fight
            for fight in event_data.get('fights', []):
                fid = fight.get('fight_detail_id')
                if fid:
                    event_lookup[event.event_id]['fights_data'][fid] = {
                        'weight_class': fight.get('weight_class'),
                        'is_title_fight': fight.get('is_title_fight', False),
                        'fight_number': fight.get('fight_number')
                    }
        
        session.commit()
        logger.success(f"Loaded {len(events_data)} events")
        
        # Load fights from fight_details (SOURCE OF TRUTH)
        logger.info("\nStep 3: Loading fights from fight_details.json...")
        with open('data/processed/fight_details.json', 'r') as f:
            fight_details = json.load(f)
        
        stats = {
            'total': 0,
            'fighter_1_wins': 0,
            'fighter_2_wins': 0,
            'draws': 0,
            'no_contests': 0,
            'missing_fighters': 0,
            'missing_events': 0
        }
        
        for i, detail in enumerate(fight_details, 1):
            try:
                fight_id = detail.get('fight_id')
                event_id = detail.get('event_id')
                
                if not fight_id or not event_id:
                    continue
                
                # Get fighters by ID
                fighter_1_id = detail.get('fighter_1_id')
                fighter_2_id = detail.get('fighter_2_id')
                
                if not fighter_1_id or not fighter_2_id:
                    continue
                
                fighter_1 = session.query(Fighter).filter_by(fighter_id=fighter_1_id).first()
                fighter_2 = session.query(Fighter).filter_by(fighter_id=fighter_2_id).first()
                
                if not fighter_1 or not fighter_2:
                    stats['missing_fighters'] += 1
                    # Create minimal fighter records
                    if not fighter_1:
                        fighter_1 = Fighter(
                            fighter_id=fighter_1_id,
                            name=detail.get('fighter_1_name', 'Unknown')
                        )
                        session.add(fighter_1)
                    if not fighter_2:
                        fighter_2 = Fighter(
                            fighter_id=fighter_2_id,
                            name=detail.get('fighter_2_name', 'Unknown')
                        )
                        session.add(fighter_2)
                    session.flush()
                
                # Get event
                event_info = event_lookup.get(event_id)
                if not event_info:
                    stats['missing_events'] += 1
                    continue
                
                event = event_info['db_event']
                fight_info = event_info['fights_data'].get(fight_id, {})
                
                # Determine winner based on fighter_X_result
                result = None
                winner_id = None
                
                f1_result = detail.get('fighter_1_result')
                f2_result = detail.get('fighter_2_result')
                
                if f1_result == 'W':
                    result = 'fighter_1'
                    winner_id = fighter_1.id
                    stats['fighter_1_wins'] += 1
                elif f2_result == 'W':
                    result = 'fighter_2'
                    winner_id = fighter_2.id
                    stats['fighter_2_wins'] += 1
                elif detail.get('winner') == 'draw':
                    result = 'draw'
                    stats['draws'] += 1
                elif detail.get('winner') in ['no_contest', 'no contest']:
                    result = 'no_contest'
                    stats['no_contests'] += 1
                
                # Create fight
                fight = Fight(
                    fight_id=fight_id,
                    event_id=event.id,
                    fighter_1_id=fighter_1.id,
                    fighter_2_id=fighter_2.id,
                    fight_number=fight_info.get('fight_number'),
                    weight_class=fight_info.get('weight_class'),
                    is_title_fight=fight_info.get('is_title_fight', False),
                    result=result,
                    winner_id=winner_id,
                    method=detail.get('method'),
                    method_detail=detail.get('method_details'),
                    round_finished=detail.get('round'),
                    time=detail.get('time'),
                    fight_detail_url=detail.get('url')
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
                
                stats['total'] += 1
                
                if i % 100 == 0:
                    session.commit()
                    logger.info(f"  Processed {i}/{len(fight_details)} fights")
            
            except Exception as e:
                logger.error(f"Error processing fight {detail.get('fight_id')}: {e}")
                continue
        
        session.commit()
        
        # Show results
        logger.info("\n" + "=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total fights processed: {stats['total']}")
        logger.info(f"Fighter 1 wins: {stats['fighter_1_wins']}")
        logger.info(f"Fighter 2 wins: {stats['fighter_2_wins']}")
        logger.info(f"Draws: {stats['draws']}")
        logger.info(f"No contests: {stats['no_contests']}")
        logger.info(f"Missing fighters: {stats['missing_fighters']}")
        logger.info(f"Missing events: {stats['missing_events']}")
        
        total_wins = stats['fighter_1_wins'] + stats['fighter_2_wins']
        if total_wins > 0:
            f1_pct = stats['fighter_1_wins'] / total_wins * 100
            f2_pct = stats['fighter_2_wins'] / total_wins * 100
            logger.info(f"\nWin distribution: {f1_pct:.1f}% fighter_1, {f2_pct:.1f}% fighter_2")
        
        if stats['fighter_2_wins'] > 0:
            logger.success(f"\n✅ SUCCESS! Both fighter_1 and fighter_2 wins found!")
        else:
            logger.error(f"\n❌ ERROR! No fighter_2 wins found")
        
        logger.info("=" * 80)
        
    finally:
        session.close()

if __name__ == '__main__':
    main()

