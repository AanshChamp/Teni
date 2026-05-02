import subprocess
import threading
import os
import json


class VoiceSpeaker:
    # macOS premium voices: Siri, Samantha, Daniel
    VOICE = "Siri"
    RATE = 185

    def speak(self, text: str):
        """Speak text aloud using macOS say (non-blocking)."""
        if not text:
            return
        thread = threading.Thread(
            target=self._say, args=(text,), daemon=True
        )
        thread.start()

    def _update_activity(self, activity: str):
        try:
            state_file = os.path.expanduser("~/Teni/state.json")
            data = {}
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    data = json.load(f)
            data["activity"] = activity
            with open(state_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _say(self, text: str):
        try:
            self._update_activity("speaking")
            # We use subprocess with a list to avoid shell injection
            subprocess.run(
                ["say", "-v", self.VOICE, "-r", str(self.RATE), text],
                timeout=30
            )
            self._update_activity("idle")
        except Exception:
            self._update_activity("idle")

