#!/bin/bash

echo "Discord Bot Setup Script"
echo "======================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ Found: $python_version"
else
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo -e "\nCreating virtual environment..."
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo -e "\nActivating virtual environment..."
source venv/bin/activate

# Install dependencies
echo -e "\nInstalling dependencies..."
pip install -r requirements.txt

# Check for .env file
echo -e "\nChecking configuration..."
if [[ ! -f ".env" ]]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "Please edit .env and add your:"
    echo "  - Discord bot token"
    echo "  - Discord channel ID"
    echo "  - Google Cloud credentials path"
else
    echo "✅ .env file exists"
fi

# Run manual tests
echo -e "\n======================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Run: python manual_test.py"
echo "3. When ready, run: python main.py"
echo ""
echo "To activate the virtual environment in the future:"
echo "source venv/bin/activate"