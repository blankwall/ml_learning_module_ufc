"""
Physical and Demographic Features
Age, height, weight, reach, stance, and related physical attributes
"""

import pandas as pd
from typing import Dict, Optional
from database.schema import Fighter


def extract_physical_features(fighter: Fighter) -> Dict[str, float]:
    """
    Extract physical and demographic features from a fighter.
    
    Pure function that takes a Fighter object and returns a dictionary of features.
    
    Args:
        fighter: Fighter database object
        
    Returns:
        Dictionary of physical features with snake_case names
    """
    age = fighter.age or 0
    height_cm = fighter.height_cm or 0
    weight_lbs = fighter.weight_lbs or 0
    reach_inches = fighter.reach_inches or 0
    stance = fighter.stance or ""
    
    features = {
        # Raw physical attributes
        "age": float(age),
        "height_cm": float(height_cm),
        "weight_lbs": float(weight_lbs),
        "reach_inches": float(reach_inches),
        
        # Age categories (binary indicators)
        "age_in_prime": 1.0 if 27 <= age <= 33 else 0.0,
        "age_past_prime": 1.0 if age > 34 else 0.0,
        
        # Stance indicators (one-hot encoded)
        "stance_orthodox": 1.0 if stance == "Orthodox" else 0.0,
        "stance_southpaw": 1.0 if stance == "Southpaw" else 0.0,
        "stance_switch": 1.0 if stance == "Switch" else 0.0,
    }
    
    return features

