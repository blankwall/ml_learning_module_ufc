#!/usr/bin/env python3
"""
Analyze betting odds spreads and win rates.

Answers questions like:
- What's the win rate for close-to-even odds vs wide spreads?
- How do favorites vs underdogs perform at different spread levels?
- What's the distribution of odds spreads in 2025?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight, Event
from sqlalchemy import or_, and_
from loguru import logger
import argparse


def american_to_prob(odds: float) -> float:
    """Convert American odds to implied probability."""
    if pd.isna(odds):
        return np.nan
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return abs(odds) / (abs(odds) + 100.0)


def calculate_odds_spread(fighter1_odds: float, fighter2_odds: float) -> float:
    """
    Calculate the odds spread (difference in implied probabilities).
    
    Returns the absolute difference between the two implied probabilities.
    A spread of 0.0 means even odds (50/50), higher spread = more lopsided.
    """
    prob1 = american_to_prob(fighter1_odds)
    prob2 = american_to_prob(fighter2_odds)
    
    if pd.isna(prob1) or pd.isna(prob2):
        return np.nan
    
    return abs(prob1 - prob2)


def normalize_name(name: str) -> str:
    """Normalize fighter name for matching."""
    if pd.isna(name):
        return ""
    return str(name).strip().lower().replace("'", "").replace(".", "")


def load_odds_with_results(odds_path: Path, db: DatabaseManager) -> pd.DataFrame:
    """Load odds CSV and match with actual fight results from database."""
    logger.info(f"Loading odds from {odds_path}...")
    df = pd.read_csv(odds_path)
    
    # Parse dates
    df['event_date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['event_date'])
    
    # Normalize fighter names
    df['f1_name_norm'] = df['fighter1'].apply(normalize_name)
    df['f2_name_norm'] = df['fighter2'].apply(normalize_name)
    
    # Calculate odds spreads and implied probabilities
    df['f1_prob'] = df['fighter1_odds'].apply(american_to_prob)
    df['f2_prob'] = df['fighter2_odds'].apply(american_to_prob)
    df['odds_spread'] = df.apply(
        lambda r: calculate_odds_spread(r['fighter1_odds'], r['fighter2_odds']), axis=1
    )
    
    # Determine favorite/underdog
    df['f1_is_favorite'] = df['fighter1_odds'] < df['fighter2_odds']
    df['f2_is_favorite'] = ~df['f1_is_favorite']
    
    # Match with database results
    session = db.get_session()
    try:
        results = []
        
        for idx, row in df.iterrows():
            # Find fighters
            f1 = session.query(Fighter).filter(
                Fighter.name.ilike(f"%{row['fighter1']}%")
            ).first()
            f2 = session.query(Fighter).filter(
                Fighter.name.ilike(f"%{row['fighter2']}%")
            ).first()
            
            if not f1 or not f2:
                results.append({
                    'matched': False,
                    'f1_won': None,
                    'f2_won': None,
                })
                continue
            
            # Find fight on this date (within ±3 days for timezone issues)
            event_date = row['event_date']
            date_start = (event_date - pd.Timedelta(days=3)).strftime('%B %d, %Y')
            date_end = (event_date + pd.Timedelta(days=3)).strftime('%B %d, %Y')
            
            # Get all events in date range (Event.date is stored as string like "January 18, 2025")
            events_in_range = session.query(Event).filter(
                Event.date >= date_start,
                Event.date <= date_end
            ).all()
            event_ids = [e.id for e in events_in_range]
            
            if not event_ids:
                results.append({
                    'matched': False,
                    'f1_won': None,
                    'f2_won': None,
                })
                continue
            
            fight = session.query(Fight).filter(
                and_(
                    or_(
                        and_(Fight.fighter_1_id == f1.id, Fight.fighter_2_id == f2.id),
                        and_(Fight.fighter_1_id == f2.id, Fight.fighter_2_id == f1.id)
                    ),
                    Fight.event_id.in_(event_ids)
                )
            ).first()
            
            if not fight:
                results.append({
                    'matched': False,
                    'f1_won': None,
                    'f2_won': None,
                })
                continue
            
            # Determine winner
            f1_won = (fight.winner_id == f1.id) if fight.winner_id else None
            f2_won = (fight.winner_id == f2.id) if fight.winner_id else None
            
            results.append({
                'matched': True,
                'f1_won': f1_won,
                'f2_won': f2_won,
            })
        
        results_df = pd.DataFrame(results)
        df = pd.concat([df, results_df], axis=1)
        
        matched_count = df['matched'].sum()
        logger.info(f"Matched {matched_count}/{len(df)} fights with results")
        
    finally:
        session.close()
    
    return df


def analyze_spreads(df: pd.DataFrame):
    """Analyze win rates by odds spread."""
    # Filter to matched fights only
    df_matched = df[df['matched'] == True].copy()
    
    if len(df_matched) == 0:
        logger.error("No matched fights found. Cannot analyze.")
        return
    
    # Determine winner (f1 or f2)
    df_matched['f1_won'] = df_matched['f1_won'].fillna(False)
    df_matched['f2_won'] = df_matched['f2_won'].fillna(False)
    
    # Calculate favorite win
    df_matched['favorite_won'] = np.where(
        df_matched['f1_is_favorite'],
        df_matched['f1_won'],
        df_matched['f2_won']
    )
    df_matched['underdog_won'] = ~df_matched['favorite_won']
    
    print("\n" + "="*80)
    print("ODDS SPREAD ANALYSIS")
    print("="*80)
    
    # Overall stats
    total_fights = len(df_matched)
    favorite_wins = df_matched['favorite_won'].sum()
    underdog_wins = df_matched['underdog_won'].sum()
    
    print(f"\nOverall Statistics:")
    print(f"  Total fights analyzed: {total_fights}")
    print(f"  Favorite wins: {favorite_wins} ({favorite_wins/total_fights:.1%})")
    print(f"  Underdog wins: {underdog_wins} ({underdog_wins/total_fights:.1%})")
    
    # Define spread buckets
    spread_buckets = [
        (0.0, 0.05, "Even (0-5% spread)"),
        (0.05, 0.10, "Close (5-10% spread)"),
        (0.10, 0.20, "Moderate (10-20% spread)"),
        (0.20, 0.30, "Wide (20-30% spread)"),
        (0.30, 1.0, "Very Wide (30%+ spread)"),
    ]
    
    print(f"\n{'='*80}")
    print("WIN RATES BY ODDS SPREAD")
    print(f"{'='*80}")
    print(f"{'Spread Range':<25} {'Fights':<10} {'Fav Win%':<12} {'Dog Win%':<12} {'Fav W':<8} {'Dog W':<8}")
    print("-"*80)
    
    for min_spread, max_spread, label in spread_buckets:
        bucket = df_matched[
            (df_matched['odds_spread'] >= min_spread) & 
            (df_matched['odds_spread'] < max_spread)
        ]
        
        if len(bucket) == 0:
            print(f"{label:<25} {'0':<10} {'N/A':<12} {'N/A':<12} {'0':<8} {'0':<8}")
            continue
        
        fav_wins = bucket['favorite_won'].sum()
        dog_wins = bucket['underdog_won'].sum()
        total = len(bucket)
        
        fav_win_rate = fav_wins / total if total > 0 else 0
        dog_win_rate = dog_wins / total if total > 0 else 0
        
        print(f"{label:<25} {total:<10} {fav_win_rate:>10.1%} {dog_win_rate:>10.1%} {fav_wins:<8} {dog_wins:<8}")
    
    # Detailed breakdown for close-to-even odds (your betting strategy)
    print(f"\n{'='*80}")
    print("CLOSE-TO-EVEN ODDS ANALYSIS (Your Betting Strategy)")
    print(f"{'='*80}")
    
    close_odds = df_matched[df_matched['odds_spread'] < 0.10].copy()
    
    if len(close_odds) > 0:
        print(f"\nFights with <10% odds spread (close to even):")
        print(f"  Total: {len(close_odds)}")
        print(f"  Favorite win rate: {close_odds['favorite_won'].mean():.1%}")
        print(f"  Underdog win rate: {close_odds['underdog_won'].mean():.1%}")
        
        # Break down by even smaller ranges
        even_closer = close_odds[close_odds['odds_spread'] < 0.05]
        if len(even_closer) > 0:
            print(f"\n  Very close (<5% spread): {len(even_closer)} fights")
            print(f"    Favorite win rate: {even_closer['favorite_won'].mean():.1%}")
            print(f"    Underdog win rate: {even_closer['underdog_won'].mean():.1%}")
        
        moderate_close = close_odds[(close_odds['odds_spread'] >= 0.05) & (close_odds['odds_spread'] < 0.10)]
        if len(moderate_close) > 0:
            print(f"\n  Moderately close (5-10% spread): {len(moderate_close)} fights")
            print(f"    Favorite win rate: {moderate_close['favorite_won'].mean():.1%}")
            print(f"    Underdog win rate: {moderate_close['underdog_won'].mean():.1%}")
    else:
        print("  No fights with <10% spread found")
    
    # Distribution of spreads
    print(f"\n{'='*80}")
    print("ODDS SPREAD DISTRIBUTION")
    print(f"{'='*80}")
    print(f"Mean spread: {df_matched['odds_spread'].mean():.3f}")
    print(f"Median spread: {df_matched['odds_spread'].median():.3f}")
    print(f"Min spread: {df_matched['odds_spread'].min():.3f}")
    print(f"Max spread: {df_matched['odds_spread'].max():.3f}")
    print(f"\nSpread percentiles:")
    for p in [10, 25, 50, 75, 90]:
        val = df_matched['odds_spread'].quantile(p/100)
        print(f"  {p}th percentile: {val:.3f}")
    
    # Win rate by favorite odds range
    print(f"\n{'='*80}")
    print("WIN RATE BY FAVORITE ODDS (American)")
    print(f"{'='*80}")
    
    # Convert to absolute value for favorite odds
    df_matched['favorite_odds_abs'] = np.where(
        df_matched['f1_is_favorite'],
        df_matched['fighter1_odds'].abs(),
        df_matched['fighter2_odds'].abs()
    )
    
    favorite_buckets = [
        (-np.inf, 110, "Pick'em to -110"),
        (110, 150, "-110 to -150"),
        (150, 200, "-150 to -200"),
        (200, 300, "-200 to -300"),
        (300, np.inf, "-300+ (heavy favorite)"),
    ]
    
    print(f"{'Favorite Odds Range':<25} {'Fights':<10} {'Win Rate':<12} {'Wins':<8}")
    print("-"*80)
    
    for min_odds, max_odds, label in favorite_buckets:
        bucket = df_matched[
            (df_matched['favorite_odds_abs'] > min_odds) & 
            (df_matched['favorite_odds_abs'] <= max_odds)
        ]
        
        if len(bucket) == 0:
            print(f"{label:<25} {'0':<10} {'N/A':<12} {'0':<8}")
            continue
        
        wins = bucket['favorite_won'].sum()
        total = len(bucket)
        win_rate = wins / total if total > 0 else 0
        
        print(f"{label:<25} {total:<10} {win_rate:>10.1%} {wins:<8}")
    
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print(f"{'='*80}")
    close_spread_win_rate = close_odds['favorite_won'].mean() if len(close_odds) > 0 else None
    overall_win_rate = df_matched['favorite_won'].mean()
    
    if close_spread_win_rate is not None:
        print(f"\nYour strategy (close-to-even odds):")
        print(f"  Favorite win rate in close fights: {close_spread_win_rate:.1%}")
        print(f"  Overall favorite win rate: {overall_win_rate:.1%}")
        
        if close_spread_win_rate < overall_win_rate:
            print(f"\n  ✓ Your intuition is CORRECT: Close fights are more unpredictable!")
            print(f"    Favorites win {overall_win_rate - close_spread_win_rate:.1%} less often in close fights.")
        else:
            print(f"\n  ⚠️  Close fights don't show lower favorite win rate in this data.")
    
    print(f"\nRecommendation:")
    print(f"  - Close-to-even odds (<10% spread) have {len(close_odds)} fights")
    print(f"  - This represents {len(close_odds)/len(df_matched):.1%} of all fights")
    print(f"  - Consider focusing on this range for more balanced matchups")


def main():
    parser = argparse.ArgumentParser(description='Analyze betting odds spreads and win rates')
    parser.add_argument('--odds-file', type=str, default='ufc_2025_odds.csv',
                        help='Path to odds CSV file')
    parser.add_argument('--output', type=str, default=None,
                        help='Optional: Save detailed results to CSV')
    
    args = parser.parse_args()
    
    odds_path = Path(args.odds_file)
    if not odds_path.exists():
        logger.error(f"Odds file not found: {odds_path}")
        return
    
    db = DatabaseManager()
    
    try:
        df = load_odds_with_results(odds_path, db)
        
        if args.output:
            df.to_csv(args.output, index=False)
            logger.info(f"Saved detailed results to {args.output}")
        
        analyze_spreads(df)
        
    finally:
        pass  # db doesn't need explicit close


if __name__ == '__main__':
    main()

