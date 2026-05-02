#!/bin/bash

# ==========================================
# T.E.N.I — Jarvis Edition Startup
# ==========================================

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       T.E.N.I — JARVIS EDITION               ║"
echo "  ║   Teni Enhanced Neural Intelligence           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# 1. Virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔄 Activating virtual environment..."
source venv/bin/activate

# 2. Dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt -q 2>/dev/null

# 3. Check for portaudio (needed by sounddevice on macOS)
if ! brew list portaudio &>/dev/null 2>&1; then
    echo "🔊 Installing PortAudio for audio streaming..."
    brew install portaudio 2>/dev/null || echo "⚠️  Install portaudio manually: brew install portaudio"
fi

# 4. Launch Teni
echo "🚀 Launching Teni AI..."
echo ""
python3 main.py

deactivate
