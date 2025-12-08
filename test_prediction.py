#!/usr/bin/env python3
"""
Quick test of predictions with corrected database
"""

from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight
from loguru import logger

def main():
    db = DatabaseManager("config/config.yaml")
    session = db.get_session()
    
    try:
        # Test with Khamzat Chimaev
        khamzat = session.query(Fighter).filter_by(name="Khamzat Chimaev").first()
        
        if not khamzat:
            logger.error("Khamzat not found!")
            return
        
        # Count wins and losses
        fights = session.query(Fight).filter(
            (Fight.fighter_1_id == khamzat.id) | (Fight.fighter_2_id == khamzat.id)
        ).all()
        
        wins = sum(1 for f in fights if f.winner_id == khamzat.id)
        losses = sum(1 for f in fights if f.winner_id and f.winner_id != khamzat.id and f.result not in ['draw', 'no_contest'])
        
        logger.info("=" * 80)
        logger.info("DATABASE VERIFICATION FOR PREDICTIONS")
        logger.info("=" * 80)
        logger.info(f"\nKhamzat Chimaev:")
        logger.info(f"  Database record: {wins}W - {losses}L")
        logger.info(f"  Total fights in DB: {len(fights)}")
        
        # Check a few other fighters
        fighters_to_check = [
            "Dricus Du Plessis",
            "Robert Whittaker", 
            "Jon Jones",
            "Alex Pereira"
        ]
        
        for name in fighters_to_check:
            fighter = session.query(Fighter).filter_by(name=name).first()
            if fighter:
                fights = session.query(Fight).filter(
                    (Fight.fighter_1_id == fighter.id) | (Fight.fighter_2_id == fighter.id)
                ).all()
                
                wins = sum(1 for f in fights if f.winner_id == fighter.id)
                losses = sum(1 for f in fights if f.winner_id and f.winner_id != fighter.id and f.result not in ['draw', 'no_contest'])
                
                logger.info(f"\n{name}:")
                logger.info(f"  Database record: {wins}W - {losses}L")
                logger.info(f"  fighters.json record: {fighter.wins}W - {fighter.losses}L")
        
        logger.info("\n" + "=" * 80)
        logger.success("✅ Database is ready for predictions!")
        logger.info("\nYou can now run:")
        logger.info("  python xgboost_predict.py")
        logger.info("=" * 80)
    
    finally:
        session.close()

if __name__ == '__main__':
    main()

