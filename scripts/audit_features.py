#!/usr/bin/env python3
"""
Feature Audit Script
Systematically checks all features for logical errors and edge cases
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger
from datetime import datetime, timedelta

from database.db_manager import DatabaseManager
from database.schema import Fighter
from features.registry import FeatureRegistry, FeatureBuilder


class FeatureAuditor:
    """Systematic feature validation and bug detection"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = self.db.get_session()
        self.feature_builder = FeatureBuilder(self.session)
        self.issues = []
        
    def audit_all_features(self) -> Dict[str, List[str]]:
        """Run all audit checks"""
        logger.info("Starting feature audit...")
        
        results = {
            "logical_errors": [],
            "edge_cases": [],
            "sanity_checks": [],
            "consistency_checks": [],
        }
        
        # Get a sample of fighters for testing
        fighters = self.session.query(Fighter).limit(100).all()
        logger.info(f"Testing with {len(fighters)} fighters")
        
        # Test each feature module
        feature_modules = [
            "physical", "striking", "grappling", "career_stats",
            "fight_history", "early_finishing", "round_3",
            "rolling_stats", "momentum", "decline", "recent_damage",
            "time_decayed", "opponent_quality", "age_interactions",
            "youth_form", "recent_striking", "recent_grappling"
        ]
        
        for module_name in feature_modules:
            logger.info(f"\n{'='*60}")
            logger.info(f"Auditing: {module_name}")
            logger.info(f"{'='*60}")
            
            module_results = self.audit_feature_module(module_name, fighters)
            for key in results:
                results[key].extend(module_results.get(key, []))
        
        return results
    
    def audit_feature_module(self, module_name: str, fighters: List[Fighter]) -> Dict[str, List[str]]:
        """Audit a specific feature module"""
        issues = {
            "logical_errors": [],
            "edge_cases": [],
            "sanity_checks": [],
            "consistency_checks": [],
        }
        
        feature_func = FeatureRegistry.get_feature_function(module_name)
        if not feature_func:
            issues["logical_errors"].append(f"{module_name}: Feature function not found")
            return issues
        
        # Test with fighters
        for fighter in fighters[:10]:  # Test with first 10 fighters
            try:
                fight_history = self.feature_builder.get_fight_history(fighter.id)
                
                context = {
                    "fighter": fighter,
                    "fighter_id": fighter.id,
                    "fight_history": fight_history,
                    "rolling_windows": [3, 5],
                    "lambda_decay": 0.3,
                    "get_fighter_record": self.feature_builder.get_fighter_record,
                    "fight_stats_by_fight_id": {},
                }
                
                features = feature_func(context)
                
                # Run checks
                self._check_logical_errors(module_name, features, fighter, issues)
                self._check_edge_cases(module_name, features, fighter, fight_history, issues)
                self._check_sanity_checks(module_name, features, issues)
                self._check_consistency(module_name, features, fighter, fight_history, issues)
                
            except Exception as e:
                issues["logical_errors"].append(
                    f"{module_name} (fighter {fighter.id}): Error - {str(e)}"
                )
        
        return issues
    
    def _check_logical_errors(self, module_name: str, features: Dict, fighter: Fighter, issues: Dict):
        """Check for logical errors in feature calculations"""
        
        # 1. Check for backwards penalties (like opponent_quality_score bug)
        if "opponent_quality" in module_name:
            if "opponent_quality_score" in features:
                score = features["opponent_quality_score"]
                beaten_wr = features.get("avg_beaten_opponent_win_rate", 0)
                lost_wr = features.get("avg_lost_to_opponent_win_rate", 0)
                
                # If lost to elite fighters, score shouldn't be heavily negative
                if lost_wr > 0.7 and score < -0.2:
                    issues["logical_errors"].append(
                        f"{module_name}: Possible backwards penalty - lost to {lost_wr:.2%} "
                        f"win rate opponents but score is {score:.3f}"
                    )
        
        # 2. Check for division by zero issues
        for key, value in features.items():
            if isinstance(value, (int, float)):
                if np.isinf(value) or np.isnan(value):
                    issues["logical_errors"].append(
                        f"{module_name}: {key} has invalid value: {value}"
                    )
        
        # 3. Check for negative values where they shouldn't exist
        # Exclude difference/decline features which can legitimately be negative
        non_negative_features = [
            "win_rate", "accuracy", "finish_rate", "striking_accuracy",
            "takedown_accuracy", "defense", "opponent_quality_score"
        ]
        # Exclude features that are differences or declines (can be negative)
        exclude_patterns = ["diff", "decline", "vs_career", "trend"]
        for key in non_negative_features:
            if any(pattern in key.lower() for pattern in exclude_patterns):
                continue
            if key in features and features[key] < -0.1:  # Allow small negatives for rounding
                issues["logical_errors"].append(
                    f"{module_name}: {key} is negative ({features[key]:.3f}) but shouldn't be"
                )
    
    def _check_edge_cases(self, module_name: str, features: Dict, fighter: Fighter, 
                         fight_history: pd.DataFrame, issues: Dict):
        """Check edge cases"""
        
        # 1. Fighter with no fights
        if len(fight_history) == 0:
            # Should have default values, not errors
            for key, value in features.items():
                if value is None:
                    issues["edge_cases"].append(
                        f"{module_name}: {key} is None for fighter with no fights"
                    )
        
        # 2. Fighter with only wins
        if len(fight_history) > 0:
            all_wins = (fight_history["result"] == "win").all()
            if all_wins:
                # Check that loss-related features handle this
                loss_features = [k for k in features.keys() if "loss" in k.lower()]
                for key in loss_features:
                    if features[key] is None:
                        issues["edge_cases"].append(
                            f"{module_name}: {key} is None for fighter with only wins"
                        )
        
        # 3. Fighter with only losses
        if len(fight_history) > 0:
            all_losses = (fight_history["result"] == "loss").all()
            if all_losses:
                # Check that win-related features handle this
                win_features = [k for k in features.keys() if "win" in k.lower() and "loss" not in k.lower()]
                for key in win_features:
                    if features[key] is None:
                        issues["edge_cases"].append(
                            f"{module_name}: {key} is None for fighter with only losses"
                        )
    
    def _check_sanity_checks(self, module_name: str, features: Dict, issues: Dict):
        """Sanity checks for feature values"""
        
        # 1. Rates should be between 0 and 1 (but activity_rate is fights per year, can be > 1)
        rate_features = [k for k in features.keys() if "rate" in k.lower() or "accuracy" in k.lower()]
        # Exclude difference/decline features which can be negative
        exclude_patterns = ["diff", "decline", "vs_career", "trend", "activity_rate"]
        for key in rate_features:
            value = features[key]
            if isinstance(value, (int, float)):
                # Skip excluded patterns
                if any(pattern in key.lower() for pattern in exclude_patterns):
                    continue
                if value > 1.1:  # Allow small overflow for rounding
                    issues["sanity_checks"].append(
                        f"{module_name}: {key} = {value:.3f} (should be <= 1.0)"
                    )
                if value < -0.1:  # Allow small negatives
                    issues["sanity_checks"].append(
                        f"{module_name}: {key} = {value:.3f} (should be >= 0.0)"
                    )
        
        # 2. Counts should be non-negative integers (but averages can be floats)
        count_features = [k for k in features.keys() if any(x in k.lower() for x in ["count", "num", "wins", "losses"])]
        # Exclude averages - they should be floats
        count_features = [k for k in count_features if "avg" not in k.lower() and "mean" not in k.lower()]
        for key in count_features:
            value = features[key]
            if isinstance(value, (int, float)):
                if value < 0:
                    issues["sanity_checks"].append(
                        f"{module_name}: {key} = {value} (should be >= 0)"
                    )
                if isinstance(value, float) and value != int(value):
                    # Counts should be integers
                    if abs(value - int(value)) > 0.01:  # Allow small floating point errors
                        issues["sanity_checks"].append(
                            f"{module_name}: {key} = {value} (should be integer)"
                        )
    
    def _check_consistency(self, module_name: str, features: Dict, fighter: Fighter,
                          fight_history: pd.DataFrame, issues: Dict):
        """Check consistency between related features"""
        
        # 1. Win rate consistency
        if "win_rate" in features and "total_fights" in features:
            win_rate = features["win_rate"]
            total_fights = features["total_fights"]
            wins = features.get("wins", 0)
            
            if total_fights > 0:
                expected_rate = wins / total_fights
                if abs(win_rate - expected_rate) > 0.01:
                    issues["consistency_checks"].append(
                        f"{module_name}: win_rate ({win_rate:.3f}) doesn't match "
                        f"wins/total_fights ({wins}/{total_fights} = {expected_rate:.3f})"
                    )
        
        # 2. Strike rate consistency
        # Check each time window separately (_last_3, _lifetime)
        # Note: We only check features with explicit time windows, not base features
        time_windows = ["_last_3", "_lifetime"]
        
        for window in time_windows:
            # Head/Body/Leg rates should sum to ~1.0 (target area) for this time window
            target_area_rates = [
                k for k in features.keys() 
                if any(x in k for x in ["head_strike_rate", "body_strike_rate", "leg_strike_rate"])
                and k.endswith(window)  # Only match features with this specific suffix
            ]
            if len(target_area_rates) >= 3:
                total_rate = sum(features.get(k, 0) for k in target_area_rates)
                # Only check if we have all three and they're not all zero
                if total_rate > 0.1:  # Only check if there's actual data
                    if total_rate > 1.2 or total_rate < 0.8:
                        issues["consistency_checks"].append(
                            f"{module_name}: Target area strike rates (head+body+leg{window}) sum to {total_rate:.3f} (should be ~1.0)"
                        )
            
            # Distance/Clinch/Ground rates should sum to ~1.0 (position) for this time window
            position_rates = [
                k for k in features.keys()
                if any(x in k for x in ["distance_strike_rate", "clinch_strike_rate", "ground_strike_rate"])
                and k.endswith(window)  # Only match features with this specific suffix
            ]
            if len(position_rates) >= 3:
                total_rate = sum(features.get(k, 0) for k in position_rates)
                if total_rate > 0.1:  # Only check if there's actual data
                    if total_rate > 1.2 or total_rate < 0.8:
                        issues["consistency_checks"].append(
                            f"{module_name}: Position strike rates (distance+clinch+ground{window}) sum to {total_rate:.3f} (should be ~1.0)"
                        )
    
    def print_report(self, results: Dict[str, List[str]]):
        """Print audit report"""
        print("\n" + "="*80)
        print("FEATURE AUDIT REPORT")
        print("="*80)
        
        total_issues = sum(len(v) for v in results.values())
        print(f"\nTotal Issues Found: {total_issues}\n")
        
        for category, issues in results.items():
            if issues:
                print(f"\n{category.upper().replace('_', ' ')} ({len(issues)} issues):")
                print("-" * 80)
                for issue in issues[:20]:  # Limit to first 20 per category
                    print(f"  • {issue}")
                if len(issues) > 20:
                    print(f"  ... and {len(issues) - 20} more")
        
        if total_issues == 0:
            print("\n✓ No issues found! All features passed audit.")
        else:
            print(f"\n⚠️  Found {total_issues} potential issues. Review above.")
        
        print("\n" + "="*80)


def main():
    auditor = FeatureAuditor()
    results = auditor.audit_all_features()
    auditor.print_report(results)
    auditor.session.close()


if __name__ == "__main__":
    main()

