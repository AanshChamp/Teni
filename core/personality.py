import json
import os

class PersonalityEngine:
    def __init__(self):
        self.state_file = os.path.expanduser("~/Teni/state.json")
        # 1 to 10 scale
        self.mood = 7       # 1=Angry/Sad, 10=Happy/Playful
        self.energy = 8     # 1=Tired/Slow, 10=Hyper/Fast
        self.confidence = 7 # 1=Cautious/Unsure, 10=Decisive/Autonomous
        self._save_state()

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    "mood": self.mood,
                    "energy": self.energy,
                    "confidence": self.confidence
                }, f)
        except Exception:
            pass

    def on_success(self):
        self.confidence = min(10, self.confidence + 1)
        self.mood = min(10, self.mood + 1)
        self.energy = max(1, self.energy - 1) # Work costs energy
        self._save_state()

    def on_failure(self):
        self.confidence = max(1, self.confidence - 2)
        self.mood = max(1, self.mood - 1)
        self.energy = max(1, self.energy - 1)
        self._save_state()

    def on_idle_tick(self):
        # Slowly regress to baseline (Neutral)
        if self.mood > 5: self.mood -= 0.1
        if self.mood < 5: self.mood += 0.1
        
        # Idle time restores energy
        self.energy = min(10, self.energy + 0.2)
        self._save_state()

    def get_state_prompt(self) -> str:
        prompt = []
        if self.mood >= 8:
            prompt.append("You are in a great, cheerful mood. Be concise but positive.")
        elif self.mood <= 3:
            prompt.append("You are currently frustrated. Be very direct and strictly professional.")
            
        if self.energy <= 3:
            prompt.append("You are feeling tired. Keep your thoughts and actions as minimal as possible.")
            
        if self.confidence >= 8:
            prompt.append("You are highly confident in your abilities. Execute decisively.")
        elif self.confidence <= 4:
            prompt.append("You are feeling uncertain. Proceed with extreme caution and ask for clarification if needed.")
            
        return " ".join(prompt)
    def trigger_proactive_greeting(self, context: dict):
        """Generate and speak a smart, context-aware greeting."""
        from llm.client import LLMClient
        from voice.speaker import VoiceSpeaker
        
        client = LLMClient()
        speaker = VoiceSpeaker()
        
        app = context.get("frontmost_app", "Finder")
        window = context.get("window_title", "")
        
        prompt = f"The user just unlocked their Mac. Frontmost app: {app}. Window: {window}. Your mood: {self.mood}. Energy: {self.energy}. Say a short, one-sentence greeting that acknowledges what they are doing. Be natural, like Jarvis."
        
        greeting = client.get_conversational_response(prompt)
        print(f"🤖 Proactive: {greeting}")
        speaker.speak(greeting)
