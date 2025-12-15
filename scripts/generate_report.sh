#!/bin/bash
# Quick script to generate HTML evaluation report

# Find the most recent eval_data CSV
LATEST_EVAL=$(ls -t reports/eval_data_*.csv 2>/dev/null | head -n 1)

if [ -z "$LATEST_EVAL" ]; then
    echo "❌ No evaluation data found in reports/"
    echo "Run this first:"
    echo "  python -m evaluation.evaluate_model \\"
    echo "    --data-path data/processed/training_data.csv \\"
    echo "    --odds-path ufc_2025_odds.csv \\"
    echo "    --min-year 2025 \\"
    echo "    --output-dir reports"
    exit 1
fi

echo "📊 Found evaluation data: $LATEST_EVAL"
echo "🔨 Generating HTML report..."

python -m evaluation.generate_html_report \
  --eval-data "$LATEST_EVAL" \
  --output reports/model_evaluation_2025.html \
  --min-year 2025

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Report generated!"
    echo "🌐 Open in browser:"
    echo "   file://$(pwd)/reports/model_evaluation_2025.html"
    echo ""
    
    # Try to open in default browser (macOS)
    if command -v open &> /dev/null; then
        echo "🚀 Opening in browser..."
        open reports/model_evaluation_2025.html
    fi
fi

