#!/bin/bash
# UFC Data Collection - Full Pipeline
# This script runs all 3 scraping steps to collect complete UFC data

set -e  # Exit on error

echo "=========================================="
echo "UFC BETTING ENGINE - DATA COLLECTION"
echo "=========================================="
echo ""
echo "This will scrape:"
echo "  1. All UFC fighters (~3000+)"
echo "  2. All UFC events (~750+)"
echo "  3. All fight details (~6000+)"
echo ""
echo "Estimated time: 3-5 hours"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 1
fi

# Create output directory
mkdir -p data/processed

# Step 1: Scrape Fighters
echo ""
echo "=========================================="
echo "STEP 1/3: SCRAPING FIGHTERS"
echo "=========================================="
python scrapers/fighter_scraper.py --mode all --output data/processed/fighters.json

if [ $? -eq 0 ]; then
    echo "✓ Fighters scraped successfully"
else
    echo "✗ Error scraping fighters"
    exit 1
fi

# Step 2: Scrape Events
echo ""
echo "=========================================="
echo "STEP 2/3: SCRAPING EVENTS"
echo "=========================================="
python scrapers/event_scraper.py --mode all --output data/processed/events.json

if [ $? -eq 0 ]; then
    echo "✓ Events scraped successfully"
else
    echo "✗ Error scraping events"
    exit 1
fi

# Step 3: Scrape Fight Details
echo ""
echo "=========================================="
echo "STEP 3/3: SCRAPING FIGHT DETAILS"
echo "=========================================="
echo "This is the longest step (2-3 hours)..."
python scrapers/event_scraper.py --mode fight-details \
  --events-file data/processed/events.json \
  --output data/processed/fight_details.json

if [ $? -eq 0 ]; then
    echo "✓ Fight details scraped successfully"
else
    echo "✗ Error scraping fight details"
    exit 1
fi

# Step 4: Populate Database
echo ""
echo "=========================================="
echo "STEP 4/4: POPULATING DATABASE"
echo "=========================================="
python database/db_manager.py --populate \
  --fighters-file data/processed/fighters.json \
  --events-file data/processed/events.json \
  --fight-details-file data/processed/fight_details.json

if [ $? -eq 0 ]; then
    echo "✓ Database populated successfully"
else
    echo "✗ Error populating database"
    exit 1
fi

# Show stats
echo ""
echo "=========================================="
echo "DATA COLLECTION COMPLETE!"
echo "=========================================="
python database/db_manager.py --stats

echo ""
echo "Next steps:"
echo "  1. Create features: python features/feature_pipeline.py --create --prepare"
echo "  2. Train models: python models/baseline_models.py --train --evaluate"
echo "  3. Launch dashboard: streamlit run dashboard/app.py"
echo ""

