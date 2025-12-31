#!/usr/bin/env python3
"""
Generate interactive HTML pages from backtest results.

Converts backtest CSV files into beautiful, interactive HTML reports
with charts and filters.
"""

import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime
import json


def generate_backtest_html(
    csv_path: Path,
    output_path: Path = None,
    title: str = None
) -> str:
    """
    Generate interactive HTML report from backtest CSV
    """
    df = pd.read_csv(csv_path)
    
    if output_path is None:
        output_path = csv_path.with_suffix('.html')
    
    if title is None:
        title = csv_path.stem.replace('_', ' ').title()
    
    # Calculate summary stats
    total_bets = len(df) if 'bet_placed' in df.columns else len(df[df.get('bet_ev', 0) > 0])
    total_staked = df.get('stake', df.get('flat_stake', 1)).sum() if 'stake' in df.columns else total_bets
    total_profit = df.get('profit', 0).sum() if 'profit' in df.columns else 0
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    
    wins = len(df[df.get('profit', 0) > 0]) if 'profit' in df.columns else 0
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    
    # Prepare data for charts (JSON)
    chart_data = {
        'dates': df.get('fight_date', []).tolist() if 'fight_date' in df.columns else [],
        'profits': df.get('profit', []).tolist() if 'profit' in df.columns else [],
        'cumulative': df.get('profit', []).cumsum().tolist() if 'profit' in df.columns else [],
        'evs': df.get('bet_ev', df.get('ev_f1', [])).tolist() if 'bet_ev' in df.columns or 'ev_f1' in df.columns else []
    }
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Backtest Results</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
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
            max-width: 1600px;
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
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f5f5f5;
            border-bottom: 3px solid #d32f2f;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #d32f2f;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value.positive {{
            color: #28a745;
        }}
        
        .stat-value.negative {{
            color: #dc3545;
        }}
        
        .charts-container {{
            padding: 30px;
        }}
        
        .chart-section {{
            margin-bottom: 40px;
        }}
        
        .chart-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }}
        
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .table-container {{
            padding: 30px;
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        
        th {{
            background: #d32f2f;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .positive {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .negative {{
            color: #dc3545;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div style="margin-top: 10px; opacity: 0.9;">Backtest Performance Analysis</div>
            <div style="margin-top: 10px; opacity: 0.8; font-size: 0.9em;">
                Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-value {'positive' if total_profit > 0 else 'negative' if total_profit < 0 else ''}">
                    {total_profit:+.2f}
                </div>
                <div class="stat-label">Total Profit (units)</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value {'positive' if roi > 0 else 'negative' if roi < 0 else ''}">
                    {roi:+.2f}%
                </div>
                <div class="stat-label">ROI</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value">{win_rate:.1f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value">{total_bets}</div>
                <div class="stat-label">Total Bets</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value">{total_staked:.2f}</div>
                <div class="stat-label">Total Staked</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-value">{wins}</div>
                <div class="stat-label">Winning Bets</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-section">
                <div class="chart-title">Cumulative Profit Over Time</div>
                <div class="chart-container">
                    <div id="cumulative-chart"></div>
                </div>
            </div>
            
            <div class="chart-section">
                <div class="chart-title">Profit Distribution</div>
                <div class="chart-container">
                    <div id="distribution-chart"></div>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <h2 style="margin-bottom: 20px;">Detailed Results</h2>
            <div style="overflow-x: auto;">
                <table id="results-table">
                    <thead>
                        <tr>
                            {''.join([f'<th>{col.replace("_", " ").title()}</th>' for col in df.columns[:10]])}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([
                            f'<tr>{"".join([f"<td>{row[col]}</td>" for col in df.columns[:10]])}</tr>'
                            for _, row in df.head(100).iterrows()
                        ])}
                    </tbody>
                </table>
            </div>
            <p style="margin-top: 15px; color: #666;">
                Showing first 100 rows. Total: {len(df)} rows
            </p>
        </div>
    </div>
    
    <script>
        // Chart data
        const data = {json.dumps(chart_data)};
        
        // Cumulative profit chart
        const cumulativeTrace = {{
            x: Array.from({{length: data.cumulative.length}}, (_, i) => i + 1),
            y: data.cumulative,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Cumulative Profit',
            line: {{color: data.cumulative[data.cumulative.length - 1] >= 0 ? '#28a745' : '#dc3545', width: 3}},
            marker: {{size: 4}}
        }};
        
        Plotly.newPlot('cumulative-chart', [cumulativeTrace], {{
            title: 'Cumulative Profit Over Time',
            xaxis: {{title: 'Bet Number'}},
            yaxis: {{title: 'Cumulative Profit (units)'}},
            hovermode: 'closest',
            margin: {{l: 60, r: 30, t: 40, b: 50}}
        }}, {{responsive: true}});
        
        // Profit distribution chart
        const distributionTrace = {{
            x: data.profits,
            type: 'histogram',
            name: 'Profit Distribution',
            marker: {{
                color: data.profits.map(p => p >= 0 ? '#28a745' : '#dc3545')
            }},
            nbinsx: 30
        }};
        
        Plotly.newPlot('distribution-chart', [distributionTrace], {{
            title: 'Profit/Loss Distribution',
            xaxis: {{title: 'Profit per Bet (units)'}},
            yaxis: {{title: 'Frequency'}},
            margin: {{l: 60, r: 30, t: 40, b: 50}}
        }}, {{responsive: true}});
    </script>
</body>
</html>"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Generate HTML from backtest CSV')
    parser.add_argument('csv_path', type=Path, help='Path to backtest CSV file')
    parser.add_argument('-o', '--output', type=Path, help='Output HTML path')
    parser.add_argument('-t', '--title', help='Custom title')
    
    args = parser.parse_args()
    
    if not args.csv_path.exists():
        print(f"Error: File not found: {args.csv_path}")
        return
    
    output_path = generate_backtest_html(
        args.csv_path,
        args.output,
        args.title
    )
    print(f"Generated: {output_path}")


if __name__ == '__main__':
    main()

