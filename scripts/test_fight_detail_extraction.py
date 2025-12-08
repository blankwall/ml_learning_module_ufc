#!/usr/bin/env python3
"""
Test script to validate fight detail extraction
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.event_scraper import EventScraper
from loguru import logger


def test_single_fight(fight_url: str):
    """Test extraction on a single fight"""
    
    logger.info(f"Testing fight detail extraction for: {fight_url}")
    
    scraper = EventScraper()
    
    # Scrape the fight
    details = scraper.scrape_fight_details(fight_url)
    
    if details:
        logger.success("Fight details extracted successfully!")
        print("\n" + "="*80)
        print("FIGHT DETAILS")
        print("="*80)
        print(json.dumps(details, indent=2))
        print("="*80)
        
        # Validate key fields
        required_fields = ['fighter_1_name', 'fighter_2_name', 'winner', 'method']
        missing = [f for f in required_fields if f not in details or not details[f]]
        
        if missing:
            logger.warning(f"Missing fields: {missing}")
        else:
            logger.success("All key fields present!")
        
        # Check totals
        if 'totals' in details:
            logger.info(f"Totals extracted: {len(details['totals'].get('fighter_1', {}))} stats per fighter")
        
        # Check sig strikes
        if 'significant_strikes' in details:
            logger.info(f"Sig strikes extracted: {len(details['significant_strikes'].get('fighter_1', {}))} stats per fighter")
        
        return details
    else:
        logger.error("Failed to extract fight details")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test fight detail extraction')
    parser.add_argument('--url', type=str,
                       default='http://ufcstats.com/fight-details/5f5b626e67529056',
                       help='Fight detail URL to test')
    
    args = parser.parse_args()
    
    test_single_fight(args.url)


if __name__ == '__main__':
    main()

