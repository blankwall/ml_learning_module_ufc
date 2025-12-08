#!/usr/bin/env python3
"""
XGBoost Quick Start Script
Get XGBoost model trained and running in minutes
"""

from loguru import logger
from pathlib import Path
from models.xgboost_model import XGBoostModel
from features.feature_pipeline import FeaturePipeline
from sklearn.model_selection import train_test_split

def main():
    """Quick start: Train XGBoost model and show results"""
    
    logger.info("=" * 60)
    logger.info("XGBoost Quick Start for UFC Fight Prediction")
    logger.info("=" * 60)
    
    # Step 1: Check if training data exists
    data_path = Path('data/processed/training_data.csv')
    
    if not data_path.exists():
        logger.error(f"Training data not found: {data_path}")
        logger.info("Please run: python -m features.feature_pipeline --create")
        return
    
    # Step 2: Load and prepare data
    logger.info("\n📊 Loading data...")
    pipeline = FeaturePipeline(initialize_db=False)
    df = pipeline.load_dataset(str(data_path))
    X, y = pipeline.prepare_features(df, fit_scaler=True)
    
    # Step 3: Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"✓ Loaded {len(X_train)} training samples, {len(X_test)} test samples")
    logger.info(f"✓ Using {len(X.columns)} features")
    
    # Step 4: Create and train model
    logger.info("\n🤖 Creating XGBoost model...")
    xgb_model = XGBoostModel()
    xgb_model.create_model(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8
    )
    
    logger.info("\n🏋️ Training model (this will take 1-5 minutes)...")
    metrics = xgb_model.train(X_train, y_train, X_test, y_test, verbose=True)
    
    # Step 5: Show results
    logger.info("\n" + "=" * 60)
    logger.info("📈 TRAINING RESULTS")
    logger.info("=" * 60)
    logger.info(f"Training Accuracy: {metrics['train_accuracy']:.1%}")
    logger.info(f"Training Log Loss: {metrics['train_log_loss']:.4f}")
    logger.info(f"Training AUC: {metrics['train_auc']:.3f}")
    logger.info("")
    logger.info(f"Test Accuracy: {metrics['val_accuracy']:.1%}")
    logger.info(f"Test Log Loss: {metrics['val_log_loss']:.4f}")
    logger.info(f"Test AUC: {metrics['val_auc']:.3f}")
    
    # Step 6: Feature importance
    logger.info("\n" + "=" * 60)
    logger.info("🎯 TOP 15 MOST IMPORTANT FEATURES")
    logger.info("=" * 60)
    
    importance_df = xgb_model.get_feature_importance(top_n=15)
    for idx, row in importance_df.iterrows():
        logger.info(f"{idx+1:2d}. {row['feature']:<40} {row['importance']:>6.0f}")
    
    # Step 7: Save everything
    logger.info("\n💾 Saving model and artifacts...")
    xgb_model.save_model()
    pipeline.save_pipeline()
    
    # Save plots
    xgb_model.plot_feature_importance(top_n=20, save_path='models/saved/feature_importance.png')
    xgb_model.plot_learning_curve(save_path='models/saved/learning_curve.png')
    xgb_model.check_calibration(X_test, y_test, save_path='models/saved/calibration_curve.png')
    
    logger.info("\n" + "=" * 60)
    logger.success("✅ XGBoost Model Ready!")
    logger.info("=" * 60)
    logger.info("\nModel saved to: models/saved/xgboost_model.json")
    logger.info("Plots saved to: models/saved/")
    logger.info("\nNext steps:")
    logger.info("  1. Check feature_importance.png to understand what matters")
    logger.info("  2. Check calibration_curve.png to verify probability quality")
    logger.info("  3. Make predictions: python quick_predict.py")
    logger.info("  4. Read XGBOOST_GUIDE.md for advanced usage")
    logger.info("")


if __name__ == '__main__':
    main()

