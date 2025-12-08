#!/usr/bin/env python3
"""
Paper Trading Tracker - Track Your Forward-Looking Bets

Use this to track predictions on UPCOMING fights (paper trading)
while you validate your system on historical fights (backtesting).

This helps you see if your edge-finding system works in real-time.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from loguru import logger
import json

from scripts.validate_edge import calculate_edge


class PaperTradingTracker:
    """Track paper trades and calculate results"""
    
    def __init__(self, bankroll: float = 10000, tracker_file: str = 'data/paper_trades/trades.json'):
        self.initial_bankroll = bankroll
        self.current_bankroll = bankroll
        self.tracker_file = Path(tracker_file)
        self.trades = self._load_trades()
    
    def _load_trades(self) -> list:
        """Load existing trades"""
        if self.tracker_file.exists():
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
                self.current_bankroll = data.get('current_bankroll', self.initial_bankroll)
                return data.get('trades', [])
        return []
    
    def _save_trades(self):
        """Save trades to file"""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'initial_bankroll': self.initial_bankroll,
            'current_bankroll': self.current_bankroll,
            'trades': self.trades,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_prediction(self, 
                      event: str,
                      fighter: str,
                      opponent: str,
                      model_prob: float,
                      bookmaker_odds: int,
                      notes: str = "") -> Dict:
        """
        Add a new paper trade prediction
        
        Args:
            event: Event name (e.g., "UFC 320")
            fighter: Fighter you're betting on
            opponent: Opponent
            model_prob: Your model's win probability (0-1)
            bookmaker_odds: Current odds (American format, e.g., +150, -200)
            notes: Optional notes about the prediction
            
        Returns:
            Trade details
        """
        # Calculate edge
        edge = calculate_edge(model_prob, bookmaker_odds)
        
        # Determine if this is a bet or just tracking
        is_bet = edge >= 0.05  # 5% minimum edge
        
        # Calculate stake using Kelly Criterion
        if is_bet:
            if bookmaker_odds < 0:
                decimal_odds = 1 + (100 / abs(bookmaker_odds))
            else:
                decimal_odds = 1 + (bookmaker_odds / 100)
            
            kelly = (decimal_odds * model_prob - 1) / (decimal_odds - 1)
            stake_pct = min(kelly * 0.25, 0.05)  # 25% Kelly, max 5%
            stake = self.current_bankroll * stake_pct
        else:
            stake = 0
        
        trade = {
            'id': len(self.trades) + 1,
            'date_added': datetime.now().isoformat(),
            'event': event,
            'fighter': fighter,
            'opponent': opponent,
            'model_prob': model_prob,
            'bookmaker_odds': bookmaker_odds,
            'edge': edge,
            'is_bet': is_bet,
            'stake': stake,
            'status': 'pending',
            'result': None,
            'profit': None,
            'notes': notes
        }
        
        self.trades.append(trade)
        self._save_trades()
        
        # Log the prediction
        if is_bet:
            logger.success(f"✅ PAPER BET #{trade['id']}: {fighter} ({bookmaker_odds:+d})")
            logger.info(f"   Edge: {edge:.1%} | Stake: ${stake:.2f} ({stake_pct:.1%} of bankroll)")
        else:
            logger.info(f"📝 TRACKED #{trade['id']}: {fighter} ({bookmaker_odds:+d})")
            logger.info(f"   Edge: {edge:.1%} (below threshold, not betting)")
        
        return trade
    
    def update_result(self, trade_id: int, fighter_won: bool):
        """
        Update a paper trade with actual result
        
        Args:
            trade_id: Trade ID
            fighter_won: True if your fighter won, False if lost
        """
        trade = next((t for t in self.trades if t['id'] == trade_id), None)
        
        if not trade:
            logger.error(f"Trade #{trade_id} not found!")
            return
        
        if trade['status'] != 'pending':
            logger.warning(f"Trade #{trade_id} already settled!")
            return
        
        trade['result'] = 'won' if fighter_won else 'lost'
        trade['status'] = 'settled'
        trade['date_settled'] = datetime.now().isoformat()
        
        # Calculate profit/loss
        if trade['is_bet']:
            if fighter_won:
                if trade['bookmaker_odds'] < 0:
                    profit = trade['stake'] * (100 / abs(trade['bookmaker_odds']))
                else:
                    profit = trade['stake'] * (trade['bookmaker_odds'] / 100)
            else:
                profit = -trade['stake']
            
            trade['profit'] = profit
            self.current_bankroll += profit
            
            result_str = "✅ WON" if fighter_won else "❌ LOST"
            logger.info(f"{result_str} - Trade #{trade_id}: {trade['fighter']}")
            logger.info(f"   Profit: ${profit:+,.2f} | New Bankroll: ${self.current_bankroll:,.2f}")
        else:
            trade['profit'] = 0
            logger.info(f"📝 Result tracked for #{trade_id}: {trade['fighter']} {trade['result']}")
        
        self._save_trades()
        self._check_milestone()
    
    def _check_milestone(self):
        """Check if we've hit a milestone (25, 50, 100 trades)"""
        settled = [t for t in self.trades if t['status'] == 'settled' and t['is_bet']]
        n = len(settled)
        
        if n in [25, 50, 100]:
            logger.success(f"\n🎯 MILESTONE: {n} Paper Trades Completed!")
            self.show_summary()
    
    def show_summary(self):
        """Show current paper trading performance"""
        settled = [t for t in self.trades if t['status'] == 'settled' and t['is_bet']]
        
        if not settled:
            logger.info("No settled trades yet")
            return
        
        n_trades = len(settled)
        n_won = sum(1 for t in settled if t['result'] == 'won')
        win_rate = (n_won / n_trades) * 100
        
        total_profit = self.current_bankroll - self.initial_bankroll
        roi = (total_profit / self.initial_bankroll) * 100
        
        avg_edge = sum(t['edge'] for t in settled) / n_trades
        
        logger.info("\n" + "="*60)
        logger.info("📊 PAPER TRADING SUMMARY")
        logger.info("="*60)
        logger.info(f"Trades Settled: {n_trades}")
        logger.info(f"Wins: {n_won} ({win_rate:.1f}%)")
        logger.info(f"Losses: {n_trades - n_won}")
        logger.info(f"Average Edge: {avg_edge:.1%}")
        logger.info(f"")
        logger.info(f"Initial Bankroll: ${self.initial_bankroll:,.2f}")
        logger.info(f"Current Bankroll: ${self.current_bankroll:,.2f}")
        logger.info(f"Total Profit: ${total_profit:+,.2f}")
        logger.info(f"ROI: {roi:+.2f}%")
        logger.info("="*60)
        
        if n_trades >= 50:
            if roi > 5:
                logger.success("\n✅ Profitable after 50+ trades!")
                logger.success("Consider moving to small real-money bets")
            elif roi > 0:
                logger.warning("\n⚠️  Marginally profitable")
                logger.warning("Continue paper trading to 100 bets")
            else:
                logger.error("\n❌ Not profitable")
                logger.error("Improve model before real money")
    
    def show_pending(self):
        """Show pending predictions"""
        pending = [t for t in self.trades if t['status'] == 'pending']
        
        if not pending:
            logger.info("No pending predictions")
            return
        
        logger.info("\n📋 Pending Predictions:")
        for trade in pending:
            bet_str = "💰" if trade['is_bet'] else "📝"
            logger.info(f"{bet_str} #{trade['id']}: {trade['fighter']} ({trade['bookmaker_odds']:+d}) - {trade['event']}")
    
    def export_to_csv(self, output_file: str = 'data/paper_trades/paper_trades.csv'):
        """Export trades to CSV for analysis"""
        df = pd.DataFrame(self.trades)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"💾 Exported to {output_path}")


def main():
    """
    Interactive paper trading tracker
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Paper Trading Tracker')
    parser.add_argument('--add', action='store_true', help='Add new prediction')
    parser.add_argument('--update', type=int, help='Update trade result (trade ID)')
    parser.add_argument('--won', action='store_true', help='Fighter won (use with --update)')
    parser.add_argument('--summary', action='store_true', help='Show summary')
    parser.add_argument('--pending', action='store_true', help='Show pending trades')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    
    # For adding new predictions
    parser.add_argument('--event', type=str, help='Event name')
    parser.add_argument('--fighter', type=str, help='Fighter name')
    parser.add_argument('--opponent', type=str, help='Opponent name')
    parser.add_argument('--prob', type=float, help='Model probability (0-1)')
    parser.add_argument('--odds', type=int, help='Bookmaker odds')
    parser.add_argument('--notes', type=str, default='', help='Optional notes')
    
    args = parser.parse_args()
    
    tracker = PaperTradingTracker()
    
    if args.add:
        if not all([args.event, args.fighter, args.opponent, args.prob, args.odds]):
            logger.error("Must provide: --event --fighter --opponent --prob --odds")
            return
        
        tracker.add_prediction(
            event=args.event,
            fighter=args.fighter,
            opponent=args.opponent,
            model_prob=args.prob,
            bookmaker_odds=args.odds,
            notes=args.notes
        )
    
    elif args.update:
        if args.won is None:
            logger.error("Must specify --won (use --won for win, omit for loss)")
            return
        
        tracker.update_result(args.update, args.won)
    
    elif args.summary:
        tracker.show_summary()
    
    elif args.pending:
        tracker.show_pending()
    
    elif args.export:
        tracker.export_to_csv()
    
    else:
        # Default: show pending and summary
        tracker.show_pending()
        tracker.show_summary()


if __name__ == '__main__':
    main()

