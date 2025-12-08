"""
Test importing a single fight to see what happens
"""
import json
from database.db_manager import DatabaseManager
from database.schema import Fighter, Event, Fight
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load one Chimaev fight from JSON
with open('data/processed/events.json') as f:
    events = json.load(f)

# Find UFC 308
test_fight = None
test_event = None
for event in events:
    if 'UFC 308' in event['name']:
        test_event = event
        for fight in event.get('fights', []):
            if 'Chimaev' in fight.get('fighter_1_name', ''):
                test_fight = fight
                break
        break

if not test_fight:
    print("Fight not found!")
    exit(1)

print("TEST FIGHT DATA FROM JSON:")
print("=" * 60)
print(f"Fighter 1: {test_fight['fighter_1_name']}")
print(f"Fighter 2: {test_fight['fighter_2_name']}")
print(f"Result in JSON: {test_fight['result']}")
print(f"Method: {test_fight['method']}")

# Now check what's in the database for this fight
db = DatabaseManager()
session = db.get_session()

# Find fighters
f1 = session.query(Fighter).filter_by(fighter_id=test_fight['fighter_1_id']).first()
f2 = session.query(Fighter).filter_by(fighter_id=test_fight['fighter_2_id']).first()

print(f"\nFighters in database:")
print(f"  F1: {f1.name} (ID: {f1.id})")
print(f"  F2: {f2.name} (ID: {f2.id})")

# Find the fight in database
fight = session.query(Fight).filter_by(
    fighter_1_id=f1.id,
    fighter_2_id=f2.id
).first()

if fight:
    print(f"\nFIGHT IN DATABASE:")
    print(f"  Fight ID: {fight.id}")
    print(f"  Fighter 1 ID: {fight.fighter_1_id}")
    print(f"  Fighter 2 ID: {fight.fighter_2_id}")
    print(f"  Result: {fight.result}")
    print(f"  Winner ID: {fight.winner_id}")
    print(f"  Method: {fight.method}")
    
    print(f"\n🔍 ANALYSIS:")
    print(f"  JSON says: result = '{test_fight['result']}'")
    print(f"  DB says: result = '{fight.result}'")
    
    if test_fight['result'] != fight.result:
        print(f"\n❌ MISMATCH! Result got flipped during import!")
    else:
        print(f"\n✅ Results match")
else:
    print("\n❌ Fight not found in database!")

session.close()

