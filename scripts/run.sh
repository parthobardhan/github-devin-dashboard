#!/bin/bash

# GitHub-Devin Dashboard Run Script
# This script starts the dashboard application

set -e

echo "Starting GitHub-Devin Integration Dashboard..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ".env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if required environment variables are set
echo "Checking configuration..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

required_vars = ['GITHUB_TOKEN', 'DEVIN_API_KEY', 'GITHUB_REPOS', 'APP_SECRET_KEY']
missing_vars = []

for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f'Missing required environment variables: {\", \".join(missing_vars)}')
    print('Please configure these in your .env file.')
    exit(1)
else:
    print('Configuration check passed')
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Start the application
echo "Starting the dashboard..."
echo "Dashboard will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Use uvicorn to run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
