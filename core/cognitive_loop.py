import threading
import time
from typing import Dict, Any, Optional
from core.awareness import SystemAwareness
from memory.memory import Memory
from memory.patterns import PatternLearner
from cloud.sync import CloudSync
from memory.patterns import PatternLearner

class CognitiveLoop(threading.Thread):
    """
    The background 'consciousness' of Teni. 
    Monitors system state and decides when to act, suggest, or stay quiet.
    """
    def __init__(self, memory: Memory, personality=None, ui=None):
        super().__init__()
        self.memory = memory
        self.personality = personality
        self.ui = ui
        self.awareness = SystemAwareness()
        self.running = True
        self.daemon = True
        
        self.last_app = None
        self.last_window = None
        self.idle_start = time.time()
        self.significance_threshold = 0.6 # 0-1 scale
        self.patterns = PatternLearner()
        self._presence_timer = 0
        self.cloud_sync = CloudSync()
        self.total_uptime = 0
        self.was_locked = False
        self.patterns = PatternLearner()
        self._presence_timer = 0
        
    def run(self):
        print("[CognitiveLoop] 🧠 Loop active")
        while self.running:
            try:
                self._tick()
            except Exception as e:
                print(f"[CognitiveLoop] ❌ Error: {e}")
            time.sleep(5)

    def _tick(self):
        ctx = self.awareness.get_deep_context()
        current_app = ctx.get("frontmost_app")
        current_window = ctx.get("window_title")
        self.total_uptime += 5
        
        # 1. Statistical Recording
        self._presence_timer += 1
        if self._presence_timer >= 12: # ~1 minute (12 * 5s)
            self.patterns.record_presence(current_app)
            self._presence_timer = 0

        # 2. Unlock detection
        is_locked = (current_app == "loginwindow")
        if self.was_locked and not is_locked:
            if self.ui: self.ui.write_log("🔓 Welcome back, Aansh.")
        self.was_locked = is_locked

        # 3. Detect Transitions
        if current_app != self.last_app:
            self.patterns.record_transition(self.last_app, current_app)
            self._handle_app_switch(current_app, ctx)
            self.last_app = current_app
            self.idle_start = time.time()
            
        if current_window != self.last_window:
            self._handle_window_change(current_window, ctx)
            self.last_window = current_window
            self.idle_start = time.time()

        # 4. Background Maintenance (Cloud Sync & Summarization)
        if self.total_uptime % 300 == 0: # Every 5 mins
            try: self.cloud_sync.export_snapshot()
            except: pass
            
        if len(self.memory.memory_data.get("commands", [])) >= 25:
            self.memory.summarize_history()

        # 5. Monitor Idle Proactivity
        idle_duration = time.time() - self.idle_start
        if idle_duration > 600: # 10 minutes idle
            self._handle_long_idle(idle_duration, ctx)
            self.idle_start = time.time() # Reset so we don't spam

    def _handle_app_switch(self, app, ctx):
        """Analyze if the app switch is significant enough to comment on."""
        # Balanced proactivity: stay quiet for most things.
        # But if they open something like 'System Settings' or 'Terminal' after a failure, offer help.
        print(f"[CognitiveLoop] 👁️ User switched to {app}")
        
        if self.personality and self.personality.proactivity > 0.7:
             # Logic to suggest environment presets could go here
             pass

    def _handle_window_change(self, window, ctx):
        pass

    def _handle_long_idle(self, duration, ctx):
        """Triggered when user returns after a long break."""
        if self.ui:
            self.ui.write_log("SYS: Welcome back, sir.")
            # We could trigger a proactive greeting here via PersonalityEngine
