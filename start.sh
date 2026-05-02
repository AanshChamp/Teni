#!/bin/bash

# ==========================================
# T.E.N.I — Jarvis Edition Startup (v2.1)
# ==========================================

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       T.E.N.I — JARVIS EDITION               ║"
echo "  ║   Teni Enhanced Neural Intelligence           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# Ensure we are in the project root
cd "$(dirname "$0")"

# 1. Virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔄 Activating virtual environment..."
source venv/bin/activate

# 2. Upgrade pip & Dependencies
echo "📚 Checking dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. Check for PortAudio (macOS specific for sounddevice)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! brew list portaudio &>/dev/null 2>&1; then
        echo "🔊 Installing PortAudio (required for audio)..."
        brew install portaudio -q || echo "⚠️  Please install portaudio manually: brew install portaudio"
    fi
fi

# 4. Launch Teni
echo "🚀 Initializing T.E.N.I Architecture..."
echo "🧠 Cognitive Loop: ONLINE"
echo "🎙  Live Engine: STANDBY"
echo "🖥  HUD Monitor: BOOTING"
echo ""

python3 main.py

deactivate
