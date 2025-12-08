import json
from database.db_manager import DatabaseManager
from database.schema import Fight

# Load fight details
with open('data/processed/fight_details.json') as f:
    fight_details = json.load(f)

details_by_id = {detail['fight_id']: detail for detail in fight_details}

db = DatabaseManager()
session = db.get_session()

# Get first 20 fights
fights = session.query(Fight).filter(Fight.fight_id.isnot(None)).limit(20).all()

matched = 0
not_matched = 0

for fight in fights:
    details = details_by_id.get(fight.fight_id)
    
    if not details:
        print(f"❌ Fight {fight.fight_id} not in fight_details.json")
        continue
    
    f1_result = details.get('fighter_1_result', '')
    f2_result = details.get('fighter_2_result', '')
    
    if f1_result == 'W':
        winning_fighter_name = details.get('fighter_1_name')
    elif f2_result == 'W':
        winning_fighter_name = details.get('fighter_2_name')
    else:
        continue
    
    # Check match
    if fight.fighter_1.name == winning_fighter_name:
        matched += 1
        print(f"✅ Match: '{fight.fighter_1.name}' == '{winning_fighter_name}'")
    elif fight.fighter_2.name == winning_fighter_name:
        matched += 1
        print(f"✅ Match: '{fight.fighter_2.name}' == '{winning_fighter_name}'")
    else:
        not_matched += 1
        print(f"❌ NO MATCH for fight {fight.fight_id}:")
        print(f"   DB Fighter 1: '{fight.fighter_1.name}'")
        print(f"   DB Fighter 2: '{fight.fighter_2.name}'")
        print(f"   Winner in details: '{winning_fighter_name}'")

print(f"\nMatched: {matched}, Not matched: {not_matched}")

session.close()

