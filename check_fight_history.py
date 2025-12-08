from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight
from features.fighter_features import FighterFeatureExtractor

db = DatabaseManager()
session = db.get_session()

# Get Chimaev
chimaev = session.query(Fighter).filter(Fighter.name.ilike('%Chimaev%')).first()
print(f"Chimaev ID: {chimaev.id}")
print(f"Official Record: {chimaev.wins}-{chimaev.losses}-{chimaev.draws}")

# Get his fight history
extractor = FighterFeatureExtractor(session)
fight_history = extractor._get_fight_history(chimaev.id)

print(f"\nFights in database: {len(fight_history)}")
print("\nFight History:")
print(fight_history[['event_date', 'result', 'method', 'weight_class']].head(15))

# Get rolling stats
rolling = extractor._extract_rolling_stats(chimaev.id, fight_history)
print(f"\nRolling Stats:")
for k, v in rolling.items():
    print(f"  {k}: {v:.3f}")

session.close()
