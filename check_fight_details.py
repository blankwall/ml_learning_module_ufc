import json

# Load fight details
with open('data/processed/fight_details.json') as f:
    fight_details = json.load(f)

# Find Chimaev vs Whittaker
print("Searching fight_details.json for Chimaev fights:")
print("=" * 60)

for detail in fight_details:
    if 'Chimaev' in detail.get('fighter_1_name', '') or 'Chimaev' in detail.get('fighter_2_name', ''):
        print(f"\nFight ID: {detail.get('fight_id')}")
        print(f"Fighter 1: {detail.get('fighter_1_name')}")
        print(f"Fighter 2: {detail.get('fighter_2_name')}")
        print(f"Fighter 1 Result: {detail.get('fighter_1_result')}")
        print(f"Fighter 2 Result: {detail.get('fighter_2_result')}")
        print(f"Winner: {detail.get('winner')}")
        print(f"Method: {detail.get('method')}")
        
        # Only show first 5
        if fight_details.index(detail) >= 5:
            break

