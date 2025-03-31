#!/bin/bash
# Installation script for Governance Trading Bot

# Set up virtual environment
echo "Creating virtual environment..."
python -m venv venv
source venv/bin/activate

# Update pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies and the package
echo "Installing package in development mode..."
pip install -e .

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating sample .env file..."
    cp proposal_revamp/.env .env
    echo "Please edit the .env file with your actual credentials."
fi

# Check if coin.json and precision.json files exist in root
if [ ! -f "coin.json" ]; then
    echo "Copying coin.json to root directory..."
    cp proposal_revamp/exchange/coin.json ./coin.json
fi

if [ ! -f "precision.json" ]; then
    echo "Copying precision.json to root directory..."
    cp proposal_revamp/exchange/precision.json ./precision.json
fi

# Create data directory if not exists
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

echo ""
echo "Installation complete!"
echo "To activate the environment: source venv/bin/activate"
echo "To run the bot: python -m proposal_revamp"
echo "Or use the command: governance-bot"
echo "" 