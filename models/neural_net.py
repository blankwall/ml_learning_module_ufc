"""
Neural Network Model for UFC fight prediction using PyTorch
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import yaml
from loguru import logger
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score

from features.feature_pipeline import FeaturePipeline


class FightDataset(Dataset):
    """PyTorch Dataset for UFC fights"""
    
    def __init__(self, X: pd.DataFrame, y: pd.Series):
        self.X = torch.FloatTensor(X.values)
        self.y = torch.FloatTensor(y.values)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class FightPredictor(nn.Module):
    """Neural network for fight outcome prediction"""
    
    def __init__(self, input_dim: int, hidden_layers: list = [256, 128, 64], dropout: float = 0.3):
        super(FightPredictor, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        # Hidden layers
        for hidden_dim in hidden_layers:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        # Output layer
        layers.append(nn.Linear(prev_dim, 1))
        layers.append(nn.Sigmoid())
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class NeuralNetModel:
    """Wrapper for training and using the neural network"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize neural network model"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.nn_config = self.config['models']['neural_net']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.feature_pipeline = FeaturePipeline(config_path)
        self.model_dir = Path(self.config['paths']['models'])
        
        logger.info(f"Using device: {self.device}")
    
    def build_model(self, input_dim: int):
        """Build the neural network"""
        self.model = FightPredictor(
            input_dim=input_dim,
            hidden_layers=self.nn_config['hidden_layers'],
            dropout=self.nn_config['dropout']
        ).to(self.device)
        
        logger.info(f"Built neural network with {sum(p.numel() for p in self.model.parameters())} parameters")
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame = None, y_val: pd.Series = None):
        """
        Train the neural network
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
        """
        if self.model is None:
            self.build_model(X_train.shape[1])
        
        # Create datasets
        train_dataset = FightDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.nn_config['batch_size'],
            shuffle=True
        )
        
        # Validation loader
        val_loader = None
        if X_val is not None and y_val is not None:
            val_dataset = FightDataset(X_val, y_val)
            val_loader = DataLoader(val_dataset, batch_size=self.nn_config['batch_size'])
        
        # Loss and optimizer
        criterion = nn.BCELoss()
        optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.nn_config['learning_rate']
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience = 10
        patience_counter = 0
        
        for epoch in range(self.nn_config['epochs']):
            # Training
            self.model.train()
            train_loss = 0.0
            
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device).unsqueeze(1)
                
                # Forward pass
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation
            val_loss = 0.0
            if val_loader is not None:
                self.model.eval()
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        batch_X = batch_X.to(self.device)
                        batch_y = batch_y.to(self.device).unsqueeze(1)
                        
                        outputs = self.model(batch_X)
                        loss = criterion(outputs, batch_y)
                        val_loss += loss.item()
                
                val_loss /= len(val_loader)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    self.save_model('neural_net_best')
                else:
                    patience_counter += 1
                
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
            
            # Log progress
            if (epoch + 1) % 10 == 0:
                log_msg = f"Epoch [{epoch+1}/{self.nn_config['epochs']}], Train Loss: {train_loss:.4f}"
                if val_loader is not None:
                    log_msg += f", Val Loss: {val_loss:.4f}"
                logger.info(log_msg)
        
        logger.success("Training complete!")
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions
        
        Args:
            X: Features
            
        Returns:
            (predictions, probabilities)
        """
        self.model.eval()
        
        dataset = FightDataset(X, pd.Series([0] * len(X)))  # Dummy labels
        loader = DataLoader(dataset, batch_size=self.nn_config['batch_size'])
        
        all_probs = []
        
        with torch.no_grad():
            for batch_X, _ in loader:
                batch_X = batch_X.to(self.device)
                outputs = self.model(batch_X)
                all_probs.extend(outputs.cpu().numpy())
        
        probabilities = np.array(all_probs).flatten()
        predictions = (probabilities > 0.5).astype(int)
        
        return predictions, probabilities
    
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """
        Evaluate the model
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Dictionary of metrics
        """
        predictions, probabilities = self.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, predictions),
            'log_loss': log_loss(y_test, probabilities),
            'roc_auc': roc_auc_score(y_test, probabilities),
        }
        
        logger.info("\nNeural Network Performance:")
        logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"  Log Loss: {metrics['log_loss']:.4f}")
        logger.info(f"  ROC AUC: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def save_model(self, model_name: str = 'neural_net'):
        """Save the model"""
        model_path = self.model_dir / f'{model_name}.pth'
        torch.save(self.model.state_dict(), model_path)
        logger.info(f"Saved model to {model_path}")
    
    def load_model(self, model_name: str = 'neural_net', input_dim: int = None):
        """Load a saved model"""
        model_path = self.model_dir / f'{model_name}.pth'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        if self.model is None:
            if input_dim is None:
                raise ValueError("input_dim must be provided when loading model from scratch")
            self.build_model(input_dim)
        
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        logger.success(f"Loaded model from {model_path}")


def main():
    """Main function for training neural network"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train UFC Neural Network')
    parser.add_argument('--train', action='store_true',
                       help='Train the model')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate the model')
    parser.add_argument('--data', type=str,
                       default='data/processed/training_data.csv',
                       help='Path to training data')
    
    args = parser.parse_args()
    
    # Initialize
    nn_model = NeuralNetModel()
    
    # Load and prepare data
    logger.info("Loading and preparing data...")
    df = nn_model.feature_pipeline.load_dataset(args.data)
    X, y = nn_model.feature_pipeline.prepare_features(df, fit_scaler=True)
    
    # Split data
    X_train, X_test, y_train, y_test = nn_model.feature_pipeline.train_test_split(X, y)
    X_train, X_val, y_train, y_val = nn_model.feature_pipeline.train_test_split(
        X_train, y_train, test_size=0.2
    )
    
    if args.train:
        nn_model.train(X_train, y_train, X_val, y_val)
        nn_model.save_model('neural_net')
        nn_model.feature_pipeline.save_pipeline()
    
    if args.evaluate:
        if nn_model.model is None:
            nn_model.load_model('neural_net', input_dim=X_train.shape[1])
        
        metrics = nn_model.evaluate(X_test, y_test)


if __name__ == '__main__':
    main()

