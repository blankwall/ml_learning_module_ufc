#!/usr/bin/env python3
"""
Backtest Last 100 Fights - Validate Your Edge-Finding System

This script:
1. Takes the last 100 completed fights
2. Generates your model's predictions
3. Compares to actual bookmaker odds
4. Identifies which fights had "edge"
5. Simulates betting ONLY those fights
6. Shows if your edge-detection system works

Use this to validate your approach before paper trading!
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from loguru import logger
import json

from database.db_manager import DatabaseManager
from scripts.validate_edge import calculate_edge, simulate_betting_results


def load_recent_fights(n_fights: int = 100) -> pd.DataFrame:
    """
    Load the most recent N completed fights from database
    
    Args:
        n_fights: Number of recent fights to load
        
    Returns:
        DataFrame with fight data
    """
    logger.info(f"Loading last {n_fights} completed fights...")
    
    db = DatabaseManager()
    session = db.get_session()
    
    # Query recent fights
    from database.schema import Fight, Event
    from sqlalchemy import desc
    
    fights = session.query(Fight)\
        .join(Event)\
        .filter(Fight.winner.isnot(None))\
        .order_by(desc(Event.date))\
        .limit(n_fights)\
        .all()
    
    logger.info(f"Loaded {len(fights)} fights")
    
    # Convert to DataFrame
    fight_data = []
    for fight in fights:
        fight_data.append({
            'fight_id': fight.id,
            'event_name': fight.event.name,
            'event_date': fight.event.date,
            'fighter_1_id': fight.fighter_1_id,
            'fighter_2_id': fight.fighter_2_id,
            'fighter_1_name': fight.fighter_1.name,
            'fighter_2_name': fight.fighter_2.name,
            'winner': fight.winner,
            'method': fight.method,
            'weight_class': fight.weight_class
        })
    
    session.close()
    
    return pd.DataFrame(fight_data)


def get_model_predictions(fights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate model predictions for each fight
    
    In practice, you'd load your trained model and predict.
    For now, this is a placeholder.
    
    Args:
        fights_df: DataFrame with fight data
        
    Returns:
        DataFrame with predictions added
    """
    logger.info("Generating model predictions...")
    
    # TODO: Replace with actual model predictions
    # For now, simulate predictions
    
    predictions = []
    
    for _, fight in fights_df.iterrows():
        # Placeholder: In reality, you'd do:
        # model = load_model('models/autogluon_model.pkl')
        # features = extract_features(fight)
        # prob = model.predict_proba(features)
        
        # For demonstration, use random probabilities
        model_prob_fighter1 = np.random.beta(5, 5)  # Simulated prediction
        
        predictions.append({
            'fight_id': fight['fight_id'],
            'fighter_1_name': fight['fighter_1_name'],
            'fighter_2_name': fight['fighter_2_name'],
            'event_name': fight['event_name'],
            'model_prob_fighter1': model_prob_fighter1,
            'model_prob_fighter2': 1 - model_prob_fighter1,
            'actual_winner': fight['winner']
        })
    
    return pd.DataFrame(predictions)


def get_historical_odds(fights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get historical bookmaker odds for these fights
    
    In practice, you'd scrape or load from BestFightOdds.com
    For now, this estimates odds.
    
    Args:
        fights_df: DataFrame with fight data
        
    Returns:
        DataFrame with odds added
    """
    logger.info("Loading historical odds...")
    
    # TODO: Replace with actual odds scraping
    # Check if odds file exists
    odds_file = Path('data/odds/historical_odds.csv')
    
    if odds_file.exists():
        logger.info(f"Loading odds from {odds_file}")
        odds_df = pd.read_csv(odds_file)
        return odds_df
    else:
        logger.warning("No historical odds file found. Estimating odds...")
        logger.warning("For real validation, scrape actual odds from BestFightOdds.com!")
        
        # Estimate odds (this is not ideal but works for testing)
        estimated_odds = []
        
        for _, fight in fights_df.iterrows():
            # Estimate odds based on which fighter won
            # In reality, bookmakers don't know outcome, so this is just for demo
            
            # Typical UFC odds distribution
            if np.random.random() > 0.5:
                # Fighter 1 is favorite
                fighter1_odds = int(np.random.uniform(-250, -110))
                fighter2_odds = int(np.random.uniform(110, 220))
            else:
                # Fighter 2 is favorite
                fighter1_odds = int(np.random.uniform(110, 220))
                fighter2_odds = int(np.random.uniform(-250, -110))
            
            estimated_odds.append({
                'fight_id': fight['fight_id'],
                'fighter_1_odds': fighter1_odds,
                'fighter_2_odds': fighter2_odds
            })
        
        return pd.DataFrame(estimated_odds)


def identify_edge_opportunities(predictions_df: pd.DataFrame, 
                               odds_df: pd.DataFrame,
                               min_edge: float = 0.05) -> pd.DataFrame:
    """
    Identify which fights had betting edge
    
    Args:
        predictions_df: Model predictions
        odds_df: Bookmaker odds
        min_edge: Minimum edge to consider (default 5%)
        
    Returns:
        DataFrame with edge analysis
    """
    logger.info(f"Identifying edge opportunities (min edge: {min_edge:.0%})...")
    
    # Merge predictions with odds
    merged = predictions_df.merge(odds_df, on='fight_id')
    
    opportunities = []
    
    for _, row in merged.iterrows():
        # Check edge on fighter 1
        edge_f1 = calculate_edge(row['model_prob_fighter1'], row['fighter_1_odds'])
        
        # Check edge on fighter 2
        edge_f2 = calculate_edge(row['model_prob_fighter2'], row['fighter_2_odds'])
        
        # Determine which side has edge (if any)
        best_edge = max(edge_f1, edge_f2)
        
        if best_edge >= min_edge:
            # We have edge!
            if edge_f1 > edge_f2:
                # Edge on fighter 1
                fighter = row['fighter_1_name']
                opponent = row['fighter_2_name']
                model_prob = row['model_prob_fighter1']
                odds = row['fighter_1_odds']
                edge = edge_f1
                is_underdog = odds > 0
                bet_on = 'fighter_1'
            else:
                # Edge on fighter 2
                fighter = row['fighter_2_name']
                opponent = row['fighter_1_name']
                model_prob = row['model_prob_fighter2']
                odds = row['fighter_2_odds']
                edge = edge_f2
                is_underdog = odds > 0
                bet_on = 'fighter_2'
            
            # Determine if bet won
            actual_winner = row['actual_winner']
            bet_won = (bet_on == actual_winner)
            
            opportunities.append({
                'fight_id': row['fight_id'],
                'event': row['event_name'],
                'fighter': fighter,
                'opponent': opponent,
                'model_prob': model_prob,
                'odds': odds,
                'edge': edge,
                'is_underdog': is_underdog,
                'bet_won': 1 if bet_won else 0,
                'bet_on': bet_on
            })
    
    logger.info(f"Found {len(opportunities)} betting opportunities with {min_edge:.0%}+ edge")
    
    return pd.DataFrame(opportunities)


def analyze_backtest_results(opportunities_df: pd.DataFrame,
                            initial_bankroll: float = 10000) -> Dict:
    """
    Analyze the backtest results
    
    Args:
        opportunities_df: DataFrame with betting opportunities
        initial_bankroll: Starting bankroll
        
    Returns:
        Dictionary with analysis results
    """
    logger.info("\n" + "="*70)
    logger.info("BACKTEST RESULTS - LAST 100 FIGHTS")
    logger.info("="*70)
    
    if len(opportunities_df) == 0:
        logger.warning("No betting opportunities found!")
        return {'has_edge': False, 'reason': 'No bets met criteria'}
    
    # Overall statistics
    total_bets = len(opportunities_df)
    bets_won = opportunities_df['bet_won'].sum()
    win_rate = (bets_won / total_bets) * 100
    
    logger.info(f"\n📊 Overall Statistics:")
    logger.info(f"   Total Bets: {total_bets}")
    logger.info(f"   Bets Won: {bets_won}")
    logger.info(f"   Win Rate: {win_rate:.1f}%")
    logger.info(f"   Average Edge: {opportunities_df['edge'].mean():.2%}")
    
    # Underdog vs Favorite breakdown
    underdogs = opportunities_df[opportunities_df['is_underdog'] == True]
    favorites = opportunities_df[opportunities_df['is_underdog'] == False]
    
    logger.info(f"\n🐕 Underdog Bets:")
    if len(underdogs) > 0:
        logger.info(f"   Count: {len(underdogs)}")
        logger.info(f"   Win Rate: {(underdogs['bet_won'].sum() / len(underdogs)) * 100:.1f}%")
        logger.info(f"   Avg Edge: {underdogs['edge'].mean():.2%}")
    else:
        logger.info("   No underdog bets found")
    
    logger.info(f"\n⭐ Favorite Bets:")
    if len(favorites) > 0:
        logger.info(f"   Count: {len(favorites)}")
        logger.info(f"   Win Rate: {(favorites['bet_won'].sum() / len(favorites)) * 100:.1f}%")
        logger.info(f"   Avg Edge: {favorites['edge'].mean():.2%}")
    else:
        logger.info("   No favorite bets found")
    
    # Simulate actual betting with Kelly Criterion
    logger.info(f"\n💰 Bankroll Simulation (Starting: ${initial_bankroll:,.0f}):")
    
    bankroll = initial_bankroll
    bet_history = []
    
    for _, bet in opportunities_df.iterrows():
        # Convert odds to decimal
        if bet['odds'] < 0:
            decimal_odds = 1 + (100 / abs(bet['odds']))
        else:
            decimal_odds = 1 + (bet['odds'] / 100)
        
        # Kelly Criterion (use 25% Kelly for safety)
        kelly = (decimal_odds * bet['model_prob'] - 1) / (decimal_odds - 1)
        stake_pct = min(kelly * 0.25, 0.05)  # Max 5% of bankroll
        stake = bankroll * stake_pct
        
        # Calculate profit/loss
        if bet['bet_won']:
            profit = stake * (decimal_odds - 1)
        else:
            profit = -stake
        
        bankroll += profit
        
        bet_history.append({
            'event': bet['event'],
            'fighter': bet['fighter'],
            'odds': bet['odds'],
            'edge': bet['edge'],
            'stake': stake,
            'profit': profit,
            'bankroll': bankroll
        })
    
    final_bankroll = bankroll
    total_profit = final_bankroll - initial_bankroll
    roi = (total_profit / initial_bankroll) * 100
    
    logger.info(f"   Final Bankroll: ${final_bankroll:,.2f}")
    logger.info(f"   Total Profit: ${total_profit:,.2f}")
    logger.info(f"   ROI: {roi:.2f}%")
    
    # Calculate max drawdown
    bankrolls = [b['bankroll'] for b in bet_history]
    peak = initial_bankroll
    max_drawdown = 0
    
    for balance in bankrolls:
        if balance > peak:
            peak = balance
        drawdown = ((peak - balance) / peak) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    logger.info(f"   Max Drawdown: {max_drawdown:.1f}%")
    
    # Determine if strategy is profitable
    logger.info("\n" + "="*70)
    
    if roi > 10:
        logger.success("✅ STRONG EDGE DETECTED!")
        logger.success(f"   Your edge-finding system produced {roi:.1f}% ROI")
        logger.success("   Recommendation: Start paper trading with confidence")
    elif roi > 5:
        logger.success("✅ MODERATE EDGE DETECTED")
        logger.info(f"   Your edge-finding system produced {roi:.1f}% ROI")
        logger.info("   Recommendation: Paper trade and continue monitoring")
    elif roi > 0:
        logger.warning("⚠️  MARGINAL EDGE")
        logger.warning(f"   Only {roi:.1f}% ROI - might be luck")
        logger.warning("   Recommendation: Need more data before paper trading")
    else:
        logger.error("❌ NO EDGE DETECTED")
        logger.error(f"   Negative {roi:.1f}% ROI")
        logger.error("   Recommendation: Improve model before betting")
    
    logger.info("="*70)
    
    return {
        'has_edge': roi > 5,
        'roi': roi,
        'win_rate': win_rate,
        'total_bets': total_bets,
        'total_profit': total_profit,
        'max_drawdown': max_drawdown,
        'underdog_count': len(underdogs),
        'favorite_count': len(favorites),
        'bet_history': bet_history
    }


def save_backtest_report(opportunities_df: pd.DataFrame,
                        results: Dict,
                        output_file: str = 'data/backtests/last_100_fights.csv'):
    """
    Save detailed backtest report
    
    Args:
        opportunities_df: Betting opportunities
        results: Analysis results
        output_file: Where to save report
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save opportunities with results
    opportunities_df.to_csv(output_path, index=False)
    logger.info(f"\n💾 Saved backtest report to: {output_path}")
    
    # Save bet history
    bet_history_df = pd.DataFrame(results['bet_history'])
    bet_history_path = output_path.parent / 'last_100_bet_history.csv'
    bet_history_df.to_csv(bet_history_path, index=False)
    logger.info(f"💾 Saved bet history to: {bet_history_path}")
    
    # Save summary
    summary = {
        'backtest_date': datetime.now().isoformat(),
        'n_fights_analyzed': 100,
        'n_betting_opportunities': results['total_bets'],
        'win_rate': results['win_rate'],
        'roi': results['roi'],
        'has_edge': results['has_edge'],
        'total_profit': results['total_profit'],
        'max_drawdown': results['max_drawdown']
    }
    
    summary_path = output_path.parent / 'last_100_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"💾 Saved summary to: {summary_path}")


def main():
    """
    Main execution function
    """
    logger.info("🧪 Backtesting Last 100 Fights - Edge Validation\n")
    
    # Step 1: Load recent fights
    fights_df = load_recent_fights(n_fights=100)
    
    if len(fights_df) == 0:
        logger.error("No fights found in database!")
        logger.info("Run the scrapers first to populate fight data")
        return
    
    # Step 2: Generate model predictions
    predictions_df = get_model_predictions(fights_df)
    
    # Step 3: Get historical odds
    odds_df = get_historical_odds(fights_df)
    
    # Step 4: Identify edge opportunities
    opportunities_df = identify_edge_opportunities(
        predictions_df, 
        odds_df,
        min_edge=0.05  # 5% minimum edge
    )
    
    if len(opportunities_df) == 0:
        logger.warning("\n⚠️  No betting opportunities found!")
        logger.info("This means your model rarely disagrees with the market by 5%+")
        logger.info("Try lowering min_edge to 0.03 (3%) or improve model")
        return
    
    # Step 5: Analyze results
    results = analyze_backtest_results(opportunities_df)
    
    # Step 6: Save report
    save_backtest_report(opportunities_df, results)
    
    # Step 7: Show best bets
    logger.info("\n🎯 Top 5 Highest-Edge Bets:")
    top_bets = opportunities_df.nlargest(5, 'edge')
    for _, bet in top_bets.iterrows():
        result = "✅ WON" if bet['bet_won'] else "❌ LOST"
        logger.info(f"   {bet['fighter']} ({bet['odds']:+d}) - Edge: {bet['edge']:.1%} - {result}")
    
    # Step 8: Next steps
    logger.info("\n" + "="*70)
    logger.info("📋 NEXT STEPS:")
    logger.info("="*70)
    
    if results['has_edge']:
        logger.info("""
1. ✅ Your edge-detection system works on historical data!
2. 🧪 Start paper trading upcoming fights
3. 📊 Track every prediction vs actual odds
4. 💰 Only bet when edge > 5% (selective!)
5. 📈 After 50 paper trades, reassess
6. 💵 If still profitable, consider small real money bets

Remember: Past performance doesn't guarantee future results!
        """)
    else:
        logger.info("""
1. ⚠️  No edge detected in last 100 fights
2. 🔧 Options:
   - Improve your model (more features, better training)
   - Lower edge threshold (try 3% instead of 5%)
   - Focus on specific scenarios (underdogs only, certain weight classes)
3. 🧪 Don't paper trade yet - improve model first
4. 📚 Use project for learning/portfolio instead
        """)


if __name__ == '__main__':
    main()

