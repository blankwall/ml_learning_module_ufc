#!/usr/bin/env python3
"""
Validate fighter records in the database
"""

import sys
from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight, Event
from loguru import logger
from datetime import datetime

def validate_fighter(session, name):
    """Validate a fighter's record"""
    
    fighter = session.query(Fighter).filter_by(name=name).first()
    
    if not fighter:
        logger.error(f"Fighter '{name}' not found in database!")
        return
    
    logger.info("=" * 80)
    logger.info(f"VALIDATING: {name}")
    logger.info("=" * 80)
    logger.info(f"Fighter ID: {fighter.fighter_id}")
    logger.info(f"Record from fighters.json: {fighter.wins}W - {fighter.losses}L - {fighter.draws}D")
    
    # Get all fights
    fights = session.query(Fight).filter(
        (Fight.fighter_1_id == fighter.id) | (Fight.fighter_2_id == fighter.id)
    ).join(Event).all()
    
    # Parse dates and sort properly (date is stored as string!)
    from dateutil import parser
    
    def parse_event_date(fight):
        try:
            event = session.get(Event, fight.event_id)
            if event and event.date:
                return parser.parse(event.date)
        except:
            pass
        return datetime.min
    
    fights.sort(key=parse_event_date, reverse=True)
    
    logger.info(f"\nTotal fights in database: {len(fights)}")
    
    # Count wins/losses
    wins = []
    losses = []
    draws = []
    no_contests = []
    
    for fight in fights:
        # Get opponent
        if fight.fighter_1_id == fighter.id:
            opponent_id = fight.fighter_2_id
        else:
            opponent_id = fight.fighter_1_id
        
        opponent = session.get(Fighter, opponent_id)
        opponent_name = opponent.name if opponent else "Unknown"
        
        # Get event for date
        event = session.get(Event, fight.event_id)
        event_name = event.name if event else "Unknown Event"
        
        # Determine result
        if fight.result == 'draw':
            draws.append({
                'opponent': opponent_name,
                'method': fight.method,
                'event': event_name,
                'fight': fight
            })
        elif fight.result == 'no_contest':
            no_contests.append({
                'opponent': opponent_name,
                'method': fight.method,
                'event': event_name,
                'fight': fight
            })
        elif fight.winner_id == fighter.id:
            wins.append({
                'opponent': opponent_name,
                'method': fight.method,
                'event': event_name,
                'fight': fight
            })
        elif fight.winner_id:
            losses.append({
                'opponent': opponent_name,
                'method': fight.method,
                'event': event_name,
                'fight': fight
            })
    
    logger.info(f"\nDatabase record: {len(wins)}W - {len(losses)}L - {len(draws)}D")
    
    # Show recent fights (last 10)
    logger.info(f"\nRecent fights (last 10):")
    
    all_results = []
    for w in wins:
        all_results.append(('WIN', w))
    for l in losses:
        all_results.append(('LOSS', l))
    for d in draws:
        all_results.append(('DRAW', d))
    
    # Sort by event (most recent first) - fights list is already sorted
    recent_10 = []
    for fight in fights[:10]:
        if fight.winner_id == fighter.id:
            result = 'WIN'
        elif fight.result == 'draw':
            result = 'DRAW'
        elif fight.result == 'no_contest':
            result = 'NC'
        else:
            result = 'LOSS'
        
        # Get opponent
        if fight.fighter_1_id == fighter.id:
            opponent_id = fight.fighter_2_id
        else:
            opponent_id = fight.fighter_1_id
        
        opponent = session.get(Fighter, opponent_id)
        opponent_name = opponent.name if opponent else "Unknown"
        
        event = session.get(Event, fight.event_id)
        event_name = event.name if event else "Unknown"
        
        recent_10.append((result, opponent_name, fight.method, event_name))
    
    for i, (result, opp, method, event) in enumerate(recent_10, 1):
        logger.info(f"  {i}. {result:4} vs {opp:30} ({method:20}) @ {event[:50]}")
    
    # Calculate win rates
    if len(recent_10) > 0:
        recent_wins = sum(1 for r, _, _, _ in recent_10 if r == 'WIN')
        win_rate_10 = recent_wins / len(recent_10)
        logger.info(f"\nWin rate (last 10): {recent_wins}/{len(recent_10)} = {win_rate_10:.1%}")
    
    if len(recent_10) >= 5:
        last_5 = recent_10[:5]
        recent_wins_5 = sum(1 for r, _, _, _ in last_5 if r == 'WIN')
        win_rate_5 = recent_wins_5 / 5
        logger.info(f"Win rate (last 5):  {recent_wins_5}/5 = {win_rate_5:.1%}")
    
    logger.info("=" * 80)
    print()

def main():
    if len(sys.argv) > 1:
        fighter_names = sys.argv[1:]
    else:
        # Default to the fighters in the question
        fighter_names = ["Edson Barboza", "Jalin Turner"]
    
    db = DatabaseManager("config/config.yaml")
    session = db.get_session()
    
    try:
        for name in fighter_names:
            validate_fighter(session, name)
    
    finally:
        session.close()

if __name__ == '__main__':
    main()

