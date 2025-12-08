"""
Matchup Feature Extraction - Creates features comparing two fighters

REFACTORED: Now works with the new modular feature system.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from database.schema import Fighter, Fight
from .fighter_features import FighterFeatureExtractor
from .registry import FeatureRegistry


class MatchupFeatureExtractor:
    """Extract features for a specific fight matchup"""
    
    def __init__(self, session: Session):
        """Initialize matchup feature extractor"""
        self.session = session
        self.fighter_extractor = FighterFeatureExtractor(session)
    
    def extract_matchup_features(
        self,
        fighter_1_id: int,
        fighter_2_id: int,
        as_of_date: Optional[datetime] = None,
        feature_set: Optional[List[str]] = None
    ) -> Dict:
        """
        Extract features for a matchup between two fighters
        
        Args:
            fighter_1_id: First fighter database ID
            fighter_2_id: Second fighter database ID
            as_of_date: Calculate features as of this date
            feature_set: Optional list of feature names to extract.
                        If None, uses FEATURE_SET_FULL (all features)
            
        Returns:
            Dictionary with matchup features
        """
        # Get individual fighter features
        f1_features = self.fighter_extractor.extract_features(
            fighter_1_id, as_of_date, feature_set=feature_set
        )
        f2_features = self.fighter_extractor.extract_features(
            fighter_2_id, as_of_date, feature_set=feature_set
        )
        
        matchup_features = {}
        
        # Add individual features with prefixes
        for key, value in f1_features.items():
            matchup_features[f'f1_{key}'] = value
        
        for key, value in f2_features.items():
            matchup_features[f'f2_{key}'] = value
        
        # Add differential features
        matchup_features.update(self._calculate_differentials(f1_features, f2_features))
        
        # Add style matchup features
        matchup_features.update(self._calculate_style_matchup(f1_features, f2_features))
        
        # Add common opponent analysis
        matchup_features.update(self._calculate_common_opponents(fighter_1_id, fighter_2_id, as_of_date))
        
        return matchup_features
    
    def _calculate_differentials(self, f1_features: Dict, f2_features: Dict) -> Dict:
        """Calculate differential features (advantages)"""
        differentials = {}
        
        # Physical advantages
        differentials['height_advantage'] = f1_features.get('height_cm', 0) - f2_features.get('height_cm', 0)
        differentials['reach_advantage'] = f1_features.get('reach_inches', 0) - f2_features.get('reach_inches', 0)
        differentials['age_difference'] = f1_features.get('age', 0) - f2_features.get('age', 0)
        
        # Experience advantages
        differentials['experience_difference'] = f1_features.get('total_fights', 0) - f2_features.get('total_fights', 0)
        # Note: win_rate is intentionally omitted from career_stats to force model
        # to use opponent-quality and recent rolling win rates instead
        # differentials['win_rate_difference'] = f1_features.get('win_rate', 0) - f2_features.get('win_rate', 0)
        
        # Striking advantages
        differentials['striking_output_diff'] = (
            f1_features.get('sig_strikes_landed_per_min', 0) - f2_features.get('sig_strikes_landed_per_min', 0)
        )
        differentials['striking_accuracy_diff'] = (
            f1_features.get('striking_accuracy', 0) - f2_features.get('striking_accuracy', 0)
        )
        differentials['striking_defense_diff'] = (
            f1_features.get('striking_defense', 0) - f2_features.get('striking_defense', 0)
        )
        # Striking differential: F1 output vs F2 defense (interaction feature)
        differentials['striking_differential'] = (
            f1_features.get('sig_strikes_landed_per_min', 0) - f2_features.get('striking_defense', 0)
        )
        
        # Grappling advantages
        differentials['takedown_ability_diff'] = (
            f1_features.get('takedown_avg_per_15min', 0) - f2_features.get('takedown_avg_per_15min', 0)
        )
        differentials['takedown_defense_diff'] = (
            f1_features.get('takedown_defense', 0) - f2_features.get('takedown_defense', 0)
        )
        # Takedown matchup: F1 accuracy vs F2 defense (interaction feature)
        differentials['takedown_matchup'] = (
            f1_features.get('takedown_accuracy', 0) - f2_features.get('takedown_defense', 0)
        )
        
        # Recent form
        differentials['recent_form_diff'] = (
            f1_features.get('win_rate_last_3', 0) - f2_features.get('win_rate_last_3', 0)
        )
        differentials['win_streak_diff'] = (
            f1_features.get('current_win_streak', 0) - f2_features.get('current_win_streak', 0)
        )
        
        # Finish rate
        differentials['finish_rate_diff'] = (
            f1_features.get('finish_rate', 0) - f2_features.get('finish_rate', 0)
        )
        
        # Round 3 performance (cardio proxy)
        differentials['round_3_performance_diff'] = (
            f1_features.get('round_3_performance_score', 0) - f2_features.get('round_3_performance_score', 0)
        )
        differentials['round_3_win_rate_diff'] = (
            f1_features.get('round_3_win_rate', 0) - f2_features.get('round_3_win_rate', 0)
        )

        # Strength-of-schedule / opponent-quality differentials
        differentials['avg_opponent_win_rate_diff'] = (
            f1_features.get('avg_opponent_win_rate', 0) - f2_features.get('avg_opponent_win_rate', 0)
        )
        differentials['avg_beaten_opponent_win_rate_diff'] = (
            f1_features.get('avg_beaten_opponent_win_rate', 0) - f2_features.get('avg_beaten_opponent_win_rate', 0)
        )
        differentials['opponent_quality_score_diff'] = (
            f1_features.get('opponent_quality_score', 0) - f2_features.get('opponent_quality_score', 0)
        )

        # Longer-horizon decline / slump differentials
        differentials['fights_since_last_win_diff'] = (
            f1_features.get('fights_since_last_win', 0) - f2_features.get('fights_since_last_win', 0)
        )
        differentials['years_since_last_win_diff'] = (
            f1_features.get('years_since_last_win', 0.0) - f2_features.get('years_since_last_win', 0.0)
        )
        differentials['has_ever_won_diff'] = (
            f1_features.get('has_ever_won', 0) - f2_features.get('has_ever_won', 0)
        )
        differentials['losses_since_last_win_diff'] = (
            f1_features.get('losses_since_last_win', 0) - f2_features.get('losses_since_last_win', 0)
        )
        differentials['decision_losses_since_last_win_diff'] = (
            f1_features.get('decision_losses_since_last_win', 0) - f2_features.get('decision_losses_since_last_win', 0)
        )
        differentials['finish_losses_since_last_win_diff'] = (
            f1_features.get('finish_losses_since_last_win', 0) - f2_features.get('finish_losses_since_last_win', 0)
        )
        differentials['recent_vs_career_win_rate_diff'] = (
            f1_features.get('recent_vs_career_win_rate', 0.0) - f2_features.get('recent_vs_career_win_rate', 0.0)
        )

        # Very recent damage / decline indicators
        differentials['recent_finish_losses_last_2_diff'] = (
            f1_features.get('recent_finish_losses_last_2', 0) - f2_features.get('recent_finish_losses_last_2', 0)
        )
        differentials['recent_finish_loss_last_fight_diff'] = (
            f1_features.get('recent_finish_loss_last_fight', 0) - f2_features.get('recent_finish_loss_last_fight', 0)
        )
        differentials['recent_finish_loss_ratio_last_2_diff'] = (
            f1_features.get('recent_finish_loss_ratio_last_2', 0.0) - f2_features.get('recent_finish_loss_ratio_last_2', 0.0)
        )

        # Recent detailed stats (FightStats-based) – striking and knockdowns
        differentials['recent_sig_strike_diff_last_3_diff'] = (
            f1_features.get('recent_sig_strike_diff_last_3', 0.0) - f2_features.get('recent_sig_strike_diff_last_3', 0.0)
        )
        differentials['recent_knockdown_diff_last_3_diff'] = (
            f1_features.get('recent_knockdown_diff_last_3', 0.0) - f2_features.get('recent_knockdown_diff_last_3', 0.0)
        )

        # Recent control time / grappling dominance (last ~3 fights)
        differentials['recent_control_time_sec_last_3_diff'] = (
            f1_features.get('recent_control_time_sec_last_3', 0.0) - f2_features.get('recent_control_time_sec_last_3', 0.0)
        )
        differentials['recent_control_time_diff_last_3_diff'] = (
            f1_features.get('recent_control_time_diff_last_3', 0.0) - f2_features.get('recent_control_time_diff_last_3', 0.0)
        )

        # Time-windowed recency and layoff / activity differentials
        differentials['win_rate_last_3_years_diff'] = (
            f1_features.get('win_rate_last_3_years', 0.0) - f2_features.get('win_rate_last_3_years', 0.0)
        )
        differentials['wins_last_3_years_diff'] = (
            f1_features.get('wins_last_3_years', 0) - f2_features.get('wins_last_3_years', 0)
        )
        differentials['losses_last_3_years_diff'] = (
            f1_features.get('losses_last_3_years', 0) - f2_features.get('losses_last_3_years', 0)
        )
        differentials['finish_rate_last_3_years_diff'] = (
            f1_features.get('finish_rate_last_3_years', 0.0) - f2_features.get('finish_rate_last_3_years', 0.0)
        )
        differentials['long_layoff_over_1yr_diff'] = (
            f1_features.get('long_layoff_over_1yr', 0) - f2_features.get('long_layoff_over_1yr', 0)
        )
        differentials['long_layoff_over_2yr_diff'] = (
            f1_features.get('long_layoff_over_2yr', 0) - f2_features.get('long_layoff_over_2yr', 0)
        )

        # Early-finish / KO-power profile differentials
        differentials['first_round_finish_rate_diff'] = (
            f1_features.get('first_round_finish_rate', 0.0) - f2_features.get('first_round_finish_rate', 0.0)
        )
        differentials['first_round_ko_rate_diff'] = (
            f1_features.get('first_round_ko_rate', 0.0) - f2_features.get('first_round_ko_rate', 0.0)
        )
        differentials['early_finish_rate_last_3_diff'] = (
            f1_features.get('early_finish_rate_last_3', 0.0) - f2_features.get('early_finish_rate_last_3', 0.0)
        )
        differentials['early_finish_rate_last_5_diff'] = (
            f1_features.get('early_finish_rate_last_5', 0.0) - f2_features.get('early_finish_rate_last_5', 0.0)
        )

        # Youth + recent form profile (young surging prospect vs older vet)
        differentials['youth_form_score_diff'] = (
            f1_features.get('youth_form_score', 0.0) - f2_features.get('youth_form_score', 0.0)
        )

        # Time-decayed performance differentials (recent performance weighted more heavily)
        differentials['time_decayed_win_rate_diff'] = (
            f1_features.get('time_decayed_win_rate', 0.0) - f2_features.get('time_decayed_win_rate', 0.0)
        )
        differentials['time_decayed_finish_rate_diff'] = (
            f1_features.get('time_decayed_finish_rate', 0.0) - f2_features.get('time_decayed_finish_rate', 0.0)
        )
        differentials['time_decayed_ko_rate_diff'] = (
            f1_features.get('time_decayed_ko_rate', 0.0) - f2_features.get('time_decayed_ko_rate', 0.0)
        )

        # Age × decline interaction differentials (makes decline worse for older fighters)
        differentials['age_x_years_since_last_win_diff'] = (
            f1_features.get('age_x_years_since_last_win', 0.0) - f2_features.get('age_x_years_since_last_win', 0.0)
        )
        differentials['age_x_fights_since_last_win_diff'] = (
            f1_features.get('age_x_fights_since_last_win', 0.0) - f2_features.get('age_x_fights_since_last_win', 0.0)
        )
        differentials['age_x_recent_vs_career_decline_diff'] = (
            f1_features.get('age_x_recent_vs_career_decline', 0.0) - f2_features.get('age_x_recent_vs_career_decline', 0.0)
        )

        # Age × activity interaction differentials (makes inactivity worse for older fighters)
        differentials['age_x_days_since_last_fight_diff'] = (
            f1_features.get('age_x_days_since_last_fight', 0.0) - f2_features.get('age_x_days_since_last_fight', 0.0)
        )
        differentials['age_x_years_since_last_fight_diff'] = (
            f1_features.get('age_x_years_since_last_fight', 0.0) - f2_features.get('age_x_years_since_last_fight', 0.0)
        )
        differentials['age_x_fights_in_last_year_diff'] = (
            f1_features.get('age_x_fights_in_last_year', 0.0) - f2_features.get('age_x_fights_in_last_year', 0.0)
        )
        
        return differentials
    
    def _calculate_style_matchup(self, f1_features: Dict, f2_features: Dict) -> Dict:
        """Calculate style matchup indicators"""
        matchup = {}
        
        # Striker vs Striker
        f1_striker = f1_features.get('sig_strikes_landed_per_min', 0) > f1_features.get('takedown_avg_per_15min', 0)
        f2_striker = f2_features.get('sig_strikes_landed_per_min', 0) > f2_features.get('takedown_avg_per_15min', 0)
        matchup['both_strikers'] = 1 if (f1_striker and f2_striker) else 0
        
        # Grappler vs Grappler
        f1_grappler = f1_features.get('takedown_avg_per_15min', 0) > 2.0
        f2_grappler = f2_features.get('takedown_avg_per_15min', 0) > 2.0
        matchup['both_grapplers'] = 1 if (f1_grappler and f2_grappler) else 0
        
        # Striker vs Grappler
        matchup['striker_vs_grappler'] = 1 if (f1_striker and f2_grappler) or (f1_grappler and f2_striker) else 0
        
        # Stance matchup
        f1_orthodox = f1_features.get('stance_orthodox', 0)
        f2_orthodox = f2_features.get('stance_orthodox', 0)
        f1_southpaw = f1_features.get('stance_southpaw', 0)
        f2_southpaw = f2_features.get('stance_southpaw', 0)
        
        matchup['orthodox_vs_orthodox'] = 1 if (f1_orthodox and f2_orthodox) else 0
        matchup['southpaw_vs_southpaw'] = 1 if (f1_southpaw and f2_southpaw) else 0
        matchup['orthodox_vs_southpaw'] = 1 if (f1_orthodox and f2_southpaw) or (f1_southpaw and f2_orthodox) else 0
        
        # Finisher vs Finisher
        f1_finisher = f1_features.get('finish_rate', 0) > 0.5
        f2_finisher = f2_features.get('finish_rate', 0) > 0.5
        matchup['both_finishers'] = 1 if (f1_finisher and f2_finisher) else 0
        
        # Power striker indicators
        f1_power = f1_features.get('ko_rate', 0) > 0.3
        f2_power = f2_features.get('ko_rate', 0) > 0.3
        matchup['power_striker_matchup'] = 1 if (f1_power and f2_power) else 0
        
        # Defensive specialists
        f1_defensive = (f1_features.get('striking_defense', 0) > 0.55 and 
                       f1_features.get('takedown_defense', 0) > 0.70)
        f2_defensive = (f2_features.get('striking_defense', 0) > 0.55 and 
                       f2_features.get('takedown_defense', 0) > 0.70)
        matchup['defensive_fight'] = 1 if (f1_defensive and f2_defensive) else 0
        
        return matchup
    
    def _calculate_common_opponents(self, fighter_1_id: int, fighter_2_id: int,
                                     as_of_date: Optional[datetime] = None) -> Dict:
        """Analyze performance against common opponents"""
        # Get fight histories
        f1_history = self.fighter_extractor._get_fight_history(fighter_1_id, as_of_date)
        f2_history = self.fighter_extractor._get_fight_history(fighter_2_id, as_of_date)
        
        if len(f1_history) == 0 or len(f2_history) == 0:
            return {
                'num_common_opponents': 0,
                'common_opponent_performance_diff': 0,
            }
        
        # Find common opponents
        f1_opponents = set(f1_history['opponent_id'].values)
        f2_opponents = set(f2_history['opponent_id'].values)
        common_opponents = f1_opponents.intersection(f2_opponents)
        
        if len(common_opponents) == 0:
            return {
                'num_common_opponents': 0,
                'common_opponent_performance_diff': 0,
            }
        
        # Compare performance against common opponents
        f1_wins = 0
        f2_wins = 0
        
        for opponent_id in common_opponents:
            f1_result = f1_history[f1_history['opponent_id'] == opponent_id]['result'].iloc[0]
            f2_result = f2_history[f2_history['opponent_id'] == opponent_id]['result'].iloc[0]
            
            if f1_result == 'win':
                f1_wins += 1
            if f2_result == 'win':
                f2_wins += 1
        
        return {
            'num_common_opponents': len(common_opponents),
            'common_opponent_performance_diff': (f1_wins - f2_wins) / len(common_opponents),
        }


def create_training_dataset(
    session: Session,
    output_path: str = 'data/processed/training_data.csv',
    feature_set: Optional[List[str]] = None
):
    """
    Create a training dataset from all completed fights
    
    Args:
        session: Database session
        output_path: Where to save the dataset
        feature_set: Optional list of feature names to extract.
                    If None, uses FEATURE_SET_FULL (all features)
    """
    logger.info("Creating training dataset from completed fights...")
    
    matchup_extractor = MatchupFeatureExtractor(session)
    
    # Get all completed fights (with results)
    fights = session.query(Fight).filter(Fight.result != None).join(Fight.event).all()
    
    training_data = []
    
    for i, fight in enumerate(fights, 1):
        if i % 100 == 0:
            logger.info(f"Processing fight {i}/{len(fights)}")
        
        try:
            # --- SIMPLE EXCLUSION HACK: skip Chimaev vs Du Plessis fight from training ---
            try:
                f1_name = (fight.fighter_1.name or "").strip()
                f2_name = (fight.fighter_2.name or "").strip()
                fighter_set = {f1_name, f2_name}
                if fighter_set == {"Khamzat Chimaev", "Dricus Du Plessis"}:
                    logger.info(f"Skipping training rows for fight {fight.id} "
                                f"({f1_name} vs {f2_name})")
                    continue
            except Exception:
                # If for any reason names/relationships are missing, fall back to normal logic
                pass

            # Skip draws and no contests
            if fight.result not in ('fighter_1', 'fighter_2'):
                continue
            
            # Determine winner and loser IDs from current Fight row.
            # In the current DB, result is often normalized so that fighter_1 is the winner,
            # but we still handle both cases explicitly.
            if fight.result == 'fighter_1':
                winner_id = fight.fighter_1_id
                loser_id = fight.fighter_2_id
            else:
                winner_id = fight.fighter_2_id
                loser_id = fight.fighter_1_id
            
            # Perspective 1: winner as fighter_1 (positive class)
            features_win = matchup_extractor.extract_matchup_features(
                winner_id,
                loser_id,
                as_of_date=None,  # Could use event date for true historical analysis
                feature_set=feature_set
            )
            features_win['target'] = 1
            features_win['fight_id'] = fight.id
            features_win['event_id'] = fight.event_id
            features_win['fighter_1_id'] = winner_id
            features_win['fighter_2_id'] = loser_id
            features_win['weight_class'] = fight.weight_class
            features_win['is_title_fight'] = fight.is_title_fight
            features_win['method'] = fight.method
            
            training_data.append(features_win)
            
            # Perspective 2: loser as fighter_1 (negative class)
            features_lose = matchup_extractor.extract_matchup_features(
                loser_id,
                winner_id,
                as_of_date=None,
                feature_set=feature_set
            )
            features_lose['target'] = 0
            features_lose['fight_id'] = fight.id
            features_lose['event_id'] = fight.event_id
            features_lose['fighter_1_id'] = loser_id
            features_lose['fighter_2_id'] = winner_id
            features_lose['weight_class'] = fight.weight_class
            features_lose['is_title_fight'] = fight.is_title_fight
            features_lose['method'] = fight.method
            
            training_data.append(features_lose)
            
        except Exception as e:
            logger.error(f"Error processing fight {fight.id}: {e}")
            continue
    
    # Convert to DataFrame
    df = pd.DataFrame(training_data)
    
    # Save to file
    df.to_csv(output_path, index=False)
    logger.success(f"Created training dataset with {len(df)} fights. Saved to {output_path}")
    
    return df


if __name__ == '__main__':
    import argparse
    from database.db_manager import DatabaseManager
    
    parser = argparse.ArgumentParser(description='Create training dataset from matchup features')
    parser.add_argument('--feature-set', type=str,
                       choices=['base', 'advanced', 'full'],
                       default='full',
                       help='Feature set to use: base, advanced, or full (default: full)')
    parser.add_argument('--output', type=str,
                       default='data/processed/training_data.csv',
                       help='Output path for training dataset')
    
    args = parser.parse_args()
    
    # Map feature set string to actual feature set
    feature_set_map = {
        'base': FeatureRegistry.FEATURE_SET_BASE,
        'advanced': FeatureRegistry.FEATURE_SET_ADVANCED,
        'full': FeatureRegistry.FEATURE_SET_FULL,
    }
    feature_set = feature_set_map[args.feature_set]
    
    db = DatabaseManager()
    session = db.get_session()
    
    logger.info(f"Creating training dataset with '{args.feature_set}' feature set...")
    df = create_training_dataset(session, output_path=args.output, feature_set=feature_set)
    
    logger.info(f"Dataset shape: {df.shape}")
    logger.info(f"Target distribution:\n{df['target'].value_counts()}")
    
    session.close()

