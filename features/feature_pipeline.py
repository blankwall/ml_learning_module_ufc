"""
Feature Pipeline - Orchestrates feature extraction and preprocessing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
from loguru import logger
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

from database.db_manager import DatabaseManager
from .matchup_features import create_training_dataset
from .registry import FeatureRegistry


class FeaturePipeline:
    """Manages the complete feature engineering pipeline"""
    
    def __init__(self, config_path: str = "config/config.yaml", initialize_db: bool = True):
        """
        Initialize feature pipeline
        
        Args:
            config_path: Path to YAML config
            initialize_db: Whether to create a database connection (needed for
                dataset creation, but can be disabled for fast inference)
        """
        self.db = DatabaseManager(config_path) if initialize_db else None
        self.scaler = StandardScaler()
        self.feature_names = None
    
    def create_dataset(
        self,
        output_path: str = 'data/processed/training_data.csv',
        feature_set: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Create complete training dataset
        
        Args:
            output_path: Path to save the dataset
            feature_set: Optional list of feature names to extract.
                        If None, uses FEATURE_SET_FULL (all features)
        """
        if self.db is None:
            raise RuntimeError("FeaturePipeline was initialized with initialize_db=False, "
                               "cannot create dataset without a database connection.")
        session = self.db.get_session()
        try:
            df = create_training_dataset(session, output_path, feature_set=feature_set)
            return df
        finally:
            session.close()
    
    def load_dataset(self, file_path: str = 'data/processed/training_data.csv') -> pd.DataFrame:
        """Load preprocessed dataset"""
        logger.info(f"Loading dataset from {file_path}")
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} samples with {len(df.columns)} features")
        return df
    
    def prepare_features(self, df: pd.DataFrame, 
                        fit_scaler: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features for model training
        
        Args:
            df: Raw dataframe
            fit_scaler: Whether to fit the scaler (True for training, False for inference)
            
        Returns:
            X: Feature matrix
            y: Target vector
        """
        logger.info("Preparing features for training...")
        
        # Separate features and target
        metadata_cols = ['fight_id', 'event_id', 'fighter_1_id', 'fighter_2_id', 
                        'weight_class', 'method', 'target']
        
        feature_cols = [col for col in df.columns if col not in metadata_cols]
        
        X = df[feature_cols].copy()
        y = df['target'] if 'target' in df.columns else None
        
        # For inference, align columns to the feature set seen during training.
        # This avoids XGBoost "feature names should match" errors by:
        #   - adding any missing training-time features with 0
        #   - dropping any new columns not seen during training
        if not fit_scaler and self.feature_names is not None:
            # Add missing expected columns
            missing = [c for c in self.feature_names if c not in X.columns]
            if missing:
                for c in missing:
                    X[c] = 0.0
            # Drop unexpected columns and order to match training
            X = X[self.feature_names]
        else:
            # During training, remember the column order
            self.feature_names = list(X.columns)
        
        # Handle missing values
        X = X.fillna(0)
        
        # Handle infinite values
        X = X.replace([np.inf, -np.inf], 0)
        
        # Scale features
        if fit_scaler:
            X_scaled = self.scaler.fit_transform(X)
            logger.info("Fitted scaler on training data")
        else:
            X_scaled = self.scaler.transform(X)
        
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
        
        logger.success(f"Prepared {len(feature_cols)} features")
        
        return X_scaled, y
    
    def train_test_split(self, X: pd.DataFrame, y: pd.Series, 
                        test_size: float = 0.2, random_state: int = 42) -> Tuple:
        """Split data into train and test sets"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        logger.info(f"Train set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        return X_train, X_test, y_train, y_test
    
    def save_pipeline(self, output_dir: str = 'models/saved'):
        """Save the feature pipeline (scaler and feature names)"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save scaler
        scaler_path = output_path / 'feature_scaler.pkl'
        joblib.dump(self.scaler, scaler_path)
        
        # Save feature names
        features_path = output_path / 'feature_names.pkl'
        joblib.dump(self.feature_names, features_path)
        
        logger.success(f"Saved feature pipeline to {output_dir}")
    
    def load_pipeline(self, input_dir: str = 'models/saved'):
        """Load a saved feature pipeline"""
        input_path = Path(input_dir)
        
        # Load scaler
        scaler_path = input_path / 'feature_scaler.pkl'
        self.scaler = joblib.load(scaler_path)
        
        # Load feature names
        features_path = input_path / 'feature_names.pkl'
        self.feature_names = joblib.load(features_path)
        
        logger.success(f"Loaded feature pipeline from {input_dir}")
    
    def get_feature_importance_summary(self, feature_importances: np.ndarray, 
                                       top_n: int = 20) -> pd.DataFrame:
        """
        Create a summary of feature importances
        
        Args:
            feature_importances: Array of feature importance scores
            top_n: Number of top features to return
            
        Returns:
            DataFrame with feature names and importance scores
        """
        if self.feature_names is None:
            logger.warning("Feature names not set")
            return None
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': feature_importances
        })
        
        importance_df = importance_df.sort_values('importance', ascending=False)
        
        logger.info(f"\nTop {top_n} most important features:")
        logger.info("\n" + importance_df.head(top_n).to_string())
        
        return importance_df
    
    def export_feature_schema(
        self,
        version: str = "1.0.0",
        output_path: str = "schema/feature_schema.json"
    ) -> dict:
        """
        Export feature schema to JSON file.
        
        This creates the canonical feature schema that becomes the master contract
        between training, prediction, Excel export, and API usage.
        
        Args:
            version: Schema version string
            output_path: Path to save the schema file
            
        Returns:
            Schema dictionary
        """
        if self.feature_names is None:
            raise ValueError("No feature names available. Prepare features first.")
        
        import json
        
        schema = {
            "version": version,
            "num_features": len(self.feature_names),
            "features": self.feature_names
        }
        
        # Save to file
        schema_path = Path(output_path)
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(schema_path, 'w') as f:
            json.dump(schema, f, indent=2)
        
        logger.success(f"Exported feature schema to {schema_path}")
        logger.info(f"Schema version: {version}")
        logger.info(f"Total features: {len(self.feature_names)}")
        
        return schema


def main():
    """Main function for running the feature pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UFC Feature Pipeline')
    parser.add_argument('--create', action='store_true',
                       help='Create training dataset from database')
    parser.add_argument('--prepare', action='store_true',
                       help='Prepare features for training')
    parser.add_argument('--input', type=str,
                       default='data/processed/training_data.csv',
                       help='Input dataset path')
    parser.add_argument('--output', type=str,
                       default='data/processed/prepared_data.csv',
                       help='Output dataset path')
    parser.add_argument('--feature-set', type=str,
                       choices=['base', 'advanced', 'full'],
                       default='full',
                       help='Feature set to use: base, advanced, or full (default: full)')
    
    args = parser.parse_args()
    
    pipeline = FeaturePipeline()
    
    if args.create:
        # Map feature set string to actual feature set
        feature_set_map = {
            'base': FeatureRegistry.FEATURE_SET_BASE,
            'advanced': FeatureRegistry.FEATURE_SET_ADVANCED,
            'full': FeatureRegistry.FEATURE_SET_FULL,
        }
        feature_set = feature_set_map[args.feature_set]
        
        logger.info(f"Creating training dataset with '{args.feature_set}' feature set...")
        df = pipeline.create_dataset(feature_set=feature_set)
        logger.info(f"Created dataset with shape: {df.shape}")
        logger.info(f"Total features: {len([c for c in df.columns if c not in ['fight_id', 'event_id', 'fighter_1_id', 'fighter_2_id', 'weight_class', 'method', 'target', 'is_title_fight']])}")
    
    if args.prepare:
        df = pipeline.load_dataset(args.input)
        X, y = pipeline.prepare_features(df, fit_scaler=True)
        
        # Save prepared data
        prepared_df = X.copy()
        prepared_df['target'] = y
        prepared_df.to_csv(args.output, index=False)
        
        # Save pipeline
        pipeline.save_pipeline()
        
        logger.success(f"Prepared data saved to {args.output}")


if __name__ == '__main__':
    main()

