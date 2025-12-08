"""
Ensemble Model - Combines predictions from multiple models
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import yaml
from loguru import logger
from pathlib import Path
import joblib

from .baseline_models import BaselineModels
from .neural_net import NeuralNetModel


class EnsembleModel:
    """Ensemble multiple models for better predictions"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize ensemble model"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ensemble_config = self.config['models']['ensemble']
        self.weights = self.ensemble_config['weights']
        
        # Initialize component models
        self.baseline_models = BaselineModels(config_path)
        self.neural_net = NeuralNetModel(config_path)
        
        self.model_dir = Path(self.config['paths']['models'])
        
        logger.info("Initialized ensemble model")
    
    def load_models(self):
        """Load all trained models"""
        logger.info("Loading component models...")
        
        # Load baseline models
        self.baseline_models.load_all_models()
        
        # Load neural network (requires input_dim - we'll handle this dynamically)
        # For now, mark as needing data shape
        logger.info("Neural network will be loaded when data shape is known")
    
    def predict(self, X: pd.DataFrame, use_models: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make ensemble predictions
        
        Args:
            X: Features
            use_models: List of models to use (default: all available)
            
        Returns:
            (predictions, probabilities)
        """
        if use_models is None:
            use_models = list(self.weights.keys())
        
        all_predictions = {}
        all_probabilities = {}
        
        # Get predictions from baseline models
        for model_name in use_models:
            if model_name in ['xgboost', 'random_forest', 'lightgbm', 'logistic']:
                if model_name in self.baseline_models.models:
                    _, probs = self.baseline_models.predict(model_name, X)
                    all_probabilities[model_name] = probs[:, 1]
                    logger.debug(f"Got predictions from {model_name}")
        
        # Get predictions from neural network
        if 'neural_net' in use_models:
            if self.neural_net.model is None:
                try:
                    self.neural_net.load_model('neural_net', input_dim=X.shape[1])
                except:
                    logger.warning("Neural network not available")
            
            if self.neural_net.model is not None:
                _, probs = self.neural_net.predict(X)
                all_probabilities['neural_net'] = probs
                logger.debug("Got predictions from neural_net")
        
        # Weighted ensemble
        ensemble_probs = self._weighted_average(all_probabilities)
        ensemble_preds = (ensemble_probs > 0.5).astype(int)
        
        return ensemble_preds, ensemble_probs
    
    def _weighted_average(self, predictions_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """Calculate weighted average of predictions"""
        total_weight = 0
        weighted_sum = None
        
        for model_name, predictions in predictions_dict.items():
            weight = self.weights.get(model_name, 0)
            
            if weight > 0:
                if weighted_sum is None:
                    weighted_sum = weight * predictions
                else:
                    weighted_sum += weight * predictions
                
                total_weight += weight
        
        if total_weight == 0:
            logger.warning("No valid models with weights > 0")
            return np.ones(len(next(iter(predictions_dict.values())))) * 0.5
        
        return weighted_sum / total_weight
    
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """Evaluate ensemble model"""
        from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
        
        predictions, probabilities = self.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, predictions),
            'log_loss': log_loss(y_test, probabilities),
            'roc_auc': roc_auc_score(y_test, probabilities),
        }
        
        logger.info("\nEnsemble Model Performance:")
        logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"  Log Loss: {metrics['log_loss']:.4f}")
        logger.info(f"  ROC AUC: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def predict_fight(self, fighter_1_id: int, fighter_2_id: int) -> Dict:
        """
        Predict a specific fight
        
        Args:
            fighter_1_id: First fighter database ID
            fighter_2_id: Second fighter database ID
            
        Returns:
            Dictionary with predictions and probabilities
        """
        from features.matchup_features import MatchupFeatureExtractor
        from database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        session = db.get_session()
        
        try:
            # Extract features
            extractor = MatchupFeatureExtractor(session)
            features = extractor.extract_matchup_features(fighter_1_id, fighter_2_id)
            
            # Convert to DataFrame
            X = pd.DataFrame([features])
            
            # Scale features (assuming pipeline is loaded)
            from features.feature_pipeline import FeaturePipeline
            pipeline = FeaturePipeline()
            pipeline.load_pipeline()
            
            # Ensure we have all required features
            missing_features = set(pipeline.feature_names) - set(X.columns)
            for feature in missing_features:
                X[feature] = 0
            
            X = X[pipeline.feature_names]
            X_scaled = pipeline.scaler.transform(X)
            X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
            
            # Make prediction
            prediction, probability = self.predict(X_scaled)
            
            result = {
                'fighter_1_id': fighter_1_id,
                'fighter_2_id': fighter_2_id,
                'fighter_1_win_probability': probability[0],
                'fighter_2_win_probability': 1 - probability[0],
                'predicted_winner': 'fighter_1' if prediction[0] == 1 else 'fighter_2',
                'confidence': abs(probability[0] - 0.5) * 2  # 0-1 scale
            }
            
            return result
            
        finally:
            session.close()


def main():
    """Main function for testing ensemble model"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UFC Ensemble Model')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate ensemble on test set')
    parser.add_argument('--predict', action='store_true',
                       help='Predict a specific fight')
    parser.add_argument('--fighter-1', type=int,
                       help='First fighter ID')
    parser.add_argument('--fighter-2', type=int,
                       help='Second fighter ID')
    parser.add_argument('--data', type=str,
                       default='data/processed/training_data.csv',
                       help='Path to training data')
    
    args = parser.parse_args()
    
    ensemble = EnsembleModel()
    ensemble.load_models()
    
    if args.evaluate:
        from features.feature_pipeline import FeaturePipeline
        
        pipeline = FeaturePipeline()
        df = pipeline.load_dataset(args.data)
        X, y = pipeline.prepare_features(df, fit_scaler=True)
        
        _, X_test, _, y_test = pipeline.train_test_split(X, y)
        
        metrics = ensemble.evaluate(X_test, y_test)
    
    if args.predict:
        if not args.fighter_1 or not args.fighter_2:
            logger.error("--fighter-1 and --fighter-2 required for prediction")
            return
        
        result = ensemble.predict_fight(args.fighter_1, args.fighter_2)
        
        print("\n" + "="*80)
        print("FIGHT PREDICTION")
        print("="*80)
        print(f"Fighter 1 Win Probability: {result['fighter_1_win_probability']:.1%}")
        print(f"Fighter 2 Win Probability: {result['fighter_2_win_probability']:.1%}")
        print(f"Predicted Winner: {result['predicted_winner']}")
        print(f"Confidence: {result['confidence']:.1%}")


if __name__ == '__main__':
    main()

