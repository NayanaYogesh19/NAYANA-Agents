#!/bin/bash

echo "===================================="
echo "FAQ Optimizer Agent - Startup"
echo "===================================="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and fill in your API keys."
    echo
    exit 1
fi

echo
echo "Starting FAQ Optimizer Agent..."
echo "Server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo

# Start the server
python backend/main.py
