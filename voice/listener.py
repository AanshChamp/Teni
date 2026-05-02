import threading
import numpy as np
import speech_recognition as sr
import os
import json
import time
from .biometrics import VoiceBiometrics


class VoiceListener:
    WAKE_WORD = "teni"
    SOUND_ALIKES = ["teni", "theni", "tiny", "tenny", "kenny", "denny", "tennis", "tony", "any"]
    STATE_FILE = os.path.expanduser("~/Teni/state.json")

    def __init__(self, callback=None):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.biometrics = VoiceBiometrics()
        self.callback = callback
        self._running = False
        self._thread = None
        self.enroll_mode = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("🎙️  Voice listener active — say 'Teni' followed by a command.")

    def stop(self):
        self._running = False

    def _update_volume(self, raw_data: np.ndarray):
        """Update state.json with current volume for animation reactivity."""
        try:
            # Calculate RMS volume
            rms = np.sqrt(np.mean(raw_data.astype(np.float32)**2))
            # Normalize to a 0.0 - 1.5 range for the overlay
            vol = min(1.5, rms / 1000.0)
            
            data = {}
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, "r") as f:
                    data = json.load(f)
            data["volume"] = vol
            with open(self.STATE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _listen_loop(self):
        mic = sr.Microphone()
        print("🎙️  Initializing Microphone...")
        
        # Set a fixed threshold so we don't hang on calibration
        self.recognizer.energy_threshold = 500 
        
        # Quick 0.1s check just to clear the buffer
        with mic as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
            except Exception:
                pass
        
        print(f"🎙️  Online. Listening for: {self.SOUND_ALIKES}")
        active_session_end = 0 


        while self._running:
            try:
                with mic as source:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=10)

                # 1. Volume & Biometrics
                raw_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                self._update_volume(raw_data)
                
                if self.enroll_mode:
                    self.biometrics.enroll(raw_data)
                    self.enroll_mode = False
                    continue

                # 2. Recognition
                try:
                    text = self.recognizer.recognize_google(audio).lower().strip()
                except sr.UnknownValueError:
                    continue

                if not text:
                    continue
                
                print(f"DEBUG: Heard: '{text}'")

                # 3. Identity check (Crucial since wake word is gone!)
                sim = self.biometrics.verify(raw_data)
                is_authorized = sim >= 0.5 or self.biometrics.enrolled_fingerprint is None or "enroll" in text

                if not is_authorized:
                    # Ignore background conversations not from Aansh
                    continue
                
                # 4. Direct Execution (No wake word needed)
                if text and self.callback:
                    print(f"🎙️  Direct Command Verified: \"{text}\"")
                    self.callback(text)

                    
            except sr.WaitTimeoutError:
                self._update_volume(np.zeros(100))
                # Clear session if silent for too long
                if time.time() > active_session_end:
                    active_session_end = 0
                continue
            except Exception:
                continue





