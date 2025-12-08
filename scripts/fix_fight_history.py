#!/usr/bin/env python3
"""
Post-processing script to fix fight history data using fight details
"""

import json
from pathlib import Path
from collections import defaultdict
from loguru import logger


def load_json(file_path: str) -> dict:
    """Load JSON file"""
    logger.info(f"Loading {file_path}...")
    with open(file_path, 'r') as f:
        return json.load(f)


def save_json(data: dict, file_path: str):
    """Save JSON file"""
    logger.info(f"Saving to {file_path}...")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def fix_fight_history(fighters_file: str, fight_details_file: str, output_file: str = None):
    """
    Fix fight history in fighters.json using accurate data from fight_details.json
    
    Args:
        fighters_file: Path to fighters.json
        fight_details_file: Path to fight_details.json
        output_file: Path to save corrected fighters.json (optional)
    """
    
    # Load data
    fighters = load_json(fighters_file)
    fight_details = load_json(fight_details_file)
    
    logger.info(f"Loaded {len(fighters)} fighters and {len(fight_details)} fight details")
    
    # Create a mapping of fight_id -> fight details
    fight_map = {}
    for fight in fight_details:
        fight_id = fight.get('fight_id')
        if fight_id:
            fight_map[fight_id] = fight
    
    logger.info(f"Created fight map with {len(fight_map)} fights")
    
    # Create fighter_id -> fighter mapping for quick lookup
    fighter_map = {}
    for fighter in fighters:
        fighter_id = fighter.get('fighter_id')
        if fighter_id:
            fighter_map[fighter_id] = fighter
    
    # Track corrections
    corrections_made = 0
    fighters_updated = 0
    
    # Fix each fighter's fight history
    for fighter in fighters:
        fighter_id = fighter.get('fighter_id')
        fighter_name = fighter.get('name')
        fight_history = fighter.get('fight_history', [])
        
        if not fight_history:
            continue
        
        fighter_corrected = False
        
        for fight in fight_history:
            fight_detail_url = fight.get('fight_detail_url')
            
            if not fight_detail_url:
                continue
            
            # Extract fight_id from URL
            fight_id = fight_detail_url.split('/')[-1]
            
            # Look up accurate fight details
            if fight_id in fight_map:
                details = fight_map[fight_id]
                
                # Determine which fighter is which
                fighter_1_id = details.get('fighter_1_id')
                fighter_2_id = details.get('fighter_2_id')
                fighter_1_name = details.get('fighter_1_name')
                fighter_2_name = details.get('fighter_2_name')
                
                # Current fighter is fighter_1
                if fighter_id == fighter_1_id:
                    correct_opponent = fighter_2_name
                    correct_opponent_url = f"http://ufcstats.com/fighter-details/{fighter_2_id}"
                # Current fighter is fighter_2
                elif fighter_id == fighter_2_id:
                    correct_opponent = fighter_1_name
                    correct_opponent_url = f"http://ufcstats.com/fighter-details/{fighter_1_id}"
                else:
                    # Can't determine - might need fighter URL matching
                    continue
                
                # Check if correction needed
                current_opponent = fight.get('opponent')
                if current_opponent != correct_opponent:
                    logger.debug(f"Fixing {fighter_name} vs {current_opponent} -> {correct_opponent}")
                    fight['opponent'] = correct_opponent
                    fight['opponent_url'] = correct_opponent_url
                    corrections_made += 1
                    fighter_corrected = True
        
        if fighter_corrected:
            fighters_updated += 1
    
    logger.success(f"Made {corrections_made} corrections across {fighters_updated} fighters")
    
    # Save corrected data
    if output_file:
        save_json(fighters, output_file)
        logger.success(f"Saved corrected fighters to {output_file}")
    else:
        # Backup original and overwrite
        backup_file = fighters_file + '.backup'
        import shutil
        shutil.copy(fighters_file, backup_file)
        logger.info(f"Created backup: {backup_file}")
        
        save_json(fighters, fighters_file)
        logger.success(f"Updated {fighters_file}")
    
    return fighters


def validate_fight_history(fighters_file: str, fight_details_file: str):
    """
    Validate fight history data by comparing with fight details
    
    Args:
        fighters_file: Path to fighters.json
        fight_details_file: Path to fight_details.json
    """
    
    fighters = load_json(fighters_file)
    fight_details = load_json(fight_details_file)
    
    # Create fight map
    fight_map = {f.get('fight_id'): f for f in fight_details if f.get('fight_id')}
    
    issues = []
    total_fights_checked = 0
    
    for fighter in fighters:
        fighter_id = fighter.get('fighter_id')
        fighter_name = fighter.get('name')
        
        for fight in fighter.get('fight_history', []):
            fight_detail_url = fight.get('fight_detail_url')
            
            if not fight_detail_url:
                continue
            
            total_fights_checked += 1
            fight_id = fight_detail_url.split('/')[-1]
            
            if fight_id not in fight_map:
                issues.append({
                    'type': 'missing_details',
                    'fighter': fighter_name,
                    'fight_id': fight_id
                })
                continue
            
            details = fight_map[fight_id]
            
            # Check if opponent name matches
            opponent = fight.get('opponent')
            fighter_1_name = details.get('fighter_1_name')
            fighter_2_name = details.get('fighter_2_name')
            
            if opponent not in [fighter_1_name, fighter_2_name]:
                issues.append({
                    'type': 'opponent_mismatch',
                    'fighter': fighter_name,
                    'fight_id': fight_id,
                    'recorded_opponent': opponent,
                    'actual_fighters': [fighter_1_name, fighter_2_name]
                })
    
    logger.info(f"\nValidation Results:")
    logger.info(f"  Total fights checked: {total_fights_checked}")
    logger.info(f"  Issues found: {len(issues)}")
    
    if issues:
        logger.warning("\nIssue breakdown:")
        issue_types = defaultdict(int)
        for issue in issues:
            issue_types[issue['type']] += 1
        
        for issue_type, count in issue_types.items():
            logger.warning(f"  {issue_type}: {count}")
        
        # Show first few examples
        logger.info("\nFirst 5 issues:")
        for issue in issues[:5]:
            logger.info(f"  {issue}")
    else:
        logger.success("No issues found!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix fight history data')
    parser.add_argument('--fighters-file', type=str,
                       default='data/processed/fighters.json',
                       help='Path to fighters JSON file')
    parser.add_argument('--fight-details-file', type=str,
                       default='data/processed/fight_details.json',
                       help='Path to fight details JSON file')
    parser.add_argument('--output', type=str,
                       help='Output file (optional, default: overwrite with backup)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate, do not fix')
    
    args = parser.parse_args()
    
    if args.validate_only:
        validate_fight_history(args.fighters_file, args.fight_details_file)
    else:
        fix_fight_history(args.fighters_file, args.fight_details_file, args.output)


if __name__ == '__main__':
    main()

