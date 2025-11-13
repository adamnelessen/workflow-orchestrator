#!/bin/bash
# Setup script for workflow-orchestrator

set -e  # Exit on error

echo "Setting up workflow-orchestrator environment..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "Setup complete! 🎉"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run with make commands:"
echo "  make install    - Install dependencies"
echo "  make reinstall  - Clean and reinstall everything"
echo "  make clean      - Remove virtual environment"
