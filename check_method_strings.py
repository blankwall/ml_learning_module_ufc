from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.fighter_features import FighterFeatureExtractor
import pandas as pd

db = DatabaseManager()
session = db.get_session()

chimaev = session.query(Fighter).filter(Fighter.name.ilike('%Chimaev%')).first()

extractor = FighterFeatureExtractor(session)
fight_history = extractor._get_fight_history(chimaev.id)

print(f"Chimaev's fight methods:")
print("=" * 60)
for idx, row in fight_history.head(10).iterrows():
    method = row['method']
    
    # Check if it matches the finish pattern
    is_finish = pd.Series([method]).str.contains('KO|TKO|Submission', na=False, case=False).iloc[0]
    
    print(f"{row['event_date']:<25} {method:<15} Finish? {is_finish}")

print("\n" + "=" * 60)
print("Testing the regex pattern:")
test_methods = ["KO/TKO", "SUB", "U-DEC", "M-DEC", "Submission"]
for method in test_methods:
    matches = pd.Series([method]).str.contains('KO|TKO|Submission', na=False, case=False).iloc[0]
    print(f"'{method}' matches? {matches}")

session.close()

