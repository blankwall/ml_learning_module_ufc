"""
Baseline ML Models - XGBoost, Random Forest, Logistic Regression
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import yaml
import joblib
from loguru import logger

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, log_loss, roc_auc_score, brier_score_loss,
    classification_report, confusion_matrix
)
import xgboost as xgb
import lightgbm as lgb

from features.feature_pipeline import FeaturePipeline


class BaselineModels:
    """Train and evaluate baseline ML models"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize models with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.models = {}
        self.feature_pipeline = FeaturePipeline(config_path)
        self.model_dir = Path(self.config['paths']['models'])
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize_models(self):
        """Initialize all baseline models"""
        logger.info("Initializing baseline models...")
        
        # XGBoost
        xgb_params = self.config['models']['xgboost']
        self.models['xgboost'] = xgb.XGBClassifier(
            n_estimators=xgb_params['n_estimators'],
            max_depth=xgb_params['max_depth'],
            learning_rate=xgb_params['learning_rate'],
            subsample=xgb_params['subsample'],
            colsample_bytree=xgb_params['colsample_bytree'],
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1
        )
        
        # Random Forest
        rf_params = self.config['models']['random_forest']
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=rf_params['n_estimators'],
            max_depth=rf_params['max_depth'],
            min_samples_split=rf_params['min_samples_split'],
            random_state=42,
            n_jobs=-1
        )
        
        # LightGBM
        self.models['lightgbm'] = lgb.LGBMClassifier(
            n_estimators=1000,
            max_depth=6,
            learning_rate=0.01,
            num_leaves=31,
            random_state=42,
            n_jobs=-1
        )
        
        # Logistic Regression (simple baseline)
        self.models['logistic'] = LogisticRegression(
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )
        
        logger.success(f"Initialized {len(self.models)} models")
    
    def train_all_models(self, X_train: pd.DataFrame, y_train: pd.Series,
                        X_val: Optional[pd.DataFrame] = None,
                        y_val: Optional[pd.Series] = None):
        """
        Train all baseline models
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
        """
        if not self.models:
            self.initialize_models()
        
        for model_name, model in self.models.items():
            logger.info(f"\nTraining {model_name}...")
            
            try:
                # XGBoost and LightGBM support early stopping
                if model_name in ['xgboost', 'lightgbm'] and X_val is not None:
                    eval_set = [(X_val, y_val)]
                    model.fit(
                        X_train, y_train,
                        eval_set=eval_set,
                        verbose=False
                    )
                else:
                    model.fit(X_train, y_train)
                
                logger.success(f"Trained {model_name}")
                
                # Save model
                self.save_model(model, model_name)
                
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
    
    def evaluate_model(self, model, model_name: str, 
                      X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """
        Evaluate a single model
        
        Args:
            model: Trained model
            model_name: Name of the model
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Dictionary of evaluation metrics
        """
        logger.info(f"\nEvaluating {model_name}...")
        
        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        metrics = {
            'model_name': model_name,
            'accuracy': accuracy_score(y_test, y_pred),
            'log_loss': log_loss(y_test, y_pred_proba),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'brier_score': brier_score_loss(y_test, y_pred_proba),
        }
        
        # Log metrics
        logger.info(f"\n{model_name} Performance:")
        logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"  Log Loss: {metrics['log_loss']:.4f}")
        logger.info(f"  ROC AUC: {metrics['roc_auc']:.4f}")
        logger.info(f"  Brier Score: {metrics['brier_score']:.4f}")
        
        # Classification report
        logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"\nConfusion Matrix:\n{cm}")
        
        # Feature importance (if available)
        if hasattr(model, 'feature_importances_'):
            importance_df = self.feature_pipeline.get_feature_importance_summary(
                model.feature_importances_, top_n=20
            )
            metrics['feature_importance'] = importance_df
        
        return metrics
    
    def evaluate_all_models(self, X_test: pd.DataFrame, y_test: pd.Series) -> pd.DataFrame:
        """
        Evaluate all trained models
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            DataFrame with all metrics
        """
        all_metrics = []
        
        for model_name, model in self.models.items():
            metrics = self.evaluate_model(model, model_name, X_test, y_test)
            all_metrics.append(metrics)
        
        # Create comparison dataframe
        metrics_df = pd.DataFrame(all_metrics)
        metrics_df = metrics_df.sort_values('roc_auc', ascending=False)
        
        logger.info("\n" + "="*80)
        logger.info("MODEL COMPARISON")
        logger.info("="*80)
        logger.info("\n" + metrics_df[['model_name', 'accuracy', 'log_loss', 'roc_auc', 'brier_score']].to_string(index=False))
        
        # Save metrics
        metrics_path = self.model_dir / 'baseline_metrics.csv'
        metrics_df[['model_name', 'accuracy', 'log_loss', 'roc_auc', 'brier_score']].to_csv(metrics_path, index=False)
        logger.success(f"Saved metrics to {metrics_path}")
        
        return metrics_df
    
    def predict(self, model_name: str, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with a specific model
        
        Args:
            model_name: Name of the model to use
            X: Features
            
        Returns:
            (predictions, probabilities)
        """
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found. Available: {list(self.models.keys())}")
        
        model = self.models[model_name]
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)
        
        return predictions, probabilities
    
    def save_model(self, model, model_name: str):
        """Save a trained model"""
        model_path = self.model_dir / f'{model_name}.pkl'
        joblib.dump(model, model_path)
        logger.info(f"Saved {model_name} to {model_path}")
    
    def load_model(self, model_name: str):
        """Load a saved model"""
        model_path = self.model_dir / f'{model_name}.pkl'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.models[model_name] = joblib.load(model_path)
        logger.success(f"Loaded {model_name} from {model_path}")
    
    def load_all_models(self):
        """Load all saved models"""
        model_names = ['xgboost', 'random_forest', 'lightgbm', 'logistic']
        
        for model_name in model_names:
            try:
                self.load_model(model_name)
            except FileNotFoundError:
                logger.warning(f"Model {model_name} not found, skipping")
    
    def cross_validate(self, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> pd.DataFrame:
        """
        Perform cross-validation on all models
        
        Args:
            X: Features
            y: Labels
            cv: Number of folds
            
        Returns:
            DataFrame with cross-validation results
        """
        from sklearn.model_selection import cross_val_score
        
        if not self.models:
            self.initialize_models()
        
        cv_results = []
        
        for model_name, model in self.models.items():
            logger.info(f"Cross-validating {model_name}...")
            
            # Accuracy
            acc_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
            
            # ROC AUC
            auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc', n_jobs=-1)
            
            cv_results.append({
                'model_name': model_name,
                'mean_accuracy': acc_scores.mean(),
                'std_accuracy': acc_scores.std(),
                'mean_roc_auc': auc_scores.mean(),
                'std_roc_auc': auc_scores.std(),
            })
            
            logger.info(f"  Accuracy: {acc_scores.mean():.4f} (+/- {acc_scores.std():.4f})")
            logger.info(f"  ROC AUC: {auc_scores.mean():.4f} (+/- {auc_scores.std():.4f})")
        
        cv_df = pd.DataFrame(cv_results)
        return cv_df


def main():
    """Main function for training baseline models"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train UFC Baseline Models')
    parser.add_argument('--train', action='store_true',
                       help='Train all models')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate trained models')
    parser.add_argument('--cross-validate', action='store_true',
                       help='Perform cross-validation')
    parser.add_argument('--data', type=str,
                       default='data/processed/training_data.csv',
                       help='Path to training data')
    
    args = parser.parse_args()
    
    # Initialize
    baseline = BaselineModels()
    
    # Load and prepare data
    logger.info("Loading and preparing data...")
    df = baseline.feature_pipeline.load_dataset(args.data)
    X, y = baseline.feature_pipeline.prepare_features(df, fit_scaler=True)
    
    # Split data
    X_train, X_test, y_train, y_test = baseline.feature_pipeline.train_test_split(X, y)
    
    # Further split train into train/val for early stopping
    X_train, X_val, y_train, y_val = baseline.feature_pipeline.train_test_split(
        X_train, y_train, test_size=0.2
    )
    
    if args.cross_validate:
        cv_results = baseline.cross_validate(X_train, y_train, cv=5)
        logger.info("\nCross-Validation Results:")
        logger.info("\n" + cv_results.to_string(index=False))
    
    if args.train:
        baseline.train_all_models(X_train, y_train, X_val, y_val)
        baseline.feature_pipeline.save_pipeline()
    
    if args.evaluate:
        if not baseline.models:
            baseline.load_all_models()
        
        metrics = baseline.evaluate_all_models(X_test, y_test)


if __name__ == '__main__':
    main()

