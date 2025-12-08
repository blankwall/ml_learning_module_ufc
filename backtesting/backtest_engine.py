"""
Backtesting Engine - Tests betting strategies on historical data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
import yaml
from pathlib import Path

from database.db_manager import DatabaseManager
from models.ensemble import EnsembleModel
from .metrics import calculate_metrics


class BacktestEngine:
    """Backtest betting strategies on historical fights"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize backtest engine"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.backtest_config = self.config['backtesting']
        self.betting_config = self.config['betting']
        
        self.db = DatabaseManager(config_path)
        self.model = EnsembleModel(config_path)
        
        # Load models
        self.model.load_models()
        
        logger.info("Initialized backtest engine")
    
    def run_backtest(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Run backtest on historical data
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            DataFrame with backtest results
        """
        if start_date is None:
            start_date = self.backtest_config['start_date']
        if end_date is None:
            end_date = self.backtest_config['end_date']
        
        logger.info(f"Running backtest from {start_date} to {end_date}")
        
        # Load training data with actual results
        from features.feature_pipeline import FeaturePipeline
        
        pipeline = FeaturePipeline()
        df = pipeline.load_dataset('data/processed/training_data.csv')
        
        # Filter by date if we have date information
        # For now, use all data
        
        X, y = pipeline.prepare_features(df, fit_scaler=True)
        
        # Get predictions
        logger.info("Generating predictions...")
        predictions, probabilities = self.model.predict(X)
        
        # Create backtest results
        results = []
        bankroll = self.backtest_config['initial_bankroll']
        
        for i in range(len(df)):
            model_prob = probabilities[i]
            actual_result = y.iloc[i]
            
            # Determine if we should bet
            edge, should_bet, stake_pct = self._calculate_bet_decision(model_prob)
            
            if should_bet:
                # Calculate profit/loss
                stake = bankroll * stake_pct
                
                # Assuming even odds for simplicity (-110 both sides)
                # In production, you'd use actual odds
                if actual_result == 1:  # Fighter 1 won
                    profit = stake * 0.91  # Win at -110
                else:
                    profit = -stake  # Loss
                
                bankroll += profit
                
                results.append({
                    'fight_id': df.iloc[i]['fight_id'] if 'fight_id' in df.columns else i,
                    'model_probability': model_prob,
                    'actual_result': actual_result,
                    'edge': edge,
                    'stake': stake,
                    'profit_loss': profit,
                    'bankroll': bankroll,
                    'bet_placed': True
                })
            else:
                results.append({
                    'fight_id': df.iloc[i]['fight_id'] if 'fight_id' in df.columns else i,
                    'model_probability': model_prob,
                    'actual_result': actual_result,
                    'edge': edge,
                    'stake': 0,
                    'profit_loss': 0,
                    'bankroll': bankroll,
                    'bet_placed': False
                })
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(df)} fights. Bankroll: ${bankroll:,.2f}")
        
        results_df = pd.DataFrame(results)
        
        # Calculate summary statistics
        self._print_backtest_summary(results_df)
        
        # Save results
        output_path = Path('data/predictions') / f'backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results_df.to_csv(output_path, index=False)
        logger.success(f"Saved backtest results to {output_path}")
        
        return results_df
    
    def _calculate_bet_decision(self, model_probability: float) -> tuple:
        """
        Determine if we should bet based on edge and Kelly criterion
        
        Args:
            model_probability: Model's predicted probability
            
        Returns:
            (edge, should_bet, stake_percentage)
        """
        # Assuming even odds (-110 both sides) for simplicity
        # In production, use actual market odds
        market_probability = 0.5
        implied_odds = 1.91  # -110 odds
        
        edge = model_probability - market_probability
        
        # Check minimum edge requirement
        if edge < self.betting_config['min_edge']:
            return edge, False, 0
        
        # Check minimum confidence
        if model_probability < self.betting_config['min_confidence']:
            return edge, False, 0
        
        # Kelly criterion
        kelly_fraction = self.betting_config['kelly_fraction']
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds-1, p = win probability, q = 1-p
        b = implied_odds - 1
        p = model_probability
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Apply fractional Kelly
        stake_pct = max(0, min(kelly * kelly_fraction, self.betting_config['max_bet_size']))
        
        should_bet = stake_pct > 0
        
        return edge, should_bet, stake_pct
    
    def _print_backtest_summary(self, results_df: pd.DataFrame):
        """Print summary statistics from backtest"""
        initial_bankroll = self.backtest_config['initial_bankroll']
        final_bankroll = results_df['bankroll'].iloc[-1]
        
        # Filter to only bets placed
        bets_df = results_df[results_df['bet_placed']]
        
        if len(bets_df) == 0:
            logger.warning("No bets placed during backtest!")
            return
        
        total_profit = final_bankroll - initial_bankroll
        roi = (total_profit / initial_bankroll) * 100
        
        num_bets = len(bets_df)
        wins = len(bets_df[bets_df['profit_loss'] > 0])
        losses = len(bets_df[bets_df['profit_loss'] < 0])
        win_rate = wins / num_bets if num_bets > 0 else 0
        
        avg_profit = bets_df[bets_df['profit_loss'] > 0]['profit_loss'].mean() if wins > 0 else 0
        avg_loss = abs(bets_df[bets_df['profit_loss'] < 0]['profit_loss'].mean()) if losses > 0 else 0
        
        # Calculate max drawdown
        bankroll_series = results_df['bankroll']
        cummax = bankroll_series.cummax()
        drawdown = (bankroll_series - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        logger.info("\n" + "="*80)
        logger.info("BACKTEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Initial Bankroll: ${initial_bankroll:,.2f}")
        logger.info(f"Final Bankroll: ${final_bankroll:,.2f}")
        logger.info(f"Total Profit/Loss: ${total_profit:,.2f}")
        logger.info(f"ROI: {roi:.2f}%")
        logger.info(f"\nTotal Bets: {num_bets}")
        logger.info(f"Wins: {wins} ({win_rate:.1%})")
        logger.info(f"Losses: {losses}")
        logger.info(f"Average Win: ${avg_profit:,.2f}")
        logger.info(f"Average Loss: ${avg_loss:,.2f}")
        logger.info(f"Max Drawdown: {max_drawdown:.2f}%")
        logger.info("="*80)


def main():
    """Main function for running backtests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UFC Betting Backtest')
    parser.add_argument('--start-date', type=str,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    engine = BacktestEngine()
    results = engine.run_backtest(args.start_date, args.end_date)


if __name__ == '__main__':
    main()

