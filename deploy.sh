#!/bin/bash

# Simple setup and run script for arXiv Paper Search (for local testing)

echo "Setting up arXiv Paper Search locally..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it and try again."
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

# Install/Upgrade dependencies
echo "Installing/Updating dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete."
echo "To run the application, you can now use:"
echo "flask run"
echo "or"
echo "python run.py"
echo ""
echo "For production, ensure a WSGI server like Gunicorn is used and managed by a process supervisor (e.g., systemd), as detailed in README.md."

# Deactivate virtual environment (optional, as script ends)
# deactivate 