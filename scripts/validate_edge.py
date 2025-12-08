#!/usr/bin/env python3
"""
Edge Validation Script - Determine if your model has a betting edge

This script helps you determine if your ML model can actually beat the market.
Accuracy alone isn't enough - you need to beat the bookmakers' odds.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from loguru import logger
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def calculate_edge(model_probability: float, bookmaker_odds: int) -> float:
    """
    Calculate edge over bookmaker
    
    Args:
        model_probability: Your model's win probability (0-1)
        bookmaker_odds: American odds (e.g., -150, +200)
    
    Returns:
        Edge as decimal (positive = you have edge)
    """
    # Convert American odds to implied probability
    if bookmaker_odds < 0:
        implied_prob = abs(bookmaker_odds) / (abs(bookmaker_odds) + 100)
    else:
        implied_prob = 100 / (bookmaker_odds + 100)
    
    # Calculate edge
    edge = model_probability - implied_prob
    
    return edge


def simulate_betting_results(predictions: pd.DataFrame, 
                             min_edge: float = 0.05,
                             initial_bankroll: float = 10000) -> Dict:
    """
    Simulate betting results to see if edge exists
    
    Args:
        predictions: DataFrame with columns:
                    - model_prob: Your model's probability
                    - actual_result: 1 if prediction correct, 0 if wrong
                    - bookmaker_odds: Odds offered
        min_edge: Minimum edge to place bet
        initial_bankroll: Starting bankroll
    
    Returns:
        Dictionary with simulation results
    """
    bankroll = initial_bankroll
    bets_placed = 0
    bets_won = 0
    total_profit = 0
    
    for _, row in predictions.iterrows():
        model_prob = row['model_prob']
        actual_result = row['actual_result']
        odds = row.get('bookmaker_odds', -110)  # Default to -110 if not available
        
        # Calculate edge
        edge = calculate_edge(model_prob, odds)
        
        # Only bet if we have minimum edge
        if edge < min_edge:
            continue
        
        # Kelly Criterion for stake sizing (use 25% Kelly for safety)
        if odds < 0:
            decimal_odds = 1 + (100 / abs(odds))
        else:
            decimal_odds = 1 + (odds / 100)
        
        kelly = (decimal_odds * model_prob - 1) / (decimal_odds - 1)
        stake = bankroll * min(kelly * 0.25, 0.05)  # Max 5% of bankroll
        
        bets_placed += 1
        
        # Calculate profit/loss
        if actual_result == 1:  # Won
            if odds < 0:
                profit = stake * (100 / abs(odds))
            else:
                profit = stake * (odds / 100)
            bets_won += 1
        else:  # Lost
            profit = -stake
        
        total_profit += profit
        bankroll += profit
    
    if bets_placed == 0:
        return {
            'has_edge': False,
            'reason': 'No bets met minimum edge requirement',
            'bets_placed': 0
        }
    
    roi = (total_profit / initial_bankroll) * 100
    win_rate = (bets_won / bets_placed) * 100
    
    return {
        'has_edge': roi > 0,
        'bets_placed': bets_placed,
        'bets_won': bets_won,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'roi': roi,
        'final_bankroll': bankroll,
        'avg_edge_per_bet': total_profit / bets_placed if bets_placed > 0 else 0
    }


def analyze_edge_by_scenario(predictions: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze where your edge exists (if at all)
    
    Returns DataFrame showing edge by different scenarios
    """
    scenarios = []
    
    # Analyze by confidence level
    for conf_threshold in [0.55, 0.60, 0.65, 0.70]:
        high_conf = predictions[predictions['model_prob'] >= conf_threshold]
        if len(high_conf) > 10:
            accuracy = high_conf['actual_result'].mean()
            scenarios.append({
                'scenario': f'Confidence >= {conf_threshold:.0%}',
                'n_bets': len(high_conf),
                'accuracy': accuracy,
                'avg_model_prob': high_conf['model_prob'].mean(),
                'potential_edge': accuracy - 0.52  # vs typical -110 odds
            })
    
    # Analyze by underdog vs favorite
    if 'is_underdog' in predictions.columns:
        for bet_type in ['favorite', 'underdog']:
            subset = predictions[predictions['is_underdog'] == (bet_type == 'underdog')]
            if len(subset) > 10:
                accuracy = subset['actual_result'].mean()
                scenarios.append({
                    'scenario': f'Betting {bet_type}s',
                    'n_bets': len(subset),
                    'accuracy': accuracy,
                    'avg_model_prob': subset['model_prob'].mean(),
                    'potential_edge': accuracy - subset['model_prob'].mean()
                })
    
    return pd.DataFrame(scenarios)


def analyze_underdog_strategy(predictions: pd.DataFrame) -> Dict:
    """
    Comprehensive underdog betting analysis
    
    Args:
        predictions: DataFrame with model predictions and results
        
    Returns:
        Dictionary with detailed underdog analysis
    """
    logger.info("\n" + "="*60)
    logger.info("UNDERDOG STRATEGY ANALYSIS")
    logger.info("="*60)
    
    # Filter for underdogs
    if 'is_underdog' in predictions.columns:
        underdogs = predictions[predictions['is_underdog'] == True].copy()
    else:
        # Infer from odds or probability
        underdogs = predictions[predictions['bookmaker_odds'] > 0].copy()
        if len(underdogs) == 0:
            # Try using model probability
            underdogs = predictions[predictions['model_prob'] < 0.5].copy()
    
    if len(underdogs) == 0:
        logger.warning("No underdogs found in dataset")
        return {'has_edge': False, 'reason': 'No underdogs in data'}
    
    logger.info(f"\nFound {len(underdogs)} underdog opportunities")
    
    # Calculate edge for each underdog
    underdogs['edge'] = underdogs.apply(
        lambda row: calculate_edge(row['model_prob'], row['bookmaker_odds']),
        axis=1
    )
    
    # Analyze by odds range
    logger.info("\n--- Edge by Odds Range ---")
    odds_ranges = [
        (100, 150, '+100 to +150 (slight underdogs)'),
        (150, 200, '+150 to +200 (moderate underdogs)'),
        (200, 300, '+200 to +300 (big underdogs)'),
        (300, 1000, '+300+ (huge underdogs)')
    ]
    
    range_results = []
    
    for min_odds, max_odds, label in odds_ranges:
        subset = underdogs[
            (underdogs['bookmaker_odds'] >= min_odds) & 
            (underdogs['bookmaker_odds'] < max_odds)
        ]
        
        if len(subset) > 5:
            avg_edge = subset['edge'].mean()
            win_rate = subset['actual_result'].mean()
            
            # Simulate betting this range
            sim = simulate_betting_results(subset[subset['edge'] > 0.03], min_edge=0.03)
            
            range_results.append({
                'odds_range': label,
                'n_fights': len(subset),
                'avg_edge': avg_edge,
                'win_rate': win_rate,
                'roi': sim.get('roi', 0) if sim['bets_placed'] > 0 else 0
            })
            
            logger.info(f"\n{label}:")
            logger.info(f"  Fights: {len(subset)}")
            logger.info(f"  Avg Edge: {avg_edge:+.2%}")
            logger.info(f"  Win Rate: {win_rate:.1%}")
            logger.info(f"  ROI: {sim.get('roi', 0):.2f}%")
    
    # Find optimal confidence threshold for underdogs
    logger.info("\n--- Optimal Underdog Threshold ---")
    thresholds = [0.30, 0.35, 0.40, 0.45]
    threshold_results = []
    
    for threshold in thresholds:
        subset = underdogs[underdogs['model_prob'] >= threshold]
        
        if len(subset) < 10:
            continue
        
        sim = simulate_betting_results(subset, min_edge=0.04)
        
        if sim['bets_placed'] > 0:
            threshold_results.append({
                'min_probability': threshold,
                'n_bets': sim['bets_placed'],
                'win_rate': sim.get('win_rate', 0),
                'roi': sim.get('roi', 0),
                'profit': sim.get('total_profit', 0)
            })
            
            logger.info(f"\nBet when model prob >= {threshold:.0%}:")
            logger.info(f"  Bets: {sim['bets_placed']}")
            logger.info(f"  Win Rate: {sim.get('win_rate', 0):.1f}%")
            logger.info(f"  ROI: {sim.get('roi', 0):.2f}%")
    
    # Find best threshold
    if threshold_results:
        best = max(threshold_results, key=lambda x: x['roi'])
        logger.info("\n" + "="*60)
        logger.success(f"BEST UNDERDOG STRATEGY:")
        logger.success(f"  Bet underdogs when model probability >= {best['min_probability']:.0%}")
        logger.success(f"  Expected ROI: {best['roi']:.2f}%")
        logger.success(f"  Win Rate: {best['win_rate']:.1f}%")
        logger.success(f"  Bets per year: ~{best['n_bets']}")
        logger.info("="*60)
        
        return {
            'has_edge': best['roi'] > 5,
            'best_threshold': best['min_probability'],
            'expected_roi': best['roi'],
            'win_rate': best['win_rate'],
            'bets_per_year': best['n_bets'],
            'odds_ranges': range_results,
            'threshold_analysis': threshold_results
        }
    else:
        logger.warning("\nNo profitable underdog strategy found")
        return {'has_edge': False, 'reason': 'No threshold produces positive ROI'}


def create_underdog_betting_system(model_threshold: float = 0.40, 
                                   min_edge: float = 0.05,
                                   odds_range: Tuple[int, int] = (120, 250)):
    """
    Create a focused underdog betting system
    
    Args:
        model_threshold: Minimum model probability to bet
        min_edge: Minimum edge required
        odds_range: (min_odds, max_odds) to target
        
    Returns:
        Betting system configuration
    """
    return {
        'name': 'UFC Underdog Value System',
        'rules': {
            'bet_when': [
                f'Fighter is underdog (+{odds_range[0]} to +{odds_range[1]})',
                f'Model probability >= {model_threshold:.0%}',
                f'Edge >= {min_edge:.0%}',
                'No recent injuries',
                'Not coming off long layoff'
            ],
            'skip_when': [
                'Edge < 5%',
                'Model probability < 35%',
                'Odds > +300 (too risky)',
                'Insufficient data on fighters'
            ],
            'position_sizing': f'{min_edge*5:.1%} of bankroll (Quarter Kelly)',
            'max_bet': '5% of bankroll',
            'max_exposure': '15% of bankroll at once'
        },
        'expected_performance': {
            'bets_per_year': '20-40',
            'win_rate': '38-45%',
            'target_roi': '8-15%',
            'variance': 'HIGH (be prepared for losing streaks)'
        }
    }


def main():
    """
    Main validation function
    
    This would typically load your backtest results and analyze them
    """
    logger.info("Edge Validation Script")
    logger.info("="*60)
    
    # Example: Load backtest results
    # In reality, you'd load actual predictions vs results
    
    print("""
    To use this script properly:
    
    1. Run backtesting to get predictions vs actual results
    2. Include bookmaker odds for each fight
    3. Load the data and run edge analysis
    
    Example usage:
    
    predictions = pd.DataFrame({
        'model_prob': [0.65, 0.58, 0.72, ...],
        'actual_result': [1, 0, 1, ...],
        'bookmaker_odds': [-150, +120, -200, ...]
    })
    
    results = simulate_betting_results(predictions, min_edge=0.05)
    
    if results['has_edge']:
        print(f"✅ Edge detected! ROI: {results['roi']:.2f}%")
    else:
        print(f"❌ No edge. Do not bet.")
    """)
    
    # Demonstrate with synthetic data
    logger.info("\nDemo with synthetic data:")
    
    np.random.seed(42)
    n_fights = 100
    
    # Scenario 1: Model has edge
    logger.info("\nScenario 1: Model with 5% edge")
    demo_data_edge = pd.DataFrame({
        'model_prob': np.random.beta(7, 3, n_fights),  # Avg ~0.70
        'bookmaker_odds': [-110] * n_fights,  # Implies ~52%
        'actual_result': np.random.binomial(1, 0.65, n_fights)  # 65% accuracy
    })
    
    results_edge = simulate_betting_results(demo_data_edge, min_edge=0.05)
    logger.info(f"  Bets placed: {results_edge['bets_placed']}")
    logger.info(f"  Win rate: {results_edge['win_rate']:.1f}%")
    logger.info(f"  ROI: {results_edge['roi']:.2f}%")
    logger.info(f"  Has edge: {results_edge['has_edge']}")
    
    # Scenario 2: Model has NO edge
    logger.info("\nScenario 2: Model with NO edge")
    demo_data_no_edge = pd.DataFrame({
        'model_prob': np.random.beta(5, 5, n_fights),  # Avg ~0.50
        'bookmaker_odds': [-110] * n_fights,
        'actual_result': np.random.binomial(1, 0.52, n_fights)  # 52% accuracy (same as market)
    })
    
    results_no_edge = simulate_betting_results(demo_data_no_edge, min_edge=0.05)
    logger.info(f"  Bets placed: {results_no_edge['bets_placed']}")
    logger.info(f"  Win rate: {results_no_edge.get('win_rate', 0):.1f}%")
    logger.info(f"  ROI: {results_no_edge.get('roi', 0):.2f}%")
    logger.info(f"  Has edge: {results_no_edge['has_edge']}")


if __name__ == '__main__':
    main()

