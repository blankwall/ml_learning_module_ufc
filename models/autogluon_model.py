"""
AutoGluon Model - Automated ML for UFC fight prediction

AutoGluon automatically:
- Trains multiple model types (XGBoost, LightGBM, CatBoost, Neural Nets, etc.)
- Tunes hyperparameters
- Creates optimal ensembles
- Often achieves better results than manual approaches
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import yaml
from loguru import logger

try:
    from autogluon.tabular import TabularPredictor
    AUTOGLUON_AVAILABLE = True
except ImportError:
    AUTOGLUON_AVAILABLE = False
    logger.warning("AutoGluon not installed. Install with: pip install autogluon.tabular")

from features.feature_pipeline import FeaturePipeline


class AutoGluonModel:
    """
    AutoML model using AutoGluon for fight prediction
    
    This is often the easiest way to get state-of-the-art results.
    AutoGluon will automatically try many models and ensemble them.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize AutoGluon model"""
        if not AUTOGLUON_AVAILABLE:
            raise ImportError("AutoGluon not installed. Install with: pip install autogluon.tabular")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.predictor = None
        self.feature_pipeline = FeaturePipeline(config_path)
        self.model_dir = Path(self.config['paths']['models']) / 'autogluon'
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initialized AutoGluon model")
    
    def train(self, train_data: pd.DataFrame, 
              time_limit: int = 3600,
              quality: str = 'best_quality',
              eval_metric: str = 'roc_auc'):
        """
        Train AutoGluon model
        
        Args:
            train_data: DataFrame with features and 'target' column
            time_limit: Training time limit in seconds (default: 1 hour)
            quality: Quality preset ('best_quality', 'high_quality', 'good_quality', 'medium_quality')
            eval_metric: Metric to optimize ('roc_auc', 'log_loss', 'accuracy')
        """
        logger.info(f"Training AutoGluon with {quality} preset, time limit: {time_limit}s")
        
        # Create predictor
        self.predictor = TabularPredictor(
            label='target',
            path=str(self.model_dir),
            eval_metric=eval_metric,
            problem_type='binary'
        )
        
        # Train
        self.predictor.fit(
            train_data=train_data,
            time_limit=time_limit,
            presets=quality,
            num_cpus='auto',
            num_gpus='auto'
        )
        
        logger.success("AutoGluon training complete!")
        
        # Show leaderboard
        leaderboard = self.predictor.leaderboard(train_data, silent=True)
        logger.info("\nModel Leaderboard (Top 10):")
        logger.info("\n" + leaderboard.head(10).to_string())
        
        return self.predictor
    
    def predict(self, X: pd.DataFrame) -> tuple:
        """
        Make predictions
        
        Args:
            X: Features DataFrame
            
        Returns:
            (predictions, probabilities)
        """
        if self.predictor is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Get predictions
        predictions = self.predictor.predict(X)
        probabilities = self.predictor.predict_proba(X)
        
        return predictions.values, probabilities.values
    
    def evaluate(self, test_data: pd.DataFrame) -> Dict:
        """
        Evaluate model on test data
        
        Args:
            test_data: DataFrame with features and 'target' column
            
        Returns:
            Dictionary of metrics
        """
        if self.predictor is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        logger.info("Evaluating AutoGluon model...")
        
        # Evaluate
        performance = self.predictor.evaluate(test_data, silent=True)
        
        logger.info("\nTest Performance:")
        for metric, value in performance.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        return performance
    
    def get_feature_importance(self, data: pd.DataFrame = None) -> pd.DataFrame:
        """
        Get feature importance
        
        Args:
            data: Optional data for computing importance
            
        Returns:
            DataFrame with feature importance
        """
        if self.predictor is None:
            raise ValueError("Model not trained yet.")
        
        importance = self.predictor.feature_importance(data)
        
        logger.info("\nTop 20 Most Important Features:")
        logger.info("\n" + importance.head(20).to_string())
        
        return importance
    
    def get_model_info(self) -> Dict:
        """Get information about trained models"""
        if self.predictor is None:
            raise ValueError("Model not trained yet.")
        
        info = {
            'best_model': self.predictor.get_model_best(),
            'num_models': len(self.predictor.model_names()),
            'models': self.predictor.model_names(),
            'leaderboard': self.predictor.leaderboard(silent=True)
        }
        
        return info
    
    def save(self):
        """Save model (AutoGluon saves automatically during training)"""
        if self.predictor is None:
            raise ValueError("Model not trained yet.")
        
        logger.info(f"Model already saved to {self.model_dir}")
    
    def load(self, path: str = None):
        """
        Load a trained model
        
        Args:
            path: Path to model directory (optional)
        """
        if path is None:
            path = str(self.model_dir)
        
        self.predictor = TabularPredictor.load(path)
        logger.success(f"Loaded AutoGluon model from {path}")


def main():
    """Main function for training AutoGluon model"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train UFC AutoGluon Model')
    parser.add_argument('--train', action='store_true',
                       help='Train the model')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate the model')
    parser.add_argument('--data', type=str,
                       default='data/processed/training_data.csv',
                       help='Path to training data')
    parser.add_argument('--time-limit', type=int, default=3600,
                       help='Training time limit in seconds (default: 1 hour)')
    parser.add_argument('--quality', type=str, default='best_quality',
                       choices=['best_quality', 'high_quality', 'good_quality', 'medium_quality'],
                       help='Quality preset')
    parser.add_argument('--predict', action='store_true',
                       help='Make a prediction for a single fight')
    parser.add_argument('--fighter-1', type=str,
                       help='First fighter name')
    parser.add_argument('--fighter-2', type=str,
                       help='Second fighter name')
    parser.add_argument('--title-fight', action='store_true',
                       help='Specify if this is a title fight (5 rounds)')
    
    args = parser.parse_args()
    
    # Handle prediction mode separately
    if args.predict:
        if not args.fighter_1 or not args.fighter_2:
            logger.error("Both --fighter-1 and --fighter-2 are required for predictions")
            return
        
        from database.db_manager import DatabaseManager
        from database.schema import Fighter
        from features.matchup_features import MatchupFeatureExtractor
        
        logger.info(f"Predicting: {args.fighter_1} vs {args.fighter_2}")
        
        # Load model
        ag_model = AutoGluonModel()
        ag_model.load()
        ag_model.feature_pipeline.load_pipeline()
        
        # Get fighters from database
        db = DatabaseManager()
        session = db.get_session()
        
        fighter_1 = session.query(Fighter).filter(Fighter.name.ilike(f"%{args.fighter_1}%")).first()
        fighter_2 = session.query(Fighter).filter(Fighter.name.ilike(f"%{args.fighter_2}%")).first()
        
        if not fighter_1:
            logger.error(f"Fighter not found: {args.fighter_1}")
            session.close()
            return
        if not fighter_2:
            logger.error(f"Fighter not found: {args.fighter_2}")
            session.close()
            return
        
        logger.info(f"Matched: {fighter_1.name} vs {fighter_2.name}")
        
        # Extract features
        extractor = MatchupFeatureExtractor(session)
        features = extractor.extract_matchup_features(fighter_1.id, fighter_2.id)
        
        # Add fight-specific features that aren't in fighter stats
        features['is_title_fight'] = 1 if args.title_fight else 0
        
        # Convert to DataFrame
        import pandas as pd
        X_df = pd.DataFrame([features])
        
        # Prepare features using the same pipeline as training
        # This handles removing metadata columns and scaling
        X_scaled, _ = ag_model.feature_pipeline.prepare_features(X_df, fit_scaler=False)
        
        # Make prediction
        prediction = ag_model.predictor.predict(X_scaled)[0]
        probabilities = ag_model.predictor.predict_proba(X_scaled)[0]
        
        # Display results
        fight_type = "TITLE FIGHT (5 rounds)" if args.title_fight else "Non-title fight (3 rounds)"
        logger.info("\n" + "="*60)
        logger.success(f"PREDICTION: {fighter_1.name} vs {fighter_2.name}")
        logger.info(f"Fight Type: {fight_type}")
        logger.info("="*60)
        logger.info(f"{fighter_1.name}: {probabilities[1]*100:.1f}% chance to win")
        logger.info(f"{fighter_2.name}: {probabilities[0]*100:.1f}% chance to win")
        logger.info("")
        if prediction == 1:
            logger.success(f"⭐ Predicted Winner: {fighter_1.name}")
        else:
            logger.success(f"⭐ Predicted Winner: {fighter_2.name}")
        logger.info("="*60)
        
        session.close()
        return
    
    # Initialize
    ag_model = AutoGluonModel()
    
    # Load and prepare data
    logger.info("Loading and preparing data...")
    df = ag_model.feature_pipeline.load_dataset(args.data)
    X, y = ag_model.feature_pipeline.prepare_features(df, fit_scaler=True)
    
    # Split data
    X_train, X_test, y_train, y_test = ag_model.feature_pipeline.train_test_split(X, y)
    
    # Combine for AutoGluon (it handles the split internally if needed)
    train_data = X_train.copy()
    train_data['target'] = y_train
    
    test_data = X_test.copy()
    test_data['target'] = y_test
    
    if args.train:
        # Train
        ag_model.train(
            train_data=train_data,
            time_limit=args.time_limit,
            quality=args.quality
        )
        
        # Get feature importance
        ag_model.get_feature_importance(train_data)
        
        # Get model info
        info = ag_model.get_model_info()
        logger.info(f"\nTrained {info['num_models']} models")
        logger.info(f"Best model: {info['best_model']}")
    
    if args.evaluate:
        if ag_model.predictor is None:
            ag_model.load()
        
        metrics = ag_model.evaluate(test_data)


if __name__ == '__main__':
    main()

