"""
Striking Features
Striking statistics, accuracy, defense, and related metrics
"""

import pandas as pd
from typing import Dict, Optional
from database.schema import Fighter,Fight
import numpy as np
from datetime import datetime

from .utils import safe_divide, ensure_numeric

def parse_strike_fraction(strike_str):
    """Parse '11 of 16' into (landed, attempted)"""
    if not strike_str or strike_str == "0 of 0":
        return 0, 0
    parts = strike_str.split(" of ")
    return int(parts[0]), int(parts[1])

def extract_fight_details(fight: Fight, fighter_number: str) -> Dict[str, float]:
    # print(fight.fight_id)
    # print(fight.fight_stats)
    # print('fight_date',fight.event.date)
    dt = datetime.strptime(fight.event.date, "%B %d, %Y")
    key = dt.strftime("%Y%m%d")
    # print(key)

    if not fight.fight_stats:
        return None
    
    # Check if significant_strikes data exists and has the required fighter data
    if not fight.fight_stats.significant_strikes:
        return None
    
    if fighter_number not in fight.fight_stats.significant_strikes:
        return None
    
    sig_strikes = fight.fight_stats.significant_strikes[fighter_number]
    totals = fight.fight_stats.fighter_1_totals if fighter_number == "fighter_1" else fight.fight_stats.fighter_2_totals
    
    # Check if required keys exist, return None if data is incomplete
    required_keys = ["sig_strikes_total", "head_strikes", "body_strikes", "leg_strikes", 
                     "distance_strikes", "clinch_strikes", "ground_strikes"]
    if not all(key in sig_strikes for key in required_keys):
        return None
    
    # Parse all strike types
    sig_total_landed, sig_total_attempted = parse_strike_fraction(sig_strikes.get("sig_strikes_total", "0 of 0"))
    head_landed, head_attempted = parse_strike_fraction(sig_strikes.get("head_strikes", "0 of 0"))
    body_landed, body_attempted = parse_strike_fraction(sig_strikes.get("body_strikes", "0 of 0"))
    leg_landed, leg_attempted = parse_strike_fraction(sig_strikes.get("leg_strikes", "0 of 0"))
    distance_landed, distance_attempted = parse_strike_fraction(sig_strikes.get("distance_strikes", "0 of 0"))
    clinch_landed, clinch_attempted = parse_strike_fraction(sig_strikes.get("clinch_strikes", "0 of 0"))
    ground_landed, ground_attempted = parse_strike_fraction(sig_strikes.get("ground_strikes", "0 of 0"))
    
    duration_min = fight.round_finished * 5 if fight.round_finished else 15

    # print("sig_total_landed", sig_total_landed, "sig_total_attempted", sig_total_attempted)
    # print("head_landed", head_landed, "head_attempted", head_attempted)
    # print("body_landed", body_landed, "body_attempted", body_attempted)
    # print("leg_landed", leg_landed, "leg_attempted", leg_attempted)
    # print("distance_landed", distance_landed, "distance_attempted", distance_attempted)
    # print("clinch_landed", clinch_landed, "clinch_attempted", clinch_attempted)
    # print("ground_landed", ground_landed, "ground_attempted", ground_attempted)
    # print("duration_min", duration_min)
    # print('knockdowns', int(totals.get('knockdowns', 0)))

    sig_strikes_landed_per_min = sig_total_landed / duration_min
    striking_accuracy = sig_total_landed / sig_total_attempted if sig_total_attempted > 0 else 0

    # Validate strike data consistency
    # Target areas (head/body/leg) should sum to sig_total_landed
    target_area_sum = head_landed + body_landed + leg_landed
    # Position (distance/clinch/ground) should also sum to sig_total_landed
    position_sum = distance_landed + clinch_landed + ground_landed
    
    # Handle data quality issues: normalize rates to sum to 1.0
    # This handles cases where UFC data has inconsistencies (e.g., head+body+leg != sig_total)
    # We normalize by the actual sum of the category, not sig_total_landed
    target_area_normalizer = target_area_sum if target_area_sum > 0 else 1.0
    position_normalizer = position_sum if position_sum > 0 else 1.0
    
    # Debug: Log if normalization is needed (data inconsistency detected)
    if target_area_sum > 0 and abs(target_area_sum - sig_total_landed) > 0.01 * sig_total_landed:
        # Data inconsistency detected - this is OK, we normalize to handle it
        pass  # Could log this if needed for debugging
    
    # Calculate per-fight metrics with normalization to handle data inconsistencies
    fight_metrics = {
        'distance_accuracy': distance_landed / distance_attempted if distance_attempted > 0 else 0,
        'clinch_accuracy': clinch_landed / clinch_attempted if clinch_attempted > 0 else 0,
        'ground_strike_output_per_min': ground_landed / duration_min if duration_min > 0 else 0,
        # Normalize target area rates so they sum to 1.0 (handle data inconsistencies)
        'leg_strike_rate': leg_landed / target_area_normalizer if target_area_normalizer > 0 else 0,
        'body_strike_rate': body_landed / target_area_normalizer if target_area_normalizer > 0 else 0,
        'head_strike_rate': head_landed / target_area_normalizer if target_area_normalizer > 0 else 0,
        # Normalize position rates so they sum to 1.0 (handle data inconsistencies)
        'ground_strike_rate': ground_landed / position_normalizer if position_normalizer > 0 else 0,
        'distance_strike_rate': distance_landed / position_normalizer if position_normalizer > 0 else 0,
        'clinch_strike_rate': clinch_landed / position_normalizer if position_normalizer > 0 else 0,
        'knockdowns': int(totals.get('knockdowns', 0)),
        "duration_min": duration_min,
        "sig_strikes_landed_per_min": sig_strikes_landed_per_min,
        "sig_total_landed": sig_total_landed,
        "striking_accuracy": striking_accuracy,
        "fight_key": key
    }
    # from pprint import pprint
    # pprint(fight_metrics)
    return fight_metrics

def extract_striking_features(fighter: Fighter) -> Dict[str, float]:
    """
    Extract striking-related features from a fighter.
    
    Pure function that takes a Fighter object and returns striking features.
    
    Args:
        fighter: Fighter database object
        
    Returns:
        Dictionary of striking features
    """
    # print(fighter.name)
    # from pprint import pprint
    # pprint(dir(fighter))
    # exit(1)
    recent_metrics = []
    sig_strikes_landed = fighter.sig_strikes_landed_per_min or 0.0
    striking_accuracy = fighter.striking_accuracy or 0.0
    sig_strikes_absorbed = fighter.sig_strikes_absorbed_per_min or 0.0
    striking_defense = fighter.striking_defense or 0.0
    
    # Collect fight metrics from both fighter_1 and fighter_2 fights
    for fight in fighter.fights_as_fighter_1:
        fight_metrics = extract_fight_details(fight, "fighter_1")
        if fight_metrics is not None:
            recent_metrics.append(fight_metrics)
    
    for fight in fighter.fights_as_fighter_2:
        fight_metrics = extract_fight_details(fight, "fighter_2")
        if fight_metrics is not None:
            recent_metrics.append(fight_metrics)
    
    # print("Total fights", len(recent_metrics))
    
    # Sort by fight_key if we have metrics
    if recent_metrics:
        recent_metrics.sort(key=lambda x: x['fight_key'], reverse=True)
        last_3 = recent_metrics[:3]  # Most recent 3 fights
        
        distance_accuracy_last_3 = np.mean([m['distance_accuracy'] for m in last_3])
        clinch_accuracy_last_3 = np.mean([m['clinch_accuracy'] for m in last_3])
        ground_output_per_min_last_3 = np.mean([m['ground_strike_output_per_min'] for m in last_3])
        
        # For strike rates, only average fights that actually have strikes
        # This prevents diluting the sum when averaging fights with 0 strikes
        fights_with_strikes = [m for m in last_3 if m.get('sig_total_landed', 0) > 0]
        if fights_with_strikes:
            leg_strike_rate_last_3 = np.mean([m['leg_strike_rate'] for m in fights_with_strikes])
            head_strike_rate_last_3 = np.mean([m['head_strike_rate'] for m in fights_with_strikes])
            body_strike_rate_last_3 = np.mean([m['body_strike_rate'] for m in fights_with_strikes])
            ground_strike_rate_last_3 = np.mean([m['ground_strike_rate'] for m in fights_with_strikes])
            distance_strike_rate_last_3 = np.mean([m['distance_strike_rate'] for m in fights_with_strikes])
        else:
            leg_strike_rate_last_3 = 0.0
            head_strike_rate_last_3 = 0.0
            body_strike_rate_last_3 = 0.0
            ground_strike_rate_last_3 = 0.0
            distance_strike_rate_last_3 = 0.0
        
        knockdowns_last_3 = sum([m['knockdowns'] for m in last_3])
        striking_accuracy_last_3 = np.mean([m['striking_accuracy'] for m in last_3])
        sig_strikes_landed_per_min_last_3 = np.mean([m['sig_strikes_landed_per_min'] for m in last_3])
        
        # Lifetime metrics
        distance_accuracy_lifetime = np.mean([m['distance_accuracy'] for m in recent_metrics])
        clinch_accuracy_lifetime = np.mean([m['clinch_accuracy'] for m in recent_metrics])
        ground_output_per_min_lifetime = np.mean([m['ground_strike_output_per_min'] for m in recent_metrics])
        
        # For strike rates, only average fights that actually have strikes
        # This prevents diluting the sum when averaging fights with 0 strikes
        fights_with_strikes_lifetime = [m for m in recent_metrics if m.get('sig_total_landed', 0) > 0]
        if fights_with_strikes_lifetime:
            leg_strike_rate_lifetime = np.mean([m['leg_strike_rate'] for m in fights_with_strikes_lifetime])
            head_strike_rate_lifetime = np.mean([m['head_strike_rate'] for m in fights_with_strikes_lifetime])
            body_strike_rate_lifetime = np.mean([m['body_strike_rate'] for m in fights_with_strikes_lifetime])
            ground_strike_rate_lifetime = np.mean([m['ground_strike_rate'] for m in fights_with_strikes_lifetime])
            distance_strike_rate_lifetime = np.mean([m['distance_strike_rate'] for m in fights_with_strikes_lifetime])
        else:
            leg_strike_rate_lifetime = 0.0
            head_strike_rate_lifetime = 0.0
            body_strike_rate_lifetime = 0.0
            ground_strike_rate_lifetime = 0.0
            distance_strike_rate_lifetime = 0.0
        
        knockdowns_lifetime = sum([m['knockdowns'] for m in recent_metrics])
        sig_strikes_landed_per_min_lifetime = np.mean([m['sig_strikes_landed_per_min'] for m in recent_metrics])
        striking_accuracy_lifetime = np.mean([m['striking_accuracy'] for m in recent_metrics])
        sig_strikes_landed_lifetime_mean = np.mean([m['sig_total_landed'] for m in recent_metrics])
    else:
        # No fight history - use defaults
        distance_accuracy_last_3 = 0.0
        clinch_accuracy_last_3 = 0.0
        ground_output_per_min_last_3 = 0.0
        leg_strike_rate_last_3 = 0.0
        knockdowns_last_3 = 0
        striking_accuracy_last_3 = 0.0
        sig_strikes_landed_per_min_last_3 = 0.0
        head_strike_rate_last_3 = 0.0
        body_strike_rate_last_3 = 0.0
        ground_strike_rate_last_3 = 0.0
        distance_strike_rate_last_3 = 0.0
        
        # Lifetime defaults
        distance_accuracy_lifetime = 0.0
        clinch_accuracy_lifetime = 0.0
        ground_output_per_min_lifetime = 0.0
        leg_strike_rate_lifetime = 0.0
        knockdowns_lifetime = 0
        head_strike_rate_lifetime = 0.0
        body_strike_rate_lifetime = 0.0
        ground_strike_rate_lifetime = 0.0
        distance_strike_rate_lifetime = 0.0
        sig_strikes_landed_per_min_lifetime = 0.0
        striking_accuracy_lifetime = 0.0
        sig_strikes_landed_lifetime_mean = 0.0
    # striking_differential_lifetime = np.mean([m['striking_differential'] for m in recent_metrics])
    # defensive_efficiency_lifetime = np.mean([m['defensive_efficiency'] for m in recent_metrics])
    # striking_volume_control_lifetime = np.mean([m['striking_volume_control'] for m in recent_metrics])

    # striking_differential = striking_differential_lifetime


    # print("Lifetime metrics")
    # print("Distance accuracy", distance_accuracy_lifetime)
    # print("Clinch accuracy", clinch_accuracy_lifetime)
    # print("Ground output per min", ground_output_per_min_lifetime)
    # print("Leg strike rate", leg_strike_rate_lifetime)
    # print("Knockdowns", knockdowns_lifetime)
    # print("Head strike rate", head_strike_rate_lifetime)
    # print("Body strike rate", body_strike_rate_lifetime)
    # print("Ground strike rate", ground_strike_rate_lifetime)
    # print("Distance strike rate", distance_strike_rate_lifetime)
    # print("Sig strikes landed per min", sig_strikes_landed_per_min_lifetime)
    # print("Striking accuracy", striking_accuracy_lifetime)

    #Not yet implemented
    # print("Sig strikes absorbed per min", sig_strikes_absorbed_per_min_lifetime)
    # print("Striking defense", striking_defense_lifetime)
    # print("Striking differential", striking_differential_lifetime)
    # print("Defensive efficiency", defensive_efficiency_lifetime)
    # print("Striking volume control", striking_volume_control_lifetime)
    # print("Total fights", len(recent_metrics))
    # exit(1)

    # head_strike_rate = fighter.head_strikes / sig_strikes_landed
    # body_strike_rate = fighter.body_strikes / sig_strikes_total  
    # leg_strike_rate = fighter.leg_strikes / sig_strikes_total
    
    # distance_strike_rate = fighter.distance_strikes / sig_strikes_total
    # clinch_strike_rate = fighter.clinch_strikes / sig_strikes_total
    # ground_strike_rate = fighter.ground_strikes / sig_strikes_total

    # # Derived features
    
    # Defensive efficiency: defense rate adjusted for volume absorbed
    # Higher defense with lower absorption = better efficiency
    defensive_efficiency = striking_defense * safe_divide(
        1.0, max(0.1, sig_strikes_absorbed), default=0.0
    )
    # NOTE:
    # `sig_strikes_landed` is a *per-minute* rate (career stat). For modeling we must keep
    # units consistent: anything compared to `sig_strikes_absorbed` (also per-minute) must
    # be per-minute as well.
    #
    # Previously we overwrote `sig_strikes_landed` with `sig_strikes_landed_lifetime_mean`,
    # which is the mean *total landed per fight* (not per-minute). That made
    # `striking_volume_control` explode (e.g. ~10-20+) and distorted multiple downstream
    # features (volume control + differential), which can easily flip close picks.
    sig_strikes_landed_per_min_effective = (
        sig_strikes_landed_per_min_lifetime if recent_metrics else sig_strikes_landed
    )

    # Striking volume control: output vs absorption ratio (both per-minute)
    # Higher ratio = more control of striking exchanges
    striking_volume_control = safe_divide(
        sig_strikes_landed_per_min_effective, max(0.1, sig_strikes_absorbed), default=0.0
    )
    # Striking differential: output minus absorption (both per-minute)
    striking_differential = sig_strikes_landed_per_min_effective - sig_strikes_absorbed
    
    features = {
        # Core striking stats (per-minute rates)
        "sig_strikes_landed_per_min": float(sig_strikes_landed_per_min_effective),
        "striking_accuracy": float(striking_accuracy),
        # "sig_strikes_absorbed_per_min": float(sig_strikes_absorbed),
        "striking_defense": float(striking_defense),
        
        # Derived striking metrics
        "striking_differential": float(striking_differential),
        "defensive_efficiency": float(defensive_efficiency),
        "striking_volume_control": float(striking_volume_control),
        
        # Last 3 fights metrics
        "distance_accuracy_last_3": float(distance_accuracy_last_3),
        "clinch_accuracy_last_3": float(clinch_accuracy_last_3),
        "ground_output_per_min_last_3": float(ground_output_per_min_last_3),
        "leg_strike_rate_last_3": float(leg_strike_rate_last_3),
        "knockdowns_last_3": float(knockdowns_last_3),
        "striking_accuracy_last_3": float(striking_accuracy_last_3),
        "sig_strikes_landed_per_min_last_3": float(sig_strikes_landed_per_min_last_3),
        "head_strike_rate_last_3": float(head_strike_rate_last_3),
        "body_strike_rate_last_3": float(body_strike_rate_last_3),
        "ground_strike_rate_last_3": float(ground_strike_rate_last_3),
        "distance_strike_rate_last_3": float(distance_strike_rate_last_3),
        
        # Lifetime metrics
        "distance_accuracy_lifetime": float(distance_accuracy_lifetime),
        "clinch_accuracy_lifetime": float(clinch_accuracy_lifetime),
        "ground_output_per_min_lifetime": float(ground_output_per_min_lifetime),
        "leg_strike_rate_lifetime": float(leg_strike_rate_lifetime),
        "knockdowns_lifetime": float(knockdowns_lifetime),
        "head_strike_rate_lifetime": float(head_strike_rate_lifetime),
        "body_strike_rate_lifetime": float(body_strike_rate_lifetime),
        "ground_strike_rate_lifetime": float(ground_strike_rate_lifetime),
        "distance_strike_rate_lifetime": float(distance_strike_rate_lifetime),
        "sig_strikes_landed_per_min_lifetime": float(sig_strikes_landed_per_min_lifetime),
        "striking_accuracy_lifetime": float(striking_accuracy_lifetime),
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

