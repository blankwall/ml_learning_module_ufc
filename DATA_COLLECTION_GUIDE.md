# UFC Data Collection Guide

## Complete 3-Step Process

### Overview
The UFC betting engine requires **3 separate scraping steps** to collect all necessary data:

1. **Fighter Profiles** - Basic stats and career information
2. **Events & Fights** - Fight cards and basic results
3. **Fight Details** - Round-by-round detailed statistics ⭐ **CRITICAL**

---

## Step 1: Scrape Fighter Profiles

Collects all UFC fighters and their career statistics.

```bash
# Test with fighters starting with 'A' (quick test)
python scrapers/fighter_scraper.py --mode test --output data/processed/fighters_test.json

# Scrape all fighters (3000+ fighters, takes ~1-2 hours)
python scrapers/fighter_scraper.py --mode all --output data/processed/fighters.json
```

**Data Collected:**
- Name, nickname, record (wins-losses-draws)
- Physical attributes (height, weight, reach, stance, age)
- Career averages (striking accuracy, takedown defense, etc.)
- Fight history (opponents, results, methods)

**Output:** `data/processed/fighters.json`

---

## Step 2: Scrape Events & Fight Cards

Collects all UFC events and the fights on each card.

```bash
# Test with 3 pages (quick test)
python scrapers/event_scraper.py --mode test --output data/processed/events_test.json

# Scrape all events (750+ events across 30 pages, takes ~30 seconds)
python scrapers/event_scraper.py --mode all --output data/processed/events.json
```

**Data Collected:**
- Event name, date, location
- Fight card (all fights on the event)
- Fighter names and IDs for each fight
- Basic results (winner, method, round)
- **Fight detail URLs** (for step 3)

**Output:** `data/processed/events.json`

---

## Step 3: Scrape Detailed Fight Statistics ⭐

**THIS IS THE CRITICAL STEP!**

Scrapes round-by-round statistics for every fight. This data is essential for ML models.

```bash
# Scrape detailed stats for ALL fights
# This will take several hours (6000+ fights at 1 second per fight = ~2 hours)
python scrapers/event_scraper.py --mode fight-details \
  --events-file data/processed/events.json \
  --output data/processed/fight_details.json
```

**Data Collected:**
- **Round-by-round totals:**
  - Knockdowns
  - Significant strikes (landed/attempted)
  - Total strikes (landed/attempted)
  - Takedowns (landed/attempted)
  - Submission attempts
  - Reversals
  - Control time

- **Significant strikes breakdown:**
  - By position: Distance, Clinch, Ground
  - By target: Head, Body, Legs
  - For BOTH fighters

**Output:** `data/processed/fight_details.json`

**Why This is Critical:**
- ML models need detailed strike data to predict outcomes
- Round-by-round stats show fighter momentum and patterns
- Position-specific data reveals fighting styles
- Without this, models only have basic career averages

---

## Step 4: Populate Database

Load all scraped data into the database for easy querying.

```bash
python database/db_manager.py --populate \
  --fighters-file data/processed/fighters.json \
  --events-file data/processed/events.json \
  --fight-details-file data/processed/fight_details.json
```

**Verify:**
```bash
python database/db_manager.py --stats
```

Expected output:
```
Database Statistics:
  Fighters: 3000+
  Events: 750+
  Fights: 6000+
  Predictions: 0
```

---

## Quick Start (Test Mode)

For a quick test with minimal data:

```bash
# 1. Test fighter scraper (just letter 'A')
python scrapers/fighter_scraper.py --mode test --output data/processed/fighters_test.json

# 2. Test event scraper (just 3 pages)
python scrapers/event_scraper.py --mode test --output data/processed/events_test.json

# 3. Scrape fight details for test events
python scrapers/event_scraper.py --mode fight-details \
  --events-file data/processed/events_test.json \
  --output data/processed/fight_details_test.json

# 4. Populate test database
python database/db_manager.py --populate \
  --fighters-file data/processed/fighters_test.json \
  --events-file data/processed/events_test.json \
  --fight-details-file data/processed/fight_details_test.json
```

---

## Full Production Scrape

For complete data collection:

```bash
#!/bin/bash

echo "Starting full UFC data collection..."

# Step 1: Fighters (1-2 hours)
echo "Step 1/3: Scraping fighters..."
python scrapers/fighter_scraper.py --mode all --output data/processed/fighters.json

# Step 2: Events (30 seconds)
echo "Step 2/3: Scraping events..."
python scrapers/event_scraper.py --mode all --output data/processed/events.json

# Step 3: Fight Details (2-3 hours)
echo "Step 3/3: Scraping fight details..."
python scrapers/event_scraper.py --mode fight-details \
  --events-file data/processed/events.json \
  --output data/processed/fight_details.json

# Step 4: Populate Database
echo "Populating database..."
python database/db_manager.py --populate \
  --fighters-file data/processed/fighters.json \
  --events-file data/processed/events.json \
  --fight-details-file data/processed/fight_details.json

echo "Data collection complete!"
python database/db_manager.py --stats
```

**Total Time:** ~3-5 hours (depends on rate limiting and network speed)

---

## Data Flow Diagram

```
┌─────────────────┐
│  UFCStats.com   │
└────────┬────────┘
         │
         ├─► Step 1: Fighter Pages ──► fighters.json
         │   (fighter-details/*)
         │
         ├─► Step 2: Event Pages ───► events.json
         │   (event-details/*)
         │
         └─► Step 3: Fight Details ─► fight_details.json
             (fight-details/*)           ⭐ CRITICAL!
                    │
                    │
         ┌──────────▼──────────┐
         │  Database Manager   │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │   SQLite Database   │
         │  - Fighters         │
         │  - Events           │
         │  - Fights           │
         │  - FightStats ⭐    │
         └─────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  Feature Pipeline   │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │    ML Models        │
         └─────────────────────┘
```

---

## Troubleshooting

### "No fight detail URL found"
Some fights (especially older ones) may not have detailed statistics. This is normal.

### Rate Limiting
The scraper respects UFCStats.com with 1-second delays. If you get blocked:
- Increase `rate_limit` in `config/config.yaml`
- Wait a few minutes and resume

### Resuming Interrupted Scrapes
Fight details saves progress every 50 fights. If interrupted, you can resume by:
1. Load the partial `fight_details.json`
2. Skip already-scraped fights (check by fight_id)
3. Continue from where it stopped

### Memory Issues
If scraping uses too much memory:
- Process events in batches
- Clear the cache directory periodically: `data/raw/`

---

## Next Steps

After data collection:

1. **Create Features:**
   ```bash
   python features/feature_pipeline.py --create --prepare
   ```

2. **Train Models:**
   ```bash
   python models/baseline_models.py --train --evaluate
   python models/neural_net.py --train --evaluate
   ```

3. **Generate Predictions:**
   ```bash
   python predict.py --fighter-1 "Fighter A" --fighter-2 "Fighter B"
   ```

---

## Important Notes

✅ **Always run all 3 scraping steps** - Each provides essential data  
✅ **Fight details is not optional** - ML models need this data  
✅ **Respect rate limits** - Be a good citizen of the internet  
✅ **Cache is your friend** - Reuse downloaded HTML when possible  
✅ **Test mode first** - Validate setup before full scrape  

---

## Summary

| Step | Data | Time | Size | Critical? |
|------|------|------|------|-----------|
| 1. Fighters | Career stats | 1-2h | 3000+ | ✅ Yes |
| 2. Events | Fight cards | 30s | 750+ | ✅ Yes |
| 3. Fight Details | Round stats | 2-3h | 6000+ | ⭐ **CRITICAL** |
| 4. Database | Populate DB | 5m | - | ✅ Yes |

**Total:** ~3-5 hours for complete dataset

Good luck! 🥊

