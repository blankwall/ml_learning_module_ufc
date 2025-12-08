#!/usr/bin/env python3
"""
Quick Start Script - Test the UFC Betting Engine setup
"""

import sys
from pathlib import Path
from loguru import logger

logger.add("logs/quickstart.log", rotation="10 MB")


def check_dependencies():
    """Check if all required packages are installed"""
    logger.info("Checking dependencies...")
    
    required_packages = [
        'beautifulsoup4', 'lxml', 'requests', 'sqlalchemy', 'pandas',
        'numpy', 'scikit-learn', 'xgboost', 'lightgbm', 'torch',
        'streamlit', 'plotly', 'yaml', 'loguru'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.debug(f"✓ {package}")
        except ImportError:
            logger.error(f"✗ {package}")
            missing.append(package)
    
    if missing:
        logger.error(f"Missing packages: {', '.join(missing)}")
        logger.info("Install with: pip install -r requirements.txt")
        return False
    
    logger.success("All dependencies installed!")
    return True


def check_data():
    """Check if data directories exist"""
    logger.info("Checking data directories...")
    
    directories = [
        'data/raw',
        'data/processed',
        'data/predictions',
        'models/saved',
        'logs'
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        else:
            logger.debug(f"✓ {directory}")
    
    logger.success("All directories ready!")
    return True


def test_event_parsing():
    """Test parsing the included UFC 319 event"""
    logger.info("\nTesting event parser with ufc_319.html...")
    
    try:
        from scrapers.event_scraper import EventScraper
        
        scraper = EventScraper()
        event_data = scraper.scrape_event_from_file('ufc_319.html')
        
        if event_data:
            logger.success(f"✓ Parsed event: {event_data['name']}")
            logger.info(f"  Found {len(event_data['fights'])} fights")
            
            # Show first fight
            if event_data['fights']:
                fight = event_data['fights'][0]
                logger.info(f"  Example fight: {fight.get('fighter_1_name')} vs {fight.get('fighter_2_name')}")
            
            # Save parsed event
            import json
            output_file = Path('data/processed/ufc_319_parsed.json')
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(event_data, f, indent=2)
            
            logger.success(f"Saved to {output_file}")
            return True
        else:
            logger.error("Failed to parse event")
            return False
            
    except Exception as e:
        logger.error(f"Error parsing event: {e}")
        return False


def test_database():
    """Test database connection"""
    logger.info("\nTesting database connection...")
    
    try:
        from database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        stats = db.get_stats_summary()
        
        logger.success("✓ Database connected!")
        logger.info(f"  Fighters: {stats['fighters']}")
        logger.info(f"  Events: {stats['events']}")
        logger.info(f"  Fights: {stats['fights']}")
        logger.info(f"  Predictions: {stats['predictions']}")
        
        if stats['fighters'] == 0:
            logger.warning("Database is empty. Run scraper to populate.")
            logger.info("Quick test: python database/db_manager.py --populate --events-file data/processed/ufc_319_parsed.json")
        
        return True
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False


def test_config():
    """Test configuration file"""
    logger.info("\nChecking configuration...")
    
    try:
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        logger.success("✓ Configuration loaded!")
        logger.info(f"  Database type: {config['database']['type']}")
        logger.info(f"  LLM provider: {config['llm']['provider']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return False


def print_next_steps():
    """Print next steps for the user"""
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    logger.info("""
1. POPULATE DATABASE:
   python database/db_manager.py --populate \\
     --events-file data/processed/ufc_319_parsed.json

2. VIEW DATA:
   streamlit run dashboard/app.py

3. FOR FULL SETUP, RUN SCRAPERS:
   # This will take several hours
   python scrapers/fighter_scraper.py --mode all
   python scrapers/event_scraper.py --mode all

4. CREATE TRAINING DATA:
   python features/feature_pipeline.py --create --prepare

5. TRAIN MODELS:
   python models/baseline_models.py --train --evaluate
   python models/neural_net.py --train --evaluate

6. GENERATE PREDICTIONS:
   python predict.py --fighter-1 "Fighter A" --fighter-2 "Fighter B"

7. RUN BACKTEST:
   python backtesting/backtest_engine.py

For detailed instructions, see SETUP.md
""")
    logger.info("="*80)


def main():
    """Run all quick start checks"""
    logger.info("="*80)
    logger.info("UFC BETTING ENGINE - QUICK START")
    logger.info("="*80)
    
    results = []
    
    # Run checks
    results.append(("Dependencies", check_dependencies()))
    results.append(("Data Directories", check_data()))
    results.append(("Configuration", test_config()))
    results.append(("Event Parser", test_event_parsing()))
    results.append(("Database", test_database()))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("QUICK START SUMMARY")
    logger.info("="*80)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        logger.success("\n✓ All checks passed! System is ready.")
        print_next_steps()
    else:
        logger.error("\n✗ Some checks failed. Please fix the issues above.")
        logger.info("See SETUP.md for detailed installation instructions.")


if __name__ == '__main__':
    main()

