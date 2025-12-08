"""
Feature engineering module for UFC fight prediction

REFACTORED: Modular feature system with clean separation of concerns.
"""

# Main interfaces (backward compatible)
from .fighter_features import FighterFeatureExtractor
from .matchup_features import MatchupFeatureExtractor
from .feature_pipeline import FeaturePipeline

# New modular system
from .registry import FeatureBuilder, FeatureRegistry

# Feature modules (for direct use if needed)
from . import physical
from . import striking
from . import grappling
from . import experiential
from . import time_based
from . import opponent_quality
from . import utils

__all__ = [
    # Main interfaces
    'FighterFeatureExtractor',
    'MatchupFeatureExtractor',
    'FeaturePipeline',
    # New modular system
    'FeatureBuilder',
    'FeatureRegistry',
    # Feature modules
    'physical',
    'striking',
    'grappling',
    'experiential',
    'time_based',
    'opponent_quality',
    'utils',
]

