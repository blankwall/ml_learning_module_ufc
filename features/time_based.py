"""
Time-Based Features
Rolling statistics, momentum, decline, activity, and time-decayed metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime

from .utils import (
    safe_divide, safe_mean, ensure_numeric, is_finish, is_ko,
    calculate_time_decayed_metric
)


def extract_rolling_stats(
    fight_history: pd.DataFrame,
    rolling_windows: List[int] = [3, 5]
) -> Dict[str, float]:
    """
    Calculate rolling statistics over different windows.
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        rolling_windows: List of window sizes (e.g., [3, 5, 10])
        
    Returns:
        Dictionary of rolling statistics
    """
    features = {}
    
    if len(fight_history) == 0:
        for window in rolling_windows:
            features[f'win_rate_last_{window}'] = 0.0
            features[f'finish_rate_last_{window}'] = 0.0
            features[f'ko_rate_last_{window}'] = 0.0
        features['performance_trend'] = 0.0
        features['athleticism_decline'] = 0.0
        return features
    
    for window in rolling_windows:
        recent_fights = fight_history.head(window)
        
        if len(recent_fights) == 0:
            features[f'win_rate_last_{window}'] = 0.0
            features[f'finish_rate_last_{window}'] = 0.0
            features[f'ko_rate_last_{window}'] = 0.0
            continue
        
        wins = (recent_fights['result'] == 'win').sum()
        finishes = recent_fights['method'].str.contains(
            'KO|TKO|SUB|Submission', na=False, case=False
        ).sum()
        
        features[f'win_rate_last_{window}'] = safe_divide(wins, len(recent_fights))
        features[f'finish_rate_last_{window}'] = safe_divide(finishes, len(recent_fights))
        
        # KO rate among wins
        kos_recent = recent_fights[
            recent_fights['method'].str.contains('KO|TKO', na=False, case=False)
        ]
        ko_wins_recent = ((kos_recent['result'] == 'win')).sum()
        wins_recent = wins
        features[f'ko_rate_last_{window}'] = safe_divide(ko_wins_recent, wins_recent)
    
    # Performance trend: difference between last 3 and last 5
    if 'win_rate_last_3' in features and 'win_rate_last_5' in features:
        features['performance_trend'] = features['win_rate_last_3'] - features['win_rate_last_5']
    else:
        features['performance_trend'] = 0.0
    
    # Athleticism decline: career KO rate vs recent KO rate
    if 'ko_rate' in features and 'ko_rate_last_3' in features:
        features['athleticism_decline'] = features['ko_rate'] - features['ko_rate_last_3']
    else:
        features['athleticism_decline'] = 0.0
    
    return features


def extract_momentum_features(
    fight_history: pd.DataFrame
) -> Dict[str, float]:
    """
    Extract momentum, recent form, and activity timing features.
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        
    Returns:
        Dictionary of momentum features
    """
    if len(fight_history) == 0:
        return {
            'current_win_streak': 0.0,
            'current_loss_streak': 0.0,
            'fights_in_last_year': 0.0,
            'activity_rate': 0.0,
            'days_since_last_fight': 0.0,
            'days_between_last_2_fights': 0.0,
            'long_layoff_over_1yr': 0.0,
            'long_layoff_over_2yr': 0.0,
        }
    
    # Calculate win/loss streaks
    win_streak = 0
    loss_streak = 0
    
    for _, fight in fight_history.iterrows():
        if fight['result'] == 'win':
            win_streak += 1
            loss_streak = 0
        elif fight['result'] == 'loss':
            loss_streak += 1
            win_streak = 0
        else:
            break
    
    # Activity rate (fights per year) - approximate (last up to 4 fights)
    fights_in_last_year = len(fight_history.head(min(len(fight_history), 4)))
    
    # Days since last fight and spacing
    days_since_last_fight = 0.0
    days_between_last_2 = 0.0
    
    try:
        if 'event_date_parsed' in fight_history.columns:
            last_date = fight_history['event_date_parsed'].iloc[0]
            now = datetime.now()
            days_since_last_fight = max(0.0, (now - last_date).days)
            
            if len(fight_history) > 1:
                prev_date = fight_history['event_date_parsed'].iloc[1]
                days_between_last_2 = max(0.0, (last_date - prev_date).days)
    except Exception:
        days_since_last_fight = 0.0
        days_between_last_2 = 0.0
    
    features = {
        'current_win_streak': float(win_streak),
        'current_loss_streak': float(loss_streak),
        'fights_in_last_year': float(fights_in_last_year),
        'activity_rate': float(fights_in_last_year),
        'days_since_last_fight': float(days_since_last_fight),
        'days_between_last_2_fights': float(days_between_last_2),
        'long_layoff_over_1yr': 1.0 if days_since_last_fight >= 365 else 0.0,
        'long_layoff_over_2yr': 1.0 if days_since_last_fight >= 730 else 0.0,
    }
    
    return features


def extract_decline_features(
    fight_history: pd.DataFrame
) -> Dict[str, float]:
    """
    Extract longer-horizon decline / slump patterns.
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        
    Returns:
        Dictionary of decline features
    """
    if len(fight_history) == 0:
        return {
            "fights_since_last_win": 0.0,
            "years_since_last_win": 0.0,
            "has_ever_won": 0.0,
            "losses_since_last_win": 0.0,
            "decision_losses_since_last_win": 0.0,
            "finish_losses_since_last_win": 0.0,
            "recent_vs_career_win_rate": 0.0,
            "win_rate_last_3_years": 0.0,
            "wins_last_3_years": 0.0,
            "losses_last_3_years": 0.0,
            "finish_rate_last_3_years": 0.0,
        }
    
    df = fight_history
    
    # Locate most recent win
    win_rows = df[df["result"] == "win"]
    if len(win_rows) == 0:
        fights_since_last_win = len(df)
        years_since_last_win = 0.0
        has_ever_won = 0.0
        slump = df
    else:
        last_win_idx = int(win_rows.index[0])
        last_win_date = df.loc[last_win_idx, "event_date_parsed"]
        
        ref_date = datetime.now()
        fights_since_last_win = last_win_idx
        years_since_last_win = max(0.0, (ref_date - last_win_date).days / 365.25)
        has_ever_won = 1.0
        
        slump = df.iloc[:last_win_idx]
    
    # Losses in slump
    if len(slump) == 0:
        losses_since_last_win = 0.0
        decision_losses_since_last_win = 0.0
        finish_losses_since_last_win = 0.0
    else:
        losses_mask = slump["result"] == "loss"
        method_series = slump["method"].astype(str)
        decision_mask = method_series.str.contains("DEC|Decision", case=False, na=False)
        finish_mask = method_series.str.contains("KO|TKO|SUB|Submission", case=False, na=False)
        
        losses_since_last_win = float(losses_mask.sum())
        decision_losses_since_last_win = float((losses_mask & decision_mask).sum())
        finish_losses_since_last_win = float((losses_mask & finish_mask).sum())
    
    # Career vs recent win rate
    total_fights = len(df)
    career_wins = (df["result"] == "win").sum()
    career_win_rate = safe_divide(career_wins, total_fights)
    
    recent = df.head(5)
    if len(recent) > 0:
        recent_wins = (recent["result"] == "win").sum()
        recent_win_rate_last_5 = safe_divide(recent_wins, len(recent))
    else:
        recent_win_rate_last_5 = 0.0
    
    recent_vs_career_win_rate = recent_win_rate_last_5 - career_win_rate
    
    # Time-windowed (3-year) recent performance
    now = datetime.now()
    three_years_ago = now - pd.DateOffset(years=3)
    
    recent_window = df[df["event_date_parsed"] >= three_years_ago] if "event_date_parsed" in df.columns else pd.DataFrame()
    
    if len(recent_window) > 0:
        wins_last_3_years = (recent_window["result"] == "win").sum()
        losses_last_3_years = (recent_window["result"] == "loss").sum()
        total_last_3_years = len(recent_window)
        win_rate_last_3_years = safe_divide(wins_last_3_years, total_last_3_years)
        
        method_series_recent = recent_window["method"].astype(str)
        finish_mask_recent = method_series_recent.str.contains(
            "KO|TKO|SUB|Submission", case=False, na=False
        )
        finishes_last_3_years = (
            ((recent_window["result"] == "win") & finish_mask_recent).sum()
        )
        finish_rate_last_3_years = safe_divide(finishes_last_3_years, wins_last_3_years)
    else:
        wins_last_3_years = 0.0
        losses_last_3_years = 0.0
        win_rate_last_3_years = 0.0
        finish_rate_last_3_years = 0.0
    
    return {
        "fights_since_last_win": float(fights_since_last_win),
        "years_since_last_win": float(years_since_last_win),
        "has_ever_won": float(has_ever_won),
        "losses_since_last_win": losses_since_last_win,
        "decision_losses_since_last_win": decision_losses_since_last_win,
        "finish_losses_since_last_win": finish_losses_since_last_win,
        "recent_vs_career_win_rate": float(recent_vs_career_win_rate),
        "win_rate_last_3_years": float(win_rate_last_3_years),
        "wins_last_3_years": float(wins_last_3_years),
        "losses_last_3_years": float(losses_last_3_years),
        "finish_rate_last_3_years": float(finish_rate_last_3_years),
    }


def extract_recent_damage_features(
    fight_history: pd.DataFrame
) -> Dict[str, float]:
    """
    Extract very recent performance, especially bad losses and finishes.
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        
    Returns:
        Dictionary of recent damage features
    """
    if len(fight_history) == 0:
        return {
            "recent_losses_last_2": 0.0,
            "recent_finish_losses_last_2": 0.0,
            "recent_finish_loss_last_fight": 0.0,
            "recent_finish_loss_ratio_last_2": 0.0,
        }
    
    recent_2 = fight_history.head(2)
    recent_1 = fight_history.head(1)
    
    def _is_finish_loss(row) -> bool:
        if row.get("result") != "loss":
            return False
        method = str(row.get("method") or "")
        return bool(pd.notna(method) and (
            "KO" in method.upper() or
            "TKO" in method.upper() or
            "SUB" in method.upper() or
            "SUBMISSION" in method.upper()
        ))
    
    # Losses and finish-losses in last 2
    losses_last_2 = 0.0
    finish_losses_last_2 = 0.0
    for _, row in recent_2.iterrows():
        if row.get("result") == "loss":
            losses_last_2 += 1.0
        if _is_finish_loss(row):
            finish_losses_last_2 += 1.0
    
    # Was the most recent fight a bad finish loss?
    last_fight_finish_loss = 0.0
    if len(recent_1) == 1:
        last_row = recent_1.iloc[0]
        if _is_finish_loss(last_row):
            last_fight_finish_loss = 1.0
    
    fights_considered = max(1, len(recent_2))
    finish_loss_ratio_last_2 = safe_divide(finish_losses_last_2, fights_considered)
    
    return {
        "recent_losses_last_2": losses_last_2,
        "recent_finish_losses_last_2": finish_losses_last_2,
        "recent_finish_loss_last_fight": last_fight_finish_loss,
        "recent_finish_loss_ratio_last_2": finish_loss_ratio_last_2,
    }


def extract_time_decayed_features(
    fight_history: pd.DataFrame,
    lambda_decay: float = 0.3
) -> Dict[str, float]:
    """
    Compute time-decayed performance metrics where recent fights are weighted more heavily.
    
    Uses exponential decay: weight = exp(-lambda * years_ago)
    
    Args:
        fight_history: DataFrame with fight history (sorted most recent first)
        lambda_decay: Decay rate (higher = faster decay, default 0.3)
        
    Returns:
        Dictionary with time-decayed metrics
    """
    if len(fight_history) == 0:
        return {
            "time_decayed_win_rate": 0.0,
            "time_decayed_finish_rate": 0.0,
            "time_decayed_ko_rate": 0.0,
        }
    
    if "event_date_parsed" not in fight_history.columns:
        # Fallback to simple win rate if dates aren't available
        wins = (fight_history["result"] == "win").sum()
        total = len(fight_history)
        return {
            "time_decayed_win_rate": safe_divide(wins, total),
            "time_decayed_finish_rate": 0.0,
            "time_decayed_ko_rate": 0.0,
        }
    
    now = datetime.now()
    method_series = fight_history["method"].astype(str)
    finish_mask = method_series.str.contains("KO|TKO|SUB|Submission", case=False, na=False)
    ko_mask = method_series.str.contains("KO|TKO", case=False, na=False)
    
    total_weight = 0.0
    win_weight = 0.0
    finish_weight = 0.0
    ko_weight = 0.0
    
    for _, row in fight_history.iterrows():
        try:
            fight_date = row["event_date_parsed"]
            years_ago = (now - fight_date).days / 365.25
            weight = np.exp(-lambda_decay * years_ago)
            
            total_weight += weight
            
            if row["result"] == "win":
                win_weight += weight
                if finish_mask.loc[row.name]:
                    finish_weight += weight
                if ko_mask.loc[row.name]:
                    ko_weight += weight
        except Exception:
            continue
    
    if total_weight == 0:
        return {
            "time_decayed_win_rate": 0.0,
            "time_decayed_finish_rate": 0.0,
            "time_decayed_ko_rate": 0.0,
        }
    
    time_decayed_win_rate = safe_divide(win_weight, total_weight)
    time_decayed_finish_rate = safe_divide(finish_weight, win_weight)
    time_decayed_ko_rate = safe_divide(ko_weight, win_weight)
    
    return {
        "time_decayed_win_rate": float(time_decayed_win_rate),
        "time_decayed_finish_rate": float(time_decayed_finish_rate),
        "time_decayed_ko_rate": float(time_decayed_ko_rate),
    }


def extract_age_interactions(
    age: float,
    decline_features: Dict[str, float],
    momentum_features: Dict[str, float]
) -> Dict[str, float]:
    """
    Create age × decline and age × activity interaction features.
    
    Args:
        age: Fighter age
        decline_features: Dictionary of decline features
        momentum_features: Dictionary of momentum/activity features
        
    Returns:
        Dictionary of age interaction features
    """
    try:
        age = float(age or 0.0)
        years_since_last_win = float(decline_features.get("years_since_last_win", 0.0) or 0.0)
        fights_since_last_win = float(decline_features.get("fights_since_last_win", 0) or 0)
        recent_vs_career_win_rate = float(decline_features.get("recent_vs_career_win_rate", 0.0) or 0.0)
        
        days_since_last_fight = float(momentum_features.get("days_since_last_fight", 0) or 0)
        fights_in_last_year = float(momentum_features.get("fights_in_last_year", 0) or 0)
        
        # Only penalize decline (negative recent_vs_career means declining)
        decline_magnitude = max(0.0, -recent_vs_career_win_rate)
        
        # Convert days to years for better scaling
        years_since_last_fight = days_since_last_fight / 365.25
        
        return {
            "age_x_years_since_last_win": float(age * years_since_last_win),
            "age_x_fights_since_last_win": float(age * fights_since_last_win),
            "age_x_recent_vs_career_decline": float(age * decline_magnitude),
            "age_x_days_since_last_fight": float(age * days_since_last_fight),
            "age_x_years_since_last_fight": float(age * years_since_last_fight),
            "age_x_fights_in_last_year": float(age * fights_in_last_year),
        }
    except Exception:
        return {
            "age_x_years_since_last_win": 0.0,
            "age_x_fights_since_last_win": 0.0,
            "age_x_recent_vs_career_decline": 0.0,
            "age_x_days_since_last_fight": 0.0,
            "age_x_years_since_last_fight": 0.0,
            "age_x_fights_in_last_year": 0.0,
        }


def extract_youth_form_score(
    age: float,
    win_rate_last_5: float,
    finish_rate_last_5: float
) -> float:
    """
    Calculate youth + recent form interaction score.
    
    Helps capture surging young prospects.
    
    Args:
        age: Fighter age
        win_rate_last_5: Win rate in last 5 fights
        finish_rate_last_5: Finish rate in last 5 fights
        
    Returns:
        Youth form score
    """
    try:
        age = float(age or 0.0)
        win_rate_last_5 = float(win_rate_last_5 or 0.0)
        finish_rate_last_5 = float(finish_rate_last_5 or 0.0)
        
        base_form = max(0.0, 0.8 * win_rate_last_5 + 0.2 * finish_rate_last_5)
        youth_factor = max(0.0, 30.0 - age)
        return float(base_form * youth_factor)
    except Exception:
        return 0.0

