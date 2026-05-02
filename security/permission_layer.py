"""
Permission Layer - Critical security override for risky operations
"""

from typing import Dict, Any, List
from utils.logger import TeniLogger
from memory.memory import Memory

class PermissionLayer:
    def __init__(self):
        self.logger = TeniLogger()
        self.memory = Memory()
        
        # Always require confirmation for these actions
        self.ALWAYS_CONFIRM_ACTIONS = {
            "delete_file",
            "force_quit", 
            "move_file",
            "calendar_add",
            "reminder_add",
            "run_shell_safe",
            "screenshot",  # Can capture sensitive info
            "run_applescript"
        }
        
        # High-risk actions requiring extra confirmation
        self.HIGH_RISK_ACTIONS = {
            "delete_file": "This will permanently delete files",
            "force_quit": "This will force quit applications without saving",
            "run_shell_safe": "This will execute shell commands",
            "calendar_add": "This will create calendar events",
            "reminder_add": "This will create reminders",
            "run_applescript": "This will execute a native AppleScript capable of deep system control"
        }
    
    def requires_confirmation(self, action: str, params: Dict[str, Any]) -> bool:
        """Override LLM confirmation - always require for risky actions."""
        # Always require confirmation for dangerous actions
        if action in self.ALWAYS_CONFIRM_ACTIONS:
            return True
        
        # Additional checks for specific parameters
        if action == "move_file":
            target = params.get("target", "")
            # Moving files outside home directory is risky
            if not target.startswith("~/"):
                return True
        
        if action == "screenshot":
            # Screenshots can capture sensitive information
            return True
        
        if action == "find_file":
            # Searching system directories is risky
            search_path = params.get("path", "")
            if search_path.startswith("/") and not search_path.startswith("/Users/"):
                return True
        
        return False
    
    def get_confirmation_message(self, action: str, params: Dict[str, Any]) -> str:
        """Get detailed confirmation message for risky action."""
        base_message = self.HIGH_RISK_ACTIONS.get(action, f"Execute {action}")
        
        # Add specific details
        if action == "delete_file":
            path = params.get("path", "")
            return f"⚠️  {base_message}: {path}\nThis cannot be undone!"
        
        if action == "force_quit":
            app = params.get("app", "")
            return f"⚠️  {base_message}: {app}\nAny unsaved work will be lost!"
        
        if action == "move_file":
            source = params.get("path", "")
            target = params.get("target", "")
            return f"⚠️  {base_message}\nFrom: {source}\nTo: {target}"
        
        if action == "run_shell_safe":
            command = params.get("command", "")
            return f"⚠️  {base_message}: {command}"
            
        if action == "run_applescript":
            script = params.get("script", "")[:100]
            return f"⚠️  {base_message}:\n{script}..."
        
        if action == "calendar_add":
            title = params.get("title", "")
            date = params.get("date", "")
            time = params.get("time", "")
            return f"⚠️  {base_message}: {title} on {date} {time or ''}"
        
        if action == "reminder_add":
            title = params.get("title", "")
            due_date = params.get("due_date", "")
            return f"⚠️  {base_message}: {title}" + (f" (Due: {due_date})" if due_date else "")
        
        if action == "screenshot":
            screenshot_type = params.get("type", "screen")
            return f"⚠️  {base_message}: {screenshot_type} screenshot\nThis will capture your screen!"
        
        return f"⚠️  {base_message}"
    
    def request_confirmation(self, action: str, params: Dict[str, Any]) -> bool:
        """Request user confirmation with context memory."""
        confirmation_message = self.get_confirmation_message(action, params)
        
        # Store confirmation request in memory
        self._store_confirmation_request(action, params, confirmation_message)
        
        # Get user input
        try:
            user_response = input(f"Teni: {confirmation_message}\nContinue? (y/n): ").strip().lower()
            
            # Store response in memory
            self._store_confirmation_response(action, user_response)
            
            return user_response == 'y'
            
        except (EOFError, KeyboardInterrupt):
            self._store_confirmation_response(action, "interrupted")
            return False
    
    def _store_confirmation_request(self, action: str, params: Dict[str, Any], message: str):
        """Store confirmation request in memory for context."""
        confirmation_data = {
            "timestamp": self.logger.logger.handlers[0].formatter.formatTime(
                self.logger.logger.makeRecord(
                    name="teni", level=20, pathname="", lineno=0,
                    msg="", args=(), exc_info=None
                )
            ),
            "action": action,
            "params": params,
            "message": message,
            "status": "pending"
        }
        
        if "pending_confirmations" not in self.memory.memory_data:
            self.memory.memory_data["pending_confirmations"] = []
        
        self.memory.memory_data["pending_confirmations"].append(confirmation_data)
        self.memory._save_memory()
    
    def _store_confirmation_response(self, action: str, response: str):
        """Store confirmation response in memory."""
        if "pending_confirmations" in self.memory.memory_data:
            for confirmation in self.memory.memory_data["pending_confirmations"]:
                if confirmation["action"] == action and confirmation["status"] == "pending":
                    confirmation["status"] = "responded"
                    confirmation["response"] = response
                    confirmation["response_timestamp"] = self.logger.logger.handlers[0].formatter.formatTime(
                        self.logger.logger.makeRecord(
                            name="teni", level=20, pathname="", lineno=0,
                            msg="", args=(), exc_info=None
                        )
                    )
                    break
            
            self.memory._save_memory()
    
    def get_pending_confirmations(self) -> List[Dict[str, Any]]:
        """Get pending confirmation requests."""
        return [
            conf for conf in self.memory.memory_data.get("pending_confirmations", [])
            if conf.get("status") == "pending"
        ]
    
    def get_confirmation_history(self, action: str = None) -> List[Dict[str, Any]]:
        """Get confirmation history for context."""
        confirmations = self.memory.memory_data.get("pending_confirmations", [])
        
        if action:
            return [conf for conf in confirmations if conf["action"] == action]
        
        return confirmations
