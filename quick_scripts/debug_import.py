import json
from database.db_manager import DatabaseManager
from database.schema import Fighter

# Check one Chimaev fight in detail
with open('data/processed/events.json') as f:
    events = json.load(f)

# Find UFC 308 (Chimaev vs Whittaker)
for event in events:
    if 'UFC 308' in event['name']:
        for fight in event.get('fights', []):
            if 'Chimaev' in fight.get('fighter_1_name', ''):
                print("JSON DATA:")
                print("=" * 60)
                print(f"Fighter 1 Name: {fight['fighter_1_name']}")
                print(f"Fighter 1 ID: {fight['fighter_1_id']}")
                print(f"Fighter 2 Name: {fight['fighter_2_name']}")
                print(f"Fighter 2 ID: {fight['fighter_2_id']}")
                print(f"Result: {fight['result']}")
                print(f"Method: {fight['method']}")
                
                # Now check database
                db = DatabaseManager()
                session = db.get_session()
                
                f1 = session.query(Fighter).filter_by(fighter_id=fight['fighter_1_id']).first()
                f2 = session.query(Fighter).filter_by(fighter_id=fight['fighter_2_id']).first()
                
                print("\nDATABASE RECORDS:")
                print("=" * 60)
                print(f"Fighter 1 ({fight['fighter_1_id']}): {f1.name if f1 else 'NOT FOUND'} (DB ID: {f1.id if f1 else 'N/A'})")
                print(f"Fighter 2 ({fight['fighter_2_id']}): {f2.name if f2 else 'NOT FOUND'} (DB ID: {f2.id if f2 else 'N/A'})")
                
                session.close()
                break
        break

