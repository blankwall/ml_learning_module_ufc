"""
Grappling Features
Takedowns, submissions, control time, and related grappling metrics
"""

import pandas as pd
from typing import Dict, Optional
from database.schema import Fighter

from .utils import safe_divide, ensure_numeric, parse_control_time_seconds


def extract_grappling_features(fighter: Fighter) -> Dict[str, float]:
    """
    Extract grappling-related features from a fighter.
    
    Pure function that takes a Fighter object and returns grappling features.
    
    Args:
        fighter: Fighter database object
        
    Returns:
        Dictionary of grappling features
    """
    features = {
        # Core grappling stats (per-15min rates)
        "takedown_avg_per_15min": float(fighter.takedown_avg_per_15min or 0.0),
        "takedown_accuracy": float(fighter.takedown_accuracy or 0.0),
        "takedown_defense": float(fighter.takedown_defense or 0.0),
        "submission_avg_per_15min": float(fighter.submission_avg_per_15min or 0.0),
    }
    
    return features


def extract_recent_grappling_features(
    fight_history: pd.DataFrame,
    fight_stats_by_fight_id: Dict[int, any],
    fighter_id: int,
    window: int = 3
) -> Dict[str, float]:
    """
    Extract recent grappling performance from FightStats (last N fights).
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        fight_stats_by_fight_id: Dictionary mapping fight_id to FightStats object
        fighter_id: Fighter ID to extract stats for
        window: Number of recent fights to consider
        
    Returns:
        Dictionary of recent grappling features
    """
    if len(fight_history) == 0 or "fight_id" not in fight_history.columns:
        return {
            "recent_control_time_sec_last_3": 0.0,
            "recent_control_time_diff_last_3": 0.0,
        }
    
    recent = fight_history.head(window)
    fight_ids = [int(fid) for fid in recent["fight_id"].tolist() if pd.notna(fid)]
    
    if not fight_ids:
        return {
            "recent_control_time_sec_last_3": 0.0,
            "recent_control_time_diff_last_3": 0.0,
        }
    
    control_diffs = []
    my_control_times = []
    
    for _, row in recent.iterrows():
        fid = int(row.get("fight_id"))
        stats = fight_stats_by_fight_id.get(fid)
        if not stats:
            continue
        
        is_f1 = bool(row.get("is_fighter_1"))
        my_totals = stats.fighter_1_totals if is_f1 else stats.fighter_2_totals
        opp_totals = stats.fighter_2_totals if is_f1 else stats.fighter_1_totals
        
        if not my_totals or not opp_totals:
            continue
        
        # Control time (seconds)
        my_ct = parse_control_time_seconds(my_totals.get("control_time"))
        opp_ct = parse_control_time_seconds(opp_totals.get("control_time"))
        my_control_times.append(my_ct)
        control_diffs.append(my_ct - opp_ct)
    
    from .utils import safe_mean
    
    return {
        "recent_control_time_sec_last_3": safe_mean(my_control_times),
        "recent_control_time_diff_last_3": safe_mean(control_diffs),
    }

