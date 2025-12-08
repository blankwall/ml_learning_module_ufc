import json

# Load events
with open('data/processed/events.json') as f:
    events = json.load(f)

# Find Chimaev fights
print("Checking events.json for Chimaev fights:")
print("=" * 60)

for event in events:
    for fight in event.get('fights', []):
        if 'Chimaev' in fight.get('fighter_1_name', '') or 'Chimaev' in fight.get('fighter_2_name', ''):
            print(f"\nEvent: {event['name']}")
            print(f"Fighter 1: {fight.get('fighter_1_name')}")
            print(f"Fighter 2: {fight.get('fighter_2_name')}")
            print(f"Result: {fight.get('result')}")
            print(f"Winner: {fight.get('winner', 'N/A')}")
            print(f"Method: {fight.get('method')}")
            break

