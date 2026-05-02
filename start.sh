#!/bin/bash

# ==========================================
# Teni AI System - Startup Script
# ==========================================

echo "🚀 Starting Teni AI System..."

# 1. Check and activate Python Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "🔄 Activating virtual environment..."
source venv/bin/activate

# 2. Install dependencies if needed
echo "📚 Checking dependencies..."
pip install -r requirements.txt -q

# 3. Start Backend / CLI
echo "🧠 Starting Teni Agent..."
# Once we build the UI overlay (frontend), we will start it here in the background!
# For now, Teni runs as the primary terminal application.

python3 main.py

# Deactivate environment on exit
deactivate
