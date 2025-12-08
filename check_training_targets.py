import pandas as pd

df = pd.read_csv('data/processed/training_data.csv')

print("Training data shape:", df.shape)
print("\nTarget distribution:")
print(df['target'].value_counts())
print(f"\nPercentage:")
print(df['target'].value_counts(normalize=True) * 100)

print("\nFirst 10 samples:")
print(df[['fight_id', 'fighter_1_id', 'fighter_2_id', 'target']].head(10))

