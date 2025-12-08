from database.db_manager import DatabaseManager
from database.schema import Fight

db = DatabaseManager()
session = db.get_session()

# Get random sample of fights
fights = session.query(Fight).limit(20).all()

print("Sample of 20 fights:")
print("=" * 80)

for fight in fights:
    print(f"\nFight {fight.id}:")
    print(f"  Fighter 1: {fight.fighter_1.name if fight.fighter_1 else 'Unknown'}")
    print(f"  Fighter 2: {fight.fighter_2.name if fight.fighter_2 else 'Unknown'}")
    print(f"  Result: {fight.result}")
    print(f"  Method: {fight.method}")

# Count results
total = session.query(Fight).count()
f1_wins = session.query(Fight).filter(Fight.result == 'fighter_1').count()
f2_wins = session.query(Fight).filter(Fight.result == 'fighter_2').count()
draws = session.query(Fight).filter(Fight.result == 'draw').count()

print("\n" + "=" * 80)
print("OVERALL STATISTICS:")
print("=" * 80)
print(f"Total fights: {total}")
print(f"Fighter 1 wins: {f1_wins} ({f1_wins/total*100:.1f}%)")
print(f"Fighter 2 wins: {f2_wins} ({f2_wins/total*100:.1f}%)")
print(f"Draws: {draws} ({draws/total*100:.1f}%)")

session.close()

