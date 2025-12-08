import json

with open('data/processed/events.json') as f:
    events = json.load(f)

# Count results in events.json
total_fights = 0
fighter_1_wins = 0
fighter_2_wins = 0
draws = 0
none_results = 0

for event in events:
    for fight in event.get('fights', []):
        total_fights += 1
        result = fight.get('result')
        
        if result == 'fighter_1':
            fighter_1_wins += 1
        elif result == 'fighter_2':
            fighter_2_wins += 1
        elif result == 'draw':
            draws += 1
        else:
            none_results += 1

print("EVENTS.JSON ANALYSIS:")
print("=" * 60)
print(f"Total fights: {total_fights}")
print(f"Fighter 1 wins: {fighter_1_wins} ({fighter_1_wins/total_fights*100:.1f}%)")
print(f"Fighter 2 wins: {fighter_2_wins} ({fighter_2_wins/total_fights*100:.1f}%)")
print(f"Draws: {draws} ({draws/total_fights*100:.1f}%)")
print(f"None/Unknown: {none_results}")

print("\nSample of fighter_2 wins:")
print("=" * 60)
count = 0
for event in events:
    for fight in event.get('fights', []):
        if fight.get('result') == 'fighter_2':
            print(f"Event: {event['name']}")
            print(f"  Fighter 1: {fight.get('fighter_1_name')}")
            print(f"  Fighter 2: {fight.get('fighter_2_name')}")
            print(f"  Result: {fight.get('result')}")
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break

