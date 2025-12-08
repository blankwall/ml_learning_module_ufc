import json
from database.db_manager import DatabaseManager
from database.schema import Fight

# Load fight details
with open('data/processed/fight_details.json') as f:
    fight_details = json.load(f)

# Find fights where fighter_2 won in fight_details
fighter_2_wins_in_details = [d for d in fight_details if d.get('fighter_2_result') == 'W']

print(f"Fights where fighter_2 won in fight_details.json: {len(fighter_2_wins_in_details)}")
print(f"Total fights in fight_details.json: {len(fight_details)}")
print(f"Percentage: {len(fighter_2_wins_in_details) / len(fight_details) * 100:.1f}%")

# Now check in database
db = DatabaseManager()
session = db.get_session()

details_by_id = {d['fight_id']: d for d in fight_details}

# Check first 10 fights where fighter_2 should win
checked = 0
should_be_f2 = 0
actually_f2 = 0

for detail in fighter_2_wins_in_details[:10]:
    fight_id = detail['fight_id']
    fight = session.query(Fight).filter_by(fight_id=fight_id).first()
    
    if not fight:
        continue
    
    checked += 1
    winning_name = detail['fighter_2_name']
    
    print(f"\nFight {fight_id}:")
    print(f"  Winner in details: {winning_name}")
    print(f"  DB Fighter 1: {fight.fighter_1.name}")
    print(f"  DB Fighter 2: {fight.fighter_2.name}")
    print(f"  DB Result: {fight.result}")
    
    # Should be fighter_2 win if winner matches fighter_2 in DB
    if fight.fighter_2.name == winning_name:
        should_be_f2 += 1
        print(f"  ✅ Should be: fighter_2 (actual: {fight.result})")
    elif fight.fighter_1.name == winning_name:
        print(f"  ⚠️  Winner is fighter_1 in DB")
    
    if fight.result == 'fighter_2':
        actually_f2 += 1

print(f"\n" + "=" * 60)
print(f"Checked: {checked} fights")
print(f"Should be fighter_2 wins: {should_be_f2}")
print(f"Actually fighter_2 wins in DB: {actually_f2}")

session.close()

