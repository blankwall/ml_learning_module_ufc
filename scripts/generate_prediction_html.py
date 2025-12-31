#!/usr/bin/env python3
"""
Generate beautiful HTML pages from prediction CSV files.

Converts data/predictions/*.csv files into standalone HTML pages
that can be hosted statically (GitHub Pages, Netlify, etc.)
"""

import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime
from typing import Optional


def format_odds(odds: float) -> str:
    """Format American odds for display"""
    if pd.isna(odds):
        return "N/A"
    odds = float(odds)
    if odds > 0:
        return f"+{int(odds)}"
    return str(int(odds))


def format_probability(prob: float) -> str:
    """Format probability as percentage"""
    if pd.isna(prob):
        return "N/A"
    return f"{float(prob) * 100:.1f}%"


def format_ev(ev: float) -> str:
    """Format expected value"""
    if pd.isna(ev):
        return "N/A"
    ev = float(ev)
    color = "green" if ev > 0 else "red" if ev < 0 else "gray"
    sign = "+" if ev > 0 else ""
    return f'<span style="color: {color}; font-weight: bold;">{sign}{ev:.3f}</span>'


def generate_prediction_html(
    csv_path: Path,
    output_path: Optional[Path] = None,
    title: Optional[str] = None
) -> str:
    """
    Generate HTML page from prediction CSV
    
    Args:
        csv_path: Path to input CSV file
        output_path: Path to output HTML file (default: same name as CSV)
        title: Custom title (default: derived from filename)
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Determine output path
    if output_path is None:
        output_path = csv_path.with_suffix('.html')
    
    # Generate title
    if title is None:
        title = csv_path.stem.replace('_', ' ').title()
    
    # Detect columns (flexible - handle different CSV formats)
    has_model_pred = 'model_p_f1_pct' in df.columns or 'model_prob_f1' in df.columns
    has_odds = 'fighter_1_odds' in df.columns
    has_ev = 'ev_f1' in df.columns or 'bet_ev' in df.columns
    has_results = 'profit' in df.columns or 'result' in df.columns
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - UFC Predictions</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #d32f2f 0%, #c62828 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .header .meta {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-top: 10px;
        }}
        
        .fights-container {{
            padding: 30px;
        }}
        
        .fight-card {{
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .fight-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .fight-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #ddd;
        }}
        
        .fighters {{
            display: flex;
            align-items: center;
            gap: 20px;
            flex: 1;
        }}
        
        .fighter {{
            flex: 1;
            text-align: center;
        }}
        
        .fighter-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #d32f2f;
            margin-bottom: 8px;
        }}
        
        .vs {{
            font-size: 1.2em;
            font-weight: bold;
            color: #666;
        }}
        
        .fight-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .detail-box {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #d32f2f;
        }}
        
        .detail-label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .detail-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }}
        
        .probability-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
            position: relative;
        }}
        
        .probability-fill {{
            height: 100%;
            background: linear-gradient(90deg, #d32f2f 0%, #f44336 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .bet-recommendation {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .bet-recommendation.positive {{
            background: #d4edda;
            border-color: #28a745;
        }}
        
        .bet-recommendation.negative {{
            background: #f8d7da;
            border-color: #dc3545;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f5f5f5;
            border-top: 3px solid #d32f2f;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #d32f2f;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
        }}
        
        @media (max-width: 768px) {{
            .fighters {{
                flex-direction: column;
            }}
            
            .vs {{
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">UFC Fight Predictions</div>
            <div class="meta">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>
        
        <div class="summary-stats">
            <div class="stat-item">
                <div class="stat-value">{len(df)}</div>
                <div class="stat-label">Total Fights</div>
            </div>"""
    
    # Add summary stats if available
    if has_model_pred:
        model_col = 'model_p_f1_pct' if 'model_p_f1_pct' in df.columns else 'model_prob_f1'
        high_confidence = len(df[(df[model_col] > 0.65) | (df[model_col] < 0.35)])
        html += f"""
            <div class="stat-item">
                <div class="stat-value">{high_confidence}</div>
                <div class="stat-label">High Confidence</div>
            </div>"""
    
    if has_ev:
        ev_col = 'ev_f1' if 'ev_f1' in df.columns else 'bet_ev'
        positive_ev = len(df[df[ev_col] > 0])
        html += f"""
            <div class="stat-item">
                <div class="stat-value">{positive_ev}</div>
                <div class="stat-label">Positive EV Bets</div>
            </div>"""
    
    if has_results:
        profit_col = 'profit' if 'profit' in df.columns else 'result'
        if profit_col in df.columns:
            total_profit = df[profit_col].sum()
            html += f"""
            <div class="stat-item">
                <div class="stat-value">{total_profit:.2f}</div>
                <div class="stat-label">Total Profit</div>
            </div>"""
    
    html += """
        </div>
        
        <div class="fights-container">"""
    
    # Generate fight cards
    for idx, row in df.iterrows():
        f1_name = row.get('fighter_1_name', row.get('f1_name', 'Fighter 1'))
        f2_name = row.get('fighter_2_name', row.get('f2_name', 'Fighter 2'))
        
        # Get probabilities
        if 'model_p_f1_pct' in df.columns:
            p_f1 = row['model_p_f1_pct'] / 100.0
            p_f2 = row.get('model_p_f2_pct', 1 - p_f1) / 100.0
        elif 'model_prob_f1' in df.columns:
            p_f1 = row['model_prob_f1']
            p_f2 = row.get('model_prob_f2', 1 - p_f1)
        else:
            p_f1 = p_f2 = None
        
        # Get odds
        f1_odds = row.get('fighter_1_odds', row.get('f1_odds', None))
        f2_odds = row.get('fighter_2_odds', row.get('f2_odds', None))
        
        # Get EV
        ev_f1 = row.get('ev_f1', None)
        ev_f2 = row.get('ev_f2', None)
        bet_ev = row.get('bet_ev', None)
        
        # Get bet recommendation
        bet_name = row.get('bet_name', None)
        bet_side = row.get('bet_side', None)
        
        html += f"""
            <div class="fight-card">
                <div class="fight-header">
                    <div class="fighters">
                        <div class="fighter">
                            <div class="fighter-name">{f1_name}</div>
                        </div>
                        <div class="vs">VS</div>
                        <div class="fighter">
                            <div class="fighter-name">{f2_name}</div>
                        </div>
                    </div>
                </div>
                
                <div class="fight-details">"""
        
        # Model predictions
        if p_f1 is not None:
            html += f"""
                    <div class="detail-box">
                        <div class="detail-label">Model Prediction</div>
                        <div class="detail-value">{f1_name}: {format_probability(p_f1)}</div>
                        <div class="detail-value">{f2_name}: {format_probability(p_f2)}</div>
                        <div class="probability-bar">
                            <div class="probability-fill" style="width: {p_f1 * 100}%">
                                {format_probability(p_f1)}
                            </div>
                        </div>
                    </div>"""
        
        # Odds
        if f1_odds is not None and not pd.isna(f1_odds):
            html += f"""
                    <div class="detail-box">
                        <div class="detail-label">Market Odds</div>
                        <div class="detail-value">{f1_name}: {format_odds(f1_odds)}</div>
                        <div class="detail-value">{f2_name}: {format_odds(f2_odds)}</div>
                    </div>"""
        
        # Expected Value
        if ev_f1 is not None and not pd.isna(ev_f1):
            html += f"""
                    <div class="detail-box">
                        <div class="detail-label">Expected Value</div>
                        <div class="detail-value">{f1_name}: {format_ev(ev_f1)}</div>
                        <div class="detail-value">{f2_name}: {format_ev(ev_f2)}</div>
                    </div>"""
        elif bet_ev is not None and not pd.isna(bet_ev):
            html += f"""
                    <div class="detail-box">
                        <div class="detail-label">Bet EV</div>
                        <div class="detail-value">{format_ev(bet_ev)}</div>
                    </div>"""
        
        # Bet recommendation
        if bet_name is not None:
            ev_value = bet_ev if bet_ev is not None else (ev_f1 if ev_f1 and ev_f1 > 0 else ev_f2)
            rec_class = "positive" if ev_value and ev_value > 0 else "negative" if ev_value and ev_value < 0 else ""
            html += f"""
                    <div class="bet-recommendation {rec_class}">
                        <strong>Recommended Bet:</strong> {bet_name} ({bet_side if bet_side else ''})
                        {f'<br>EV: {format_ev(ev_value)}' if ev_value is not None else ''}
                    </div>"""
        
        # Results (if available)
        if 'profit' in df.columns and not pd.isna(row.get('profit')):
            profit = row['profit']
            profit_class = "positive" if profit > 0 else "negative"
            html += f"""
                    <div class="bet-recommendation {profit_class}">
                        <strong>Result:</strong> Profit: {profit:.2f} units
                    </div>"""
        
        html += """
                </div>
            </div>"""
    
    html += """
        </div>
    </div>
</body>
</html>"""
    
    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Generate HTML from prediction CSV')
    parser.add_argument('csv_path', type=Path, help='Path to prediction CSV file')
    parser.add_argument('-o', '--output', type=Path, help='Output HTML path (default: same as CSV with .html)')
    parser.add_argument('-t', '--title', help='Custom title for the page')
    parser.add_argument('--all', action='store_true', help='Process all CSV files in data/predictions/')
    
    args = parser.parse_args()
    
    if args.all:
        predictions_dir = Path('data/predictions')
        csv_files = list(predictions_dir.glob('*.csv'))
        print(f"Found {len(csv_files)} CSV files")
        
        for csv_file in csv_files:
            if 'with_model' in csv_file.name or 'upcoming' in csv_file.name:
                print(f"Processing {csv_file.name}...")
                output = csv_file.with_suffix('.html')
                generate_prediction_html(csv_file, output)
                print(f"  → {output}")
    else:
        if not args.csv_path.exists():
            print(f"Error: File not found: {args.csv_path}")
            return
        
        output_path = generate_prediction_html(
            args.csv_path,
            args.output,
            args.title
        )
        print(f"Generated: {output_path}")


if __name__ == '__main__':
    main()

