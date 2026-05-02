import json
import os

class PersonalityEngine:
    """Adaptive, state-driven personality for Teni."""
    def __init__(self):
        self.state_file = os.path.expanduser("~/Teni/state.json")
        self.mood = 0.7       # 0.0 to 1.0
        self.confidence = 0.7 # 0.0 to 1.0
        self.proactivity = 0.5 # 0.0 to 1.0 (Balanced)
        self.mode = "watchful" # watchful, active, dormant
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.mood = data.get("mood", 0.7)
                    self.confidence = data.get("confidence", 0.7)
        except: pass

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({"mood": self.mood, "confidence": self.confidence}, f)
        except: pass

    def on_success(self):
        self.confidence = min(1.0, self.confidence + 0.05)
        self.mood = min(1.0, self.mood + 0.02)
        self._save_state()

    def on_failure(self):
        self.confidence = max(0.2, self.confidence - 0.15)
        self.mood = max(0.1, self.mood - 0.05)
        self._save_state()

    def get_behavior_prompt(self) -> str:
        """Injects behavioral modifiers into the LLM system prompt."""
        modifiers = []
        if self.confidence > 0.8:
            modifiers.append("You are feeling highly confident. Be decisive and proactive.")
        elif self.confidence < 0.4:
            modifiers.append("You are feeling cautious due to recent issues. Verify steps and be more conservative.")
        
        if self.mood < 0.3:
            modifiers.append("Your tone should be strictly professional and minimal.")
        else:
            modifiers.append("Your tone is helpful and slightly informal, like a trusted collaborator.")
            
        return " ".join(modifiers)
