import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import Config

class Memory:
    def __init__(self):
        self.memory_file = Config.MEMORY_FILE
        self.memory_data = self._load_memory()
        self._ensure_memory_structure()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file with error handling."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                return self._create_empty_memory()
        except Exception as e:
            print(f"Error loading memory: {e}")
            return self._create_empty_memory()
    
    def _create_empty_memory(self) -> Dict[str, Any]:
        """Create empty memory structure."""
        return {
            "tasks": [],
            "deadlines": [],
            "frequent_apps": {},
            "recent_files": [],
            "behavior_patterns": {},
            "preferences": {},
            "commands": [],
            "long_term_insights": [],
            "stats": {
                "total_commands": 0,
                "successful_commands": 0,
                "failed_commands": 0,
                "conversation_count": 0,
                "most_used_actions": {},
                "usage_by_hour": {},
                "usage_by_day": {}
            }
        }
    
    def _ensure_memory_structure(self):
        """Ensure memory has all required sections."""
        empty_memory = self._create_empty_memory()
        
        for key, value in empty_memory.items():
            if key not in self.memory_data:
                self.memory_data[key] = value
    
    def _save_memory(self):
        """Save memory to file with error handling."""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory_data, f, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def add_command(self, user_input: str, intent: Dict[str, Any], result: Dict[str, Any]):
        """Add command to memory with enhanced tracking."""
        command_data = {
            "timestamp": datetime.now().isoformat(),
            "input": user_input,
            "intent": intent,
            "result": result,
            "success": result.get("success", False)
        }
        
        self.memory_data["commands"].append(command_data)
        
        # Keep only last 100 commands
        if len(self.memory_data["commands"]) > 100:
            self.memory_data["commands"] = self.memory_data["commands"][-100:]
        
        # Update stats
        self.memory_data["stats"]["total_commands"] += 1
        
        if result.get("success"):
            self.memory_data["stats"]["successful_commands"] += 1
        else:
            self.memory_data["stats"]["failed_commands"] += 1
        
        # Update most used actions
        action_name = intent.get("action")
        if action_name:
            if action_name not in self.memory_data["stats"]["most_used_actions"]:
                self.memory_data["stats"]["most_used_actions"][action_name] = 0
            self.memory_data["stats"]["most_used_actions"][action_name] += 1
        
        # Update frequent apps
        if action_name == "open_app":
            app_name = intent.get("parameters", {}).get("app") or intent.get("target")
            if app_name:
                if app_name not in self.memory_data["frequent_apps"]:
                    self.memory_data["frequent_apps"][app_name] = 0
                self.memory_data["frequent_apps"][app_name] += 1
        
        # Update recent files
        if action_name in ["create_folder", "move_file", "rename_file"]:
            path = intent.get("parameters", {}).get("path")
            if path and path not in self.memory_data["recent_files"]:
                self.memory_data["recent_files"].append(path)
                if len(self.memory_data["recent_files"]) > 50:
                    self.memory_data["recent_files"] = self.memory_data["recent_files"][-50:]
        
        self._save_memory()
    
    def get_recent_commands(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent command interactions."""
        return self.memory_data["commands"][-count:] if self.memory_data["commands"] else []
    
    def get_frequent_apps(self) -> Dict[str, int]:
        """Get most frequently used applications."""
        return self.memory_data["frequent_apps"]
    
    def get_recent_files(self, count: int = 10) -> List[str]:
        """Get recent files."""
        return self.memory_data["recent_files"][-count:] if self.memory_data["recent_files"] else []
    
    def get_upcoming_deadlines(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming deadlines within specified days."""
        now = datetime.now()
        upcoming = []
        
        for deadline in self.memory_data["deadlines"]:
            try:
                due_date = datetime.fromisoformat(deadline["due_date"])
                if due_date <= now + timedelta(days=days):
                    upcoming.append(deadline)
            except (ValueError, KeyError):
                continue
        
        return upcoming
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences and settings."""
        return self.memory_data.get("preferences", {})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        stats = self.memory_data.get("stats", {})
        total = stats.get("total_commands", 0)
        successful = stats.get("successful_commands", 0)
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        return {
            "total_commands": total,
            "successful_commands": successful,
            "failed_commands": stats.get("failed_commands", 0),
            "success_rate": success_rate,
            "frequent_apps": self.memory_data.get("frequent_apps", {}),
            "most_used_actions": stats.get("most_used_actions", {})
        }
    
    def get_interaction_count(self) -> int:
        """Get total interaction count."""
        return self.memory_data["stats"]["total_commands"]
    
    def get_command_success_rate(self) -> float:
        """Get command success rate percentage."""
        total = self.memory_data["stats"]["total_commands"]
        successful = self.memory_data["stats"]["successful_commands"]
        
        if total == 0:
            return 0.0
        
        return (successful / total) * 100
    
    def get_most_used_actions(self) -> Dict[str, int]:
        """Get most used actions."""
        return self.memory_data["stats"].get("most_used_actions", {})
    
    def get_recent_errors(self, count: int = 5) -> List[str]:
        """Get recent error messages."""
        errors = []
        
        for command in reversed(self.memory_data["commands"][-20:]):
            if not command.get("success") and command.get("result", {}).get("error"):
                errors.append(command["result"]["error"])
        
        return errors[:count], {}
        
    def summarize_history(self):
        """Summarize old commands into long_term_insights using the LLM."""
        if len(self.memory_data["commands"]) < 20:
            return # Not enough data to summarize yet
            
        print("🧠 Teni Memory: Summarizing long-term insights in background...")
        
        # We need LLMClient, import it locally to avoid circular imports if any
        from llm.client import LLMClient
        from llm.prompts import MEMORY_SUMMARIZER_PROMPT
        
        llm_client = LLMClient()
        
        # Grab the oldest 50 commands (or whatever we have)
        history_to_summarize = self.memory_data["commands"][:50]
        
        # Prepare text representation
        history_text = "\n".join([f"Input: {cmd.get('input')} | Action: {cmd.get('intent', {}).get('action')} | Success: {cmd.get('success')}" for cmd in history_to_summarize])
        
        messages = [
            {"role": "system", "content": MEMORY_SUMMARIZER_PROMPT},
            {"role": "user", "content": f"Command History:\n{history_text}"}
        ]
        
        try:
            result = llm_client._make_request(messages, "summarize history")
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                parsed = llm_client._parse_json_response(content)
                if parsed and "insights" in parsed:
                    new_insights = parsed["insights"]
                    # Add new insights
                    for insight in new_insights:
                        if insight not in self.memory_data["long_term_insights"]:
                            self.memory_data["long_term_insights"].append(insight)
                    
                    # Truncate old commands that we just summarized to keep short term memory clean
                    self.memory_data["commands"] = self.memory_data["commands"][50:]
                    self._save_memory()
                    print(f"🧠 Teni Memory: Extracted {len(new_insights)} new insights.")
        except Exception as e:
            print(f"Error during memory summarization: {e}")
