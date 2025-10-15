#!/bin/bash

# Unifero CLI API Deployment Script
# This script helps test the API locally before deploying to Vercel

echo "🚀 Unifero CLI API Deployment Helper"
echo "===================================="

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
else
    echo "❌ Virtual environment not active. Please run: source .venv/bin/activate"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Test API import
echo "🔍 Testing API import..."
python -c "from api import app; print('✅ API imports successfully')"

# Start the development server
echo "🌐 Starting development server..."
echo "API will be available at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn api:app --reload --host 0.0.0.0 --port 8000