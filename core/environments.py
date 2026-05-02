import subprocess

class EnvironmentManager:
    """Manages workspace presets (Study Mode, Code Mode, etc.)"""
    
    PRESETS = {
        "study_mode": {
            "open": ["Notes", "Safari"],
            "close": ["Messages", "Music"],
            "dnd": True
        },
        "code_mode": {
            "open": ["Xcode", "Terminal", "Safari"],
            "close": ["Mail", "Messages"],
            "dnd": False
        }
    }

    def activate(self, preset_name):
        preset = self.PRESETS.get(preset_name.lower())
        if not preset: return False
        
        print(f"[Environment] 🛠 Activating {preset_name}...")
        
        # 1. Open apps
        for app in preset.get("open", []):
            subprocess.run(["open", "-a", app])
            
        # 2. Close distracting apps
        for app in preset.get("close", []):
            subprocess.run(["osascript", "-e", f'quit application "{app}"'])
            
        # 3. System settings (DND would need more complex AppleScript)
        return True
