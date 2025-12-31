#!/bin/bash
# Helper script to deploy the UFC Analysis bundle via SCP

set -e

BUNDLE_DIR="ufc_analysis_bundle"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "UFC Analysis Bundle Deployment Helper"
echo "=========================================="
echo ""

# Check if bundle exists
if [ ! -d "$SCRIPT_DIR/$BUNDLE_DIR" ]; then
    echo -e "${RED}Error: Bundle directory not found!${NC}"
    echo "Please run: python3 bundle_for_deployment.py"
    exit 1
fi

# Get deployment target
if [ -z "$1" ]; then
    echo "Usage: $0 user@host:/path/to/destination"
    echo ""
    echo "Example:"
    echo "  $0 user@example.com:~/ufc_analysis"
    echo "  $0 user@192.168.1.100:/opt/ufc_analysis"
    exit 1
fi

DEST="$1"

echo -e "${YELLOW}Deploying bundle to: ${DEST}${NC}"
echo ""

# Confirm
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

# Get bundle size
BUNDLE_SIZE=$(du -sh "$SCRIPT_DIR/$BUNDLE_DIR" | cut -f1)
echo ""
echo -e "${YELLOW}Bundle size: ${BUNDLE_SIZE}${NC}"
echo "This may take a while depending on your connection speed..."
echo ""

# Deploy via SCP
echo -e "${GREEN}Copying bundle...${NC}"
scp -r "$SCRIPT_DIR/$BUNDLE_DIR" "$DEST"

echo ""
echo -e "${GREEN}✓ Bundle deployed successfully!${NC}"
echo ""
echo "Next steps on the remote machine:"
echo "  1. cd $(basename "$BUNDLE_DIR")"
echo "  2. chmod +x setup.sh"
echo "  3. ./setup.sh"
echo "  4. source .venv/bin/activate"
echo ""
echo "Then you can run:"
echo "  python xgboost_predict.py --fighter-1 \"Fighter Name\" --fighter-2 \"Fighter Name\" --model xgboost_model_with_2025"
echo "  python -m evaluation.preview_upcoming_fights --input data/predictions/upcoming_fights_ufc325.csv --model-name xgboost_model_with_2025 --symmetric"

