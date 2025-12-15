#!/usr/bin/env python3
"""
Validation script for testing predictions against expected outcomes
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import re
from typing import List, Tuple, Dict

# Test cases: (fighter_1, fighter_2, expected_f1_percentage)
TEST_CASES = [
    ("Grant Dawson", "Manuel Torres", 60.0),
    ("Fares Ziam", "Nazim Sadykhov", 50.0),
    ("Maycee Barber", "Karine Silva", 60.0),
    ("Anthony Hernandez", "Sean Strickland", 80.0),
    ("Tatsuro Taira", "Brandon Moreno", 50.0),
]


def run_prediction(fighter_1: str, fighter_2: str, quick_mode: bool = False) -> Dict[str, float]:
    """
    Run prediction and extract percentages.
    
    Args:
        fighter_1: First fighter name
        fighter_2: Second fighter name
        quick_mode: If True, suppress verbose output
        
    Returns:
        Dictionary with fighter names and percentages
    """
    cmd = [
        sys.executable,
        "xgboost_predict.py",
        "--fighter-1", fighter_1,
        "--fighter-2", fighter_2,
        "--quiet"  # Always use quiet mode for validation
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout + result.stderr
        print(output)
        # Extract percentages from output
        # Pattern: "Fighter Name: XX.X% chance to win"
        pattern = r'([^:]+):\s+(\d+\.\d+)%\s+chance to win'
        matches = re.findall(pattern, output)
        
        if len(matches) >= 2:
            f1_name = matches[0][0].strip()
            f1_pct = float(matches[0][1])
            f2_name = matches[1][0].strip()
            f2_pct = float(matches[1][1])
            
            return {
                "f1_name": f1_name,
                "f1_pct": f1_pct,
                "f2_name": f2_name,
                "f2_pct": f2_pct,
            }
        else:
            # Fallback: try to find percentages in any format
            pct_pattern = r'(\d+\.\d+)%\s+chance to win'
            percentages = re.findall(pct_pattern, output)
            print(percentages)
            if len(percentages) >= 2:
                return {
                    "f1_name": fighter_1,
                    "f1_pct": float(percentages[0]),
                    "f2_name": fighter_2,
                    "f2_pct": float(percentages[1]),
                }
            
            return {
                "f1_name": fighter_1,
                "f1_pct": 0.0,
                "f2_name": fighter_2,
                "f2_pct": 0.0,
                "error": "Could not parse percentages"
            }
    except Exception as e:
        return {
            "f1_name": fighter_1,
            "f1_pct": 0.0,
            "f2_name": fighter_2,
            "f2_pct": 0.0,
            "error": str(e)
        }


def validate_predictions(quick_mode: bool = False):
    """
    Run all test cases and compare predicted vs expected.
    
    Args:
        quick_mode: If True, only show percentages (suppress verbose output)
    """
    if not quick_mode:
        print("\n" + "="*80)
        print("PREDICTION VALIDATION")
        print("="*80)
        print()
    
    results = []
    
    for fighter_1, fighter_2, expected_f1_pct in TEST_CASES:
        if not quick_mode:
            print(f"Testing: {fighter_1} vs {fighter_2} (Expected: {fighter_1} {expected_f1_pct}%)")
            print("  Running prediction...", end=" ", flush=True)
        
        prediction = run_prediction(fighter_1, fighter_2, quick_mode)
        
        if "error" in prediction:
            if not quick_mode:
                print(f"ERROR: {prediction['error']}")
            results.append({
                "f1": fighter_1,
                "f2": fighter_2,
                "predicted_f1": 0.0,
                "expected_f1": expected_f1_pct,
                "diff": -expected_f1_pct,
                "error": prediction["error"]
            })
            continue
        
        predicted_f1_pct = prediction["f1_pct"]
        diff = predicted_f1_pct - expected_f1_pct
        
        results.append({
            "f1": fighter_1,
            "f2": fighter_2,
            "predicted_f1": predicted_f1_pct,
            "expected_f1": expected_f1_pct,
            "diff": diff,
        })
        
        if not quick_mode:
            print(f"Done! Predicted: {predicted_f1_pct:.1f}% (Diff: {diff:+.1f}%)")
    
    # Print summary table
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print()
    print(f"{'Fighter 1':<25} {'Fighter 2':<25} {'Predicted':<12} {'Expected':<12} {'Diff':<10}")
    print("-" * 80)
    
    total_diff = 0.0
    valid_cases = 0
    
    for result in results:
        if "error" in result:
            print(f"{result['f1']:<25} {result['f2']:<25} {'ERROR':<12} {result['expected_f1']:<12.1f} {'N/A':<10}")
        else:
            diff_str = f"{result['diff']:+.1f}%"
            # Color code: green if within 5%, yellow if within 10%, red if >10%
            if abs(result['diff']) <= 5.0:
                diff_str = f"✓ {diff_str}"
            elif abs(result['diff']) <= 10.0:
                diff_str = f"⚠ {diff_str}"
            else:
                diff_str = f"✗ {diff_str}"
            
            print(f"{result['f1']:<25} {result['f2']:<25} {result['predicted_f1']:<12.1f} {result['expected_f1']:<12.1f} {diff_str:<10}")
            total_diff += abs(result['diff'])
            valid_cases += 1
    
    print("-" * 80)
    
    if valid_cases > 0:
        avg_diff = total_diff / valid_cases
        print(f"\nAverage absolute difference: {avg_diff:.1f}%")
        print(f"Total test cases: {len(results)}")
        print(f"Valid predictions: {valid_cases}")
    
    print("="*80)
    
    # Quick mode: also print just percentages for easy copy-paste
    if quick_mode:
        print("\nQUICK OUTPUT (percentages only):")
        for result in results:
            if "error" not in result:
                print(f"{result['f1']} vs {result['f2']}: {result['predicted_f1']:.1f}% | {result['expected_f1']:.1f}% (diff: {result['diff']:+.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate predictions against expected outcomes")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: only show percentages, suppress verbose output"
    )
    
    args = parser.parse_args()
    
    validate_predictions(quick_mode=args.quick)

