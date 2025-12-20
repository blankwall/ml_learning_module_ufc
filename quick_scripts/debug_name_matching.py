import json
from database.db_manager import DatabaseManager
from database.schema import Fight

# Load fight details
with open('data/processed/fight_details.json') as f:
    fight_details = json.load(f)

db = DatabaseManager()
session = db.get_session()

# Check a fight we know should be fighter_2 win
# Let's find one where fighter_2_result == 'W'
print("Finding fights where fighter_2 won in fight_details.json:")
print("=" * 80)

for detail in fight_details[:10]:
    if detail.get('fighter_2_result') == 'W':
        fight_id = detail.get('fight_id')
        
        # Find in database
        fight = session.query(Fight).filter_by(fight_id=fight_id).first()
        
        if fight:
            print(f"\nFight ID: {fight_id}")
            print(f"\nFIGHT_DETAILS.JSON:")
            print(f"  Fighter 1: '{detail.get('fighter_1_name')}' (Result: {detail.get('fighter_1_result')})")
            print(f"  Fighter 2: '{detail.get('fighter_2_name')}' (Result: {detail.get('fighter_2_result')})")
            print(f"  Winner: {detail.get('winner')}")
            
            print(f"\nDATABASE:")
            print(f"  Fighter 1: '{fight.fighter_1.name}' (ID: {fight.fighter_1_id})")
            print(f"  Fighter 2: '{fight.fighter_2.name}' (ID: {fight.fighter_2_id})")
            print(f"  Result: {fight.result}")
            print(f"  Winner ID: {fight.winner_id}")
            
            # Check name matching
            winner_name = detail.get('fighter_2_name')
            print(f"\nNAME MATCHING:")
            print(f"  Winner in fight_details: '{winner_name}'")
            print(f"  Match fighter_1? {fight.fighter_1.name} == {winner_name}: {fight.fighter_1.name == winner_name}")
            print(f"  Match fighter_2? {fight.fighter_2.name} == {winner_name}: {fight.fighter_2.name == winner_name}")
            
            print("\n" + "=" * 80)
            break

session.close()

