from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight

db = DatabaseManager()
session = db.get_session()

chimaev = session.query(Fighter).filter(Fighter.name.ilike('%Chimaev%')).first()

# Get a specific fight (Oct 2024 vs Whittaker)
fights = session.query(Fight).filter(
    (Fight.fighter_1_id == chimaev.id) | (Fight.fighter_2_id == chimaev.id)
).join(Fight.event).all()

print("Chimaev's fights in database:")
for fight in fights[:5]:
    is_f1 = fight.fighter_1_id == chimaev.id
    opponent_name = fight.fighter_2.name if is_f1 else fight.fighter_1.name
    
    print(f"\nFight ID: {fight.id}")
    print(f"  Event: {fight.event.name}")
    print(f"  Chimaev is: {'fighter_1' if is_f1 else 'fighter_2'}")
    print(f"  Opponent: {opponent_name}")
    print(f"  Result: {fight.result}")
    print(f"  Method: {fight.method}")
    print(f"  Winner ID: {fight.winner_id}")
    print(f"  Chimaev ID: {chimaev.id}")

session.close()
