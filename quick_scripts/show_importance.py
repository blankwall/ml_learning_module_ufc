from models.xgboost_model import XGBoostModel

model = XGBoostModel()
model.load_model('xgboost_model')

importance_df = model.get_feature_importance(top_n=30)
print("\nTop 30 Features:")
print("=" * 60)
for idx, row in importance_df.iterrows():
    print(f"{idx+1:2d}. {row['feature']:<45} {row['importance']:>8.0f}")
