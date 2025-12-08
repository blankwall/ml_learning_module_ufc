from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.matchup_features import MatchupFeatureExtractor
import pandas as pd

db = DatabaseManager()
session = db.get_session()

f1 = session.query(Fighter).filter(Fighter.name.ilike('%Chimaev%')).first()
f2 = session.query(Fighter).filter(Fighter.name.ilike('%Du Plessis%')).first()

print("=" * 60)
print("FIGHTER 1: Khamzat Chimaev")
print("=" * 60)
print(f"Record: {f1.wins}-{f1.losses}-{f1.draws}")
print(f"Age: {f1.age}")
print(f"Reach: {f1.reach_inches}")
print(f"Height: {f1.height_cm}")
print(f"Striking: {f1.sig_strikes_landed_per_min:.2f}/min")
print(f"Striking Defense: {f1.striking_defense:.1%}")
print(f"Takedowns: {f1.takedown_avg_per_15min:.2f}/15min")
print(f"TD Accuracy: {f1.takedown_accuracy:.1%}")

print("\n" + "=" * 60)
print("FIGHTER 2: Dricus Du Plessis")
print("=" * 60)
print(f"Record: {f2.wins}-{f2.losses}-{f2.draws}")
print(f"Age: {f2.age}")
print(f"Reach: {f2.reach_inches}")
print(f"Height: {f2.height_cm}")
print(f"Striking: {f2.sig_strikes_landed_per_min:.2f}/min")
print(f"Striking Defense: {f2.striking_defense:.1%}")
print(f"Takedowns: {f2.takedown_avg_per_15min:.2f}/15min")
print(f"TD Accuracy: {f2.takedown_accuracy:.1%}")

# Get features
extractor = MatchupFeatureExtractor(session)
features = extractor.extract_matchup_features(f1.id, f2.id)

print("\n" + "=" * 60)
print("KEY DIFFERENTIAL FEATURES")
print("=" * 60)

# Show the top 5 important features and their values
key_features = [
    'f1_win_rate_last_10',
    'f2_win_rate_last_10',
    'round_3_win_rate_diff',
    'takedown_ability_diff',
    'f1_age',
    'f2_age',
    'striking_differential',
    'reach_advantage',
    'f1_total_fights',
    'f2_total_fights'
]

for feat in key_features:
    if feat in features:
        print(f"{feat}: {features[feat]:.3f}")

session.close()
