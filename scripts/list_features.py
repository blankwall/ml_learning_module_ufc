"""
Script to list all features extracted by the feature pipeline
"""

def get_all_features():
    """
    Returns a comprehensive list of all features extracted by the pipeline
    """
    
    # Fighter 1 and Fighter 2 features (same set for both)
    fighter_features = {
        'Basic Physical/Demographic Features': [
            'height_cm',
            'weight_lbs',
            'reach_inches',
            'age',
            'stance_orthodox',
            'stance_southpaw',
            'stance_switch',
        ],
        
        'Career Statistics': [
            'total_fights',
            'wins',
            'losses',
            'draws',
            'win_rate',
            'sig_strikes_landed_per_min',
            'striking_accuracy',
            'sig_strikes_absorbed_per_min',
            'striking_defense',
            'striking_differential',
            'takedown_avg_per_15min',
            'takedown_accuracy',
            'takedown_defense',
            'submission_avg_per_15min',
        ],
        
        'Fight History Features': [
            'has_fight_history',
            'finish_rate',
            'ko_rate',
            'submission_rate',
            'decision_rate',
            'title_fight_experience',
            'avg_fight_duration_rounds',
        ],
        
        'Rolling Statistics (last 3, 5, 10 fights)': [
            'win_rate_last_3',
            'finish_rate_last_3',
            'win_rate_last_5',
            'finish_rate_last_5',
            'win_rate_last_10',
            'finish_rate_last_10',
        ],
        
        'Momentum Features': [
            'current_win_streak',
            'current_loss_streak',
            'fights_in_last_year',
            'activity_rate',
        ],
        
        'Round 3 Performance (Cardio Proxy)': [
            'round_3_fight_rate',
            'round_3_win_rate',
            'round_3_finish_rate',
            'round_3_performance_score',
        ],
    }
    
    # Differential features (Fighter 1 - Fighter 2)
    differential_features = {
        'Physical Advantages': [
            'height_advantage',
            'reach_advantage',
            'age_difference',
        ],
        
        'Experience Advantages': [
            'experience_difference',
            'win_rate_difference',
        ],
        
        'Striking Advantages': [
            'striking_output_diff',
            'striking_accuracy_diff',
            'striking_defense_diff',
            'striking_differential',  # F1 output vs F2 defense (interaction)
        ],
        
        'Grappling Advantages': [
            'takedown_ability_diff',
            'takedown_defense_diff',
            'takedown_matchup',  # F1 accuracy vs F2 defense (interaction)
        ],
        
        'Recent Form': [
            'recent_form_diff',
            'win_streak_diff',
            'finish_rate_diff',
        ],
        
        'Round 3 Performance': [
            'round_3_performance_diff',
            'round_3_win_rate_diff',
        ],
    }
    
    # Style matchup features
    style_matchup_features = [
        'both_strikers',
        'both_grapplers',
        'striker_vs_grappler',
        'orthodox_vs_orthodox',
        'southpaw_vs_southpaw',
        'orthodox_vs_southpaw',
        'both_finishers',
        'power_striker_matchup',
        'defensive_fight',
    ]
    
    # Common opponent features
    common_opponent_features = [
        'num_common_opponents',
        'common_opponent_performance_diff',
    ]
    
    return {
        'fighter_features': fighter_features,
        'differential_features': differential_features,
        'style_matchup_features': style_matchup_features,
        'common_opponent_features': common_opponent_features,
    }


def print_feature_list():
    """Print a formatted list of all features"""
    features = get_all_features()
    
    print("=" * 80)
    print("COMPLETE FEATURE LIST")
    print("=" * 80)
    print()
    
    # Fighter features (prefixed with f1_ and f2_)
    print("FIGHTER FEATURES (each feature is prefixed with 'f1_' and 'f2_' for each fighter)")
    print("-" * 80)
    
    for category, feature_list in features['fighter_features'].items():
        print(f"\n{category}:")
        for feature in feature_list:
            print(f"  - f1_{feature}")
            print(f"  - f2_{feature}")
    
    print("\n" + "=" * 80)
    print("DIFFERENTIAL FEATURES (Fighter 1 - Fighter 2)")
    print("-" * 80)
    
    for category, feature_list in features['differential_features'].items():
        print(f"\n{category}:")
        for feature in feature_list:
            print(f"  - {feature}")
    
    print("\n" + "=" * 80)
    print("STYLE MATCHUP FEATURES")
    print("-" * 80)
    
    for feature in features['style_matchup_features']:
        print(f"  - {feature}")
    
    print("\n" + "=" * 80)
    print("COMMON OPPONENT FEATURES")
    print("-" * 80)
    
    for feature in features['common_opponent_features']:
        print(f"  - {feature}")
    
    print("\n" + "=" * 80)
    
    # Count total features
    total_fighter_features = sum(len(f) for f in features['fighter_features'].values())
    total_differential = sum(len(f) for f in features['differential_features'].values())
    total_style = len(features['style_matchup_features'])
    total_common = len(features['common_opponent_features'])
    
    # Each fighter feature appears twice (f1_ and f2_)
    total_features = (total_fighter_features * 2) + total_differential + total_style + total_common
    
    print(f"\nTOTAL FEATURES: {total_features}")
    print(f"  - Fighter features (f1_ + f2_): {total_fighter_features * 2}")
    print(f"  - Differential features: {total_differential}")
    print(f"  - Style matchup features: {total_style}")
    print(f"  - Common opponent features: {total_common}")
    print()


def get_flat_feature_list():
    """Get a flat list of all feature names as they appear in the dataset"""
    features = get_all_features()
    
    feature_list = []
    
    # Add fighter features with f1_ and f2_ prefixes
    for category_features in features['fighter_features'].values():
        for feature in category_features:
            feature_list.append(f'f1_{feature}')
            feature_list.append(f'f2_{feature}')
    
    # Add differential features
    for category_features in features['differential_features'].values():
        feature_list.extend(category_features)
    
    # Add style matchup features
    feature_list.extend(features['style_matchup_features'])
    
    # Add common opponent features
    feature_list.extend(features['common_opponent_features'])
    
    return feature_list


if __name__ == '__main__':
    print_feature_list()
    
    print("\n" + "=" * 80)
    print("FLAT FEATURE LIST (as they appear in dataset)")
    print("=" * 80)
    print()
    
    flat_list = get_flat_feature_list()
    for i, feature in enumerate(flat_list, 1):
        print(f"{i:3d}. {feature}")

