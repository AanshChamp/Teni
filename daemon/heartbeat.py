import threading
import time
import subprocess
from memory.memory import Memory
from core.autonomy import AutonomyEngine
from cloud.sync import CloudSync
from core.awareness import SystemAwareness


class Heartbeat(threading.Thread):
    def __init__(self, memory: Memory, personality=None):
        super().__init__()
        self.memory = memory
        self.personality = personality
        self.autonomy = AutonomyEngine()
        self.cloud_sync = CloudSync()
        self.awareness = SystemAwareness()
        self.running = True
        self.daemon = True
        self.idle_time = 0
        self.total_uptime = 0
        self.tick_interval = 5
        self.was_locked = False
        self.last_awake_check = time.time()

    def reset_idle(self):
        """Reset idle timer. Called by main loop when user interacts."""
        self.idle_time = 0

    def run(self):
        while self.running:
            time.sleep(self.tick_interval)

            if not self.running:
                break

            self.idle_time += self.tick_interval
            self.total_uptime += self.tick_interval

            # 0. Check for Unlock / Wake events
            is_locked = self._check_screen_locked()
            if self.was_locked and not is_locked:
                print("🔓 Mac Unlocked — Teni is waking up.")
                if self.personality:
                    # Context-aware greeting
                    ctx = self.awareness.get_context()
                    self.personality.trigger_proactive_greeting(ctx)
            
            self.was_locked = is_locked

            if self.personality:
                self.personality.on_idle_tick()

            # 1. Background deadline checks
            deadlines = self.memory.get_upcoming_deadlines(days=1)

            # 2. Idle tasks (30 seconds of inactivity)
            if self.idle_time >= 30:
                self.idle_time = 0

                # Summarize memory if commands have built up
                if len(self.memory.memory_data.get("commands", [])) >= 20:
                    self.memory.summarize_history()

                # Autonomy: analyse patterns and suggest tasks
                self.autonomy.analyse_and_suggest(self.memory.memory_data)

            # 3. Cloud snapshot every 5 minutes of uptime
            if self.total_uptime > 0 and self.total_uptime % 300 == 0:
                try:
                    self.cloud_sync.export_snapshot()
                except Exception:
                    pass

    def _check_screen_locked(self) -> bool:
        """Check if the screen is currently locked/asleep."""
        try:
            # Check for the screensaver/loginwindow process being 'frontmost' or active
            # On macOS, this string is present in 'ioreg' when locked
            cmd = "ioreg -n IODisplayWrangler | grep -i IOPowerManagement"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            # This is a heuristic. A better one is checking for 'CGSession' status or loginwindow.
            # For simplicity, we check if the user is in the 'loginwindow' app context.
            front = self.awareness.get_frontmost_app()
            return front == "loginwindow"
        except Exception:
            return False


    def stop(self):
        self.running = False

