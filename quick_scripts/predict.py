#!/usr/bin/env python3
"""
Main Prediction Script - Generate predictions for upcoming fights
"""

import argparse
import json
from pathlib import Path
from loguru import logger

from database.db_manager import DatabaseManager
from models.ensemble import EnsembleModel
from database.schema import Fighter


def predict_event(event_id: str):
    """Predict all fights in an event"""
    logger.info(f"Generating predictions for event: {event_id}")
    
    db = DatabaseManager()
    model = EnsembleModel()
    
    # Load models
    model.load_models()
    
    session = db.get_session()
    
    try:
        from database.schema import Event, Fight
        
        # Get event
        event = session.query(Event).filter_by(event_id=event_id).first()
        
        if not event:
            logger.error(f"Event {event_id} not found in database")
            return
        
        logger.info(f"Event: {event.name} on {event.date}")
        
        # Get fights
        fights = session.query(Fight).filter_by(event_id=event.id).all()
        
        if not fights:
            logger.warning("No fights found for this event")
            return
        
        predictions = []
        
        for i, fight in enumerate(fights, 1):
            logger.info(f"\nFight {i}: {fight.fighter_1.name} vs {fight.fighter_2.name}")
            
            try:
                result = model.predict_fight(fight.fighter_1_id, fight.fighter_2_id)
                
                prediction = {
                    'fight_id': fight.id,
                    'fighter_1': fight.fighter_1.name,
                    'fighter_2': fight.fighter_2.name,
                    'fighter_1_win_prob': result['fighter_1_win_probability'],
                    'fighter_2_win_prob': result['fighter_2_win_probability'],
                    'predicted_winner': result['predicted_winner'],
                    'confidence': result['confidence']
                }
                
                predictions.append(prediction)
                
                logger.info(f"  {fight.fighter_1.name}: {result['fighter_1_win_probability']:.1%}")
                logger.info(f"  {fight.fighter_2.name}: {result['fighter_2_win_probability']:.1%}")
                logger.info(f"  Confidence: {result['confidence']:.1%}")
                
            except Exception as e:
                logger.error(f"Error predicting fight: {e}")
        
        # Save predictions
        output_dir = Path('data/predictions')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'predictions_{event_id}.json'
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        logger.success(f"Saved predictions to {output_file}")
        
    finally:
        session.close()


def predict_single_fight(fighter_1_name: str, fighter_2_name: str):
    """Predict a single fight between two fighters"""
    logger.info(f"Predicting: {fighter_1_name} vs {fighter_2_name}")
    
    db = DatabaseManager()
    model = EnsembleModel()
    
    # Load models
    model.load_models()
    
    session = db.get_session()
    
    try:
        # Find fighters
        fighter_1 = session.query(Fighter).filter(Fighter.name.ilike(f"%{fighter_1_name}%")).first()
        fighter_2 = session.query(Fighter).filter(Fighter.name.ilike(f"%{fighter_2_name}%")).first()
        
        if not fighter_1:
            logger.error(f"Fighter '{fighter_1_name}' not found")
            return
        
        if not fighter_2:
            logger.error(f"Fighter '{fighter_2_name}' not found")
            return
        
        logger.info(f"Matched: {fighter_1.name} vs {fighter_2.name}")
        
        # Generate prediction
        result = model.predict_fight(fighter_1.id, fighter_2.id)
        
        print("\n" + "="*80)
        print("FIGHT PREDICTION")
        print("="*80)
        print(f"\n{fighter_1.name} ({fighter_1.wins}-{fighter_1.losses}-{fighter_1.draws})")
        print(f"  vs")
        print(f"{fighter_2.name} ({fighter_2.wins}-{fighter_2.losses}-{fighter_2.draws})")
        print(f"\n{fighter_1.name} Win Probability: {result['fighter_1_win_probability']:.1%}")
        print(f"{fighter_2.name} Win Probability: {result['fighter_2_win_probability']:.1%}")
        print(f"\nPredicted Winner: {'Fighter 1' if result['predicted_winner'] == 'fighter_1' else 'Fighter 2'}")
        print(f"Confidence: {result['confidence']:.1%}")
        print("="*80)
        
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Generate UFC fight predictions')
    parser.add_argument('--event', type=str,
                       help='Event ID to predict all fights')
    parser.add_argument('--fighter-1', type=str,
                       help='First fighter name')
    parser.add_argument('--fighter-2', type=str,
                       help='Second fighter name')
    
    args = parser.parse_args()
    
    if args.event:
        predict_event(args.event)
    elif args.fighter_1 and args.fighter_2:
        predict_single_fight(args.fighter_1, args.fighter_2)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python predict.py --event UFC-320")
        print("  python predict.py --fighter-1 'Jon Jones' --fighter-2 'Tom Aspinall'")


if __name__ == '__main__':
    main()

