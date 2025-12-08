"""
Striking Features
Striking statistics, accuracy, defense, and related metrics
"""

import pandas as pd
from typing import Dict, Optional
from database.schema import Fighter

from .utils import safe_divide, ensure_numeric


def extract_striking_features(fighter: Fighter) -> Dict[str, float]:
    """
    Extract striking-related features from a fighter.
    
    Pure function that takes a Fighter object and returns striking features.
    
    Args:
        fighter: Fighter database object
        
    Returns:
        Dictionary of striking features
    """
    sig_strikes_landed = fighter.sig_strikes_landed_per_min or 0.0
    striking_accuracy = fighter.striking_accuracy or 0.0
    sig_strikes_absorbed = fighter.sig_strikes_absorbed_per_min or 0.0
    striking_defense = fighter.striking_defense or 0.0
    
    # Derived features
    striking_differential = sig_strikes_landed - sig_strikes_absorbed
    
    # Defensive efficiency: defense rate adjusted for volume absorbed
    # Higher defense with lower absorption = better efficiency
    defensive_efficiency = striking_defense * safe_divide(
        1.0, max(0.1, sig_strikes_absorbed), default=0.0
    )
    
    # Striking volume control: output vs absorption ratio
    # Higher ratio = more control of striking exchanges
    striking_volume_control = safe_divide(
        sig_strikes_landed, max(0.1, sig_strikes_absorbed), default=0.0
    )
    
    features = {
        # Core striking stats (per-minute rates)
        "sig_strikes_landed_per_min": float(sig_strikes_landed),
        "striking_accuracy": float(striking_accuracy),
        "sig_strikes_absorbed_per_min": float(sig_strikes_absorbed),
        "striking_defense": float(striking_defense),
        
        # Derived striking metrics
        "striking_differential": float(striking_differential),
        "defensive_efficiency": float(defensive_efficiency),
        "striking_volume_control": float(striking_volume_control),
    }
    
    return features


def extract_recent_striking_features(
    fight_history: pd.DataFrame,
    fight_stats_by_fight_id: Dict[int, any],
    fighter_id: int,
    window: int = 3
) -> Dict[str, float]:
    """
    Extract recent striking performance from FightStats (last N fights).
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        fight_stats_by_fight_id: Dictionary mapping fight_id to FightStats object
        fighter_id: Fighter ID to extract stats for
        window: Number of recent fights to consider
        
    Returns:
        Dictionary of recent striking features
    """
    if len(fight_history) == 0 or "fight_id" not in fight_history.columns:
        return {
            "recent_sig_strike_diff_last_3": 0.0,
            "recent_knockdown_diff_last_3": 0.0,
        }
    
    from .utils import parse_landed, parse_int
    
    recent = fight_history.head(window)
    fight_ids = [int(fid) for fid in recent["fight_id"].tolist() if pd.notna(fid)]
    
    if not fight_ids:
        return {
            "recent_sig_strike_diff_last_3": 0.0,
            "recent_knockdown_diff_last_3": 0.0,
        }
    
    sig_diffs = []
    kd_diffs = []
    
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
        
        # Knockdowns
        my_kd = parse_int(my_totals.get("knockdowns"))
        opp_kd = parse_int(opp_totals.get("knockdowns"))
        kd_diffs.append(my_kd - opp_kd)
        
        # Significant strikes landed
        my_sig = parse_landed(my_totals.get("sig_strikes"))
        opp_sig = parse_landed(opp_totals.get("sig_strikes"))
        sig_diffs.append(my_sig - opp_sig)
    
    from .utils import safe_mean
    
    return {
        "recent_sig_strike_diff_last_3": safe_mean(sig_diffs),
        "recent_knockdown_diff_last_3": safe_mean(kd_diffs),
    }

