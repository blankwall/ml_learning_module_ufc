# Export schema after training

from models.xgboost_model import XGBoostModel
from loguru import logger

logger.info("Loading XGBoost model...")
xgb_model = XGBoostModel()

try:
    xgb_model.load_model('xgboost_model')
except FileNotFoundError:
    logger.error("XGBoost model not found. Please train first:")
    logger.error("  python -m models.xgboost_model --train")
    exit(1)

# Export the schema
xgb_model.export_feature_schema(version="1.0.0")

# Load and use schema
from schema import get_feature_list, align_feature_vector, validate_feature_vector

features = get_feature_list()
logger.info(f"Loaded schema with {len(features)} features")

# Example: Create a test feature dictionary with a few features
# In practice, this would come from feature extraction
test_feature_dict = {
    "f1_height_cm": 180.0,
    "f1_weight_lbs": 170.0,
    "f1_reach_inches": 72.0,
    "f1_age": 28.0,
    # ... (in practice, all features would be populated)
}

# Test alignment (will fill missing features with 0.0)
aligned = align_feature_vector(test_feature_dict)
logger.info(f"Aligned feature vector length: {len(aligned)}")
logger.info(f"First 10 aligned values: {aligned[:10]}")

# Test validation
is_valid, missing = validate_feature_vector(test_feature_dict, strict=False)
if not is_valid:
    logger.warning(f"Feature vector validation failed. Missing: {len(missing)} features")
else:
    logger.info("Feature vector structure is valid (non-strict mode)")

print(f"\nSchema Summary:")
print(f"  Total features: {len(features)}")
print(f"  First 5 features: {features[:5]}")
print(f"  Last 5 features: {features[-5:]}")