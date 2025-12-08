"""
Performance Metrics for Backtesting
"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_metrics(results_df: pd.DataFrame, initial_bankroll: float) -> Dict:
    """
    Calculate comprehensive performance metrics
    
    Args:
        results_df: DataFrame with backtest results
        initial_bankroll: Starting bankroll
        
    Returns:
        Dictionary of performance metrics
    """
    final_bankroll = results_df['bankroll'].iloc[-1]
    
    # Filter to only placed bets
    bets_df = results_df[results_df['bet_placed']]
    
    if len(bets_df) == 0:
        return {
            'total_bets': 0,
            'roi': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0
        }
    
    # Basic metrics
    total_profit = final_bankroll - initial_bankroll
    roi = (total_profit / initial_bankroll)
    
    num_bets = len(bets_df)
    wins = len(bets_df[bets_df['profit_loss'] > 0])
    win_rate = wins / num_bets
    
    # Risk metrics
    returns = bets_df['profit_loss'] / bets_df['stake']
    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(num_bets) if returns.std() > 0 else 0
    
    # Drawdown
    bankroll_series = results_df['bankroll']
    cummax = bankroll_series.cummax()
    drawdown = (bankroll_series - cummax) / cummax
    max_drawdown = abs(drawdown.min())
    
    # Profit factor
    gross_profit = bets_df[bets_df['profit_loss'] > 0]['profit_loss'].sum()
    gross_loss = abs(bets_df[bets_df['profit_loss'] < 0]['profit_loss'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    metrics = {
        'total_bets': num_bets,
        'wins': wins,
        'losses': num_bets - wins,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'roi': roi,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'avg_profit_per_bet': total_profit / num_bets,
    }
    
    return metrics


def calculate_calibration(predictions: np.ndarray, actuals: np.ndarray, n_bins: int = 10) -> Dict:
    """
    Calculate calibration metrics
    
    Args:
        predictions: Predicted probabilities
        actuals: Actual outcomes (0 or 1)
        n_bins: Number of bins for calibration
        
    Returns:
        Calibration metrics
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(predictions, bins[:-1])
    
    calibration_data = []
    
    for i in range(1, n_bins + 1):
        mask = bin_indices == i
        if mask.sum() > 0:
            predicted_prob = predictions[mask].mean()
            actual_freq = actuals[mask].mean()
            count = mask.sum()
            
            calibration_data.append({
                'bin': i,
                'predicted_prob': predicted_prob,
                'actual_freq': actual_freq,
                'count': count
            })
    
    calibration_df = pd.DataFrame(calibration_data)
    
    # Expected Calibration Error (ECE)
    ece = ((calibration_df['predicted_prob'] - calibration_df['actual_freq']).abs() * 
           calibration_df['count']).sum() / len(predictions)
    
    return {
        'calibration_curve': calibration_df,
        'expected_calibration_error': ece
    }

