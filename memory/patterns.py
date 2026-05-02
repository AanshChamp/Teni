import json
import os
from datetime import datetime

class PatternLearner:
    """Silently tracks user behavior to learn habits and statistical trends."""
    def __init__(self):
        self.file = os.path.expanduser("~/Teni/memory/patterns.json")
        self.data = self._load()
        
    def _load(self):
        try:
            if os.path.exists(self.file):
                with open(self.file, 'r') as f: return json.load(f)
        except: pass
        return {
            "app_usage": {}, # app_name: {total_minutes, peak_hours}
            "workflow_sequences": [], 
            "focus_stats": {},
            "daily_patterns": {
                "work_start_avg": "15:00",
                "break_avg": "17:00"
            }
        }

    def record_presence(self, app):
        """Called every minute to track time spent in apps."""
        if app not in self.data["app_usage"]:
            self.data["app_usage"][app] = {"total_minutes": 0, "hits": 0}
        
        self.data["app_usage"][app]["total_minutes"] += 1
        self._save()

    def record_transition(self, from_app, to_app):
        """Silently record app switches to learn common workflows."""
        if not from_app or not to_app: return
        
        timestamp = datetime.now().isoformat()
        # Find existing sequence or add new
        seq_found = False
        for seq in self.data["workflow_sequences"]:
            if seq["from"] == from_app and seq["to"] == to_app:
                seq["count"] = seq.get("count", 0) + 1
                seq_found = True
                break
        
        if not seq_found:
            self.data["workflow_sequences"].append({
                "from": from_app, 
                "to": to_app, 
                "count": 1,
                "last_seen": timestamp
            })
            
        self._save()

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, 'w') as f: json.dump(self.data, f, indent=2)
        except: pass
