#!/usr/bin/env python3
"""
Verify that Khamzat Chimaev's record is correct in the database
"""

from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight
from loguru import logger

def main():
    db = DatabaseManager("config/config.yaml")
    session = db.get_session()
    
    try:
        # Find Khamzat
        khamzat = session.query(Fighter).filter_by(name="Khamzat Chimaev").first()
        
        if not khamzat:
            logger.error("Khamzat Chimaev not found in database!")
            return
        
        logger.info("=" * 80)
        logger.info(f"KHAMZAT CHIMAEV VERIFICATION")
        logger.info("=" * 80)
        logger.info(f"\nFighter ID: {khamzat.fighter_id}")
        logger.info(f"Record from fighters.json: {khamzat.wins}W - {khamzat.losses}L - {khamzat.draws}D")
        
        # Get fights from database
        fights = session.query(Fight).filter(
            (Fight.fighter_1_id == khamzat.id) | (Fight.fighter_2_id == khamzat.id)
        ).all()
        
        db_wins = 0
        db_losses = 0
        db_draws = 0
        
        logger.info(f"\nFights in database: {len(fights)}")
        logger.info("\nFight results:")
        
        for fight in fights:
            # Get opponent
            if fight.fighter_1_id == khamzat.id:
                opponent_id = fight.fighter_2_id
                khamzat_is_fighter_1 = True
            else:
                opponent_id = fight.fighter_1_id
                khamzat_is_fighter_1 = False
            
            opponent = session.get(Fighter, opponent_id)
            opponent_name = opponent.name if opponent else "Unknown"
            
            # Determine result
            if fight.result == 'draw':
                db_draws += 1
                result_str = "DRAW"
            elif fight.winner_id == khamzat.id:
                db_wins += 1
                result_str = "WIN"
            elif fight.winner_id:
                db_losses += 1
                result_str = "LOSS"
            else:
                result_str = "NO RESULT"
            
            logger.info(f"  vs {opponent_name}: {result_str} ({fight.method})")
        
        logger.info(f"\nRecord from database fights: {db_wins}W - {db_losses}L - {db_draws}D")
        logger.info("=" * 80)
        
        # Verify
        if db_losses == 0 and db_wins > 0:
            logger.success(f"\n✅ CORRECT! Khamzat is undefeated with {db_wins} wins")
        elif db_losses > 0:
            logger.error(f"\n❌ ERROR! Khamzat should have 0 losses, but DB shows {db_losses}")
        else:
            logger.warning(f"\n⚠️  WARNING! Khamzat has no fights in database")
    
    finally:
        session.close()

if __name__ == '__main__':
    main()

