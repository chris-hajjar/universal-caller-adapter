#!/bin/bash

# Universal Caller Adapter - Quick Start Script

set -e

echo "=================================="
echo "Universal Caller Adapter - Setup"
echo "=================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✓ Setup complete!"
echo ""
echo "To start the server:"
echo "  python main.py"
echo ""
echo "To run the demo (in another terminal):"
echo "  python demo.py"
echo ""
echo "Or run both automatically:"
echo "  ./run_demo.sh"
echo ""
