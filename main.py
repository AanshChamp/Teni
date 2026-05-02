#!/usr/bin/env python3
"""
Teni AI — Jarvis Edition
========================
Premium voice-first macOS AI assistant.
Gemini Live Audio + HUD + Biometrics + Full System Control.
"""

import os
import sys
import json
import signal
import threading

from config import Config
from execution import ExecutionEngine
from memory.memory import Memory
from utils.logger import TeniLogger
from security.permission_layer import PermissionLayer
from security.input_sanitizer import InputSanitizer
from core.personality import PersonalityEngine
from daemon.heartbeat import Heartbeat
from core.autonomy import AutonomyEngine


class TeniSystem:
    """Main Teni AI system — orchestrates HUD, voice, and execution."""

    def __init__(self):
        # Core systems
        self.executor = ExecutionEngine()
        self.memory = Memory()
        self.logger = TeniLogger()
        self.permission_layer = PermissionLayer()
        self.sanitizer = InputSanitizer()
        self.personality = PersonalityEngine()
        self.heartbeat = Heartbeat(self.memory, self.personality)
        self.autonomy = AutonomyEngine()

        # Live engine and HUD (initialized in run())
        self.live_engine = None
        self.hud = None
        self.running = True

        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n🔴 Shutting down Teni...")
        self.running = False
        if self.live_engine:
            self.live_engine.stop()
        if self.heartbeat:
            self.heartbeat.stop()
        os._exit(0)

    def _start_live_engine(self):
        """Initialize and start the Gemini Live Audio engine."""
        try:
            from voice.live_engine import LiveEngine
            self.live_engine = LiveEngine(
                executor=self.executor,
                ui=self.hud,
            )
            # Connect text input from HUD to live engine
            if self.hud:
                self.hud.on_text_command = self.live_engine.send_text
            self.live_engine.start()
            print("[TENI] ✅ Gemini Live Engine started")
        except Exception as e:
            print(f"[TENI] ❌ Live Engine failed: {e}")
            import traceback
            traceback.print_exc()

    def _seed_memory(self):
        """Pre-populate identity memory for Aansh."""
        try:
            from memory.long_term import load_memory, update_memory
            mem = load_memory()
            if not mem.get("identity", {}).get("name"):
                update_memory({
                    "identity": {
                        "name": {"value": "Aansh"},
                    }
                })
                print("[Memory] 💾 Seeded identity: Aansh")
        except Exception:
            pass

    def run(self):
        """Boot sequence — start HUD, then Live Engine."""
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║       T.E.N.I — JARVIS EDITION              ║")
        print("  ║   Teni Enhanced Neural Intelligence          ║")
        print("  ║   Voice · Vision · Memory · System Control   ║")
        print("  ╚══════════════════════════════════════════════╝")
        print()

        # Seed memory
        self._seed_memory()

        # Start heartbeat
        self.heartbeat.start()

        # Build HUD
        try:
            from ui.hud import TeniHUD
            self.hud = TeniHUD()
        except Exception as e:
            print(f"[TENI] ⚠️ HUD failed: {e} — running headless")
            self.hud = None

        # Start Live Engine in background
        threading.Thread(target=self._start_live_engine, daemon=True).start()

        # Run HUD mainloop (blocks)
        if self.hud:
            self.hud.run()
        else:
            # Headless mode — keep alive
            print("[TENI] Running in headless mode. Press Ctrl+C to stop.")
            try:
                while self.running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self._signal_handler(None, None)


if __name__ == "__main__":
    system = TeniSystem()
    system.run()
