#!/usr/bin/env python3
"""
T.E.N.I — JARVIS EDITION (v2.0)
==============================
Persistent, Context-Aware AI System
PyQt6 HUD + Gemini Live Audio + Cognitive Loop
"""

import os
import sys
import signal
import threading
from ui.hud import TeniHUD
from core.cognitive_loop import CognitiveLoop
from core.personality import PersonalityEngine
from execution import ExecutionEngine
from memory.memory import Memory
from voice.live_engine import LiveEngine

class TeniSystem:
    def __init__(self):
        # 1. Core Data & Systems
        self.memory = Memory()
        self.personality = PersonalityEngine()
        self.executor = ExecutionEngine()
        
        # 2. UI (PyQt6)
        self.hud = TeniHUD()
        
        # 3. Intelligence (Cognitive Loop)
        self.brain = CognitiveLoop(
            memory=self.memory, 
            personality=self.personality, 
            ui=self.hud
        )
        
        # 4. Voice (Gemini Live)
        self.voice = LiveEngine(
            executor=self.executor,
            ui=self.hud
        )
        
        # Binding
        self.hud.on_text_command = self.voice.send_text
        
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, *_):
        print("\n🔴 Teni Shutting Down...")
        self.voice.stop()
        os._exit(0)

    def run(self):
        # 1. Validation
        from config import Config
        if not Config.GEMINI_API_KEY:
            print("\n❌ ERROR: GEMINI_API_KEY not found!")
            print("Please create a '.env' file in the project root and add:")
            print("GEMINI_API_KEY=your_key_here")
            print("\nRefer to .env.template for guidance.")
            os._exit(1)

        print("🚀 T.E.N.I Booting...")
        
        # Start Background Intelligence
        self.brain.start()
        
        # Start Voice Engine
        threading.Thread(target=self.voice.start, daemon=True).start()
        
        # Start UI (Blocks)
        self.hud.run()

if __name__ == "__main__":
    TeniSystem().run()
