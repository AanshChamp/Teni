import os
import re
from typing import Dict, Any, Optional
from config import Config

class IntentValidator:
    def __init__(self):
        self.allowed_actions = Config.ALLOWED_ACTIONS
        self.safe_shell_commands = Config.SAFE_SHELL_COMMANDS
    
    def validate(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(intent, dict):
            return {"error": "Invalid intent format"}
        
        # Handle multi-action format
        if "actions" in intent:
            actions = intent["actions"]
            if not isinstance(actions, list):
                return {"error": "Actions must be an array"}
            
            for i, action in enumerate(actions):
                if not isinstance(action, dict):
                    return {"error": f"Action {i+1} must be an object"}
                
                if "action" not in action:
                    return {"error": f"Action {i+1} missing action field"}
                
                action_name = action["action"]
                if action_name not in self.allowed_actions:
                    return {"error": f"Action {i+1}: '{action_name}' not allowed"}
                
                if "parameters" not in action or not isinstance(action["parameters"], dict):
                    return {"error": f"Action {i+1} missing or invalid parameters field"}
                
                params = action["parameters"]
                
                # Validate specific action parameters
                validation_result = self._validate_action_params(action_name, params)
                if validation_result:
                    return validation_result
            
            return None
        
        # Handle single-action format
        if "action" not in intent:
            return {"error": "Missing action field"}
        
        action = intent["action"]
        if action not in self.allowed_actions:
            return {"error": f"Action '{action}' not allowed"}
        
        if "parameters" not in intent or not isinstance(intent["parameters"], dict):
            return {"error": "Missing or invalid parameters field"}
        
        params = intent["parameters"]
        
        # Validate specific action parameters
        validation_result = self._validate_action_params(action, params)
        if validation_result:
            return validation_result
        
        return None
    
    def _validate_action_params(self, action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate parameters for specific actions."""
        if action in ["create_folder", "rename_file", "move_file", "list_files"]:
            if "path" in params and params["path"]:
                validation_result = self._validate_file_path(params["path"])
                if validation_result:
                    return validation_result
        
        if action == "run_shell_safe":
            if "content" in params and params["content"]:
                validation_result = self._validate_shell_command(params["content"])
                if validation_result:
                    return validation_result
        
        if action == "open_website":
            if "url" in params and params["url"]:
                validation_result = self._validate_url(params["url"])
                if validation_result:
                    return validation_result
        
        return None
    
    def _validate_file_path(self, path: str) -> Optional[Dict[str, Any]]:
        if not path or not isinstance(path, str):
            return {"error": "Invalid file path"}
        
        expanded_path = os.path.expanduser(path)
        normalized_path = os.path.normpath(expanded_path)
        
        if ".." in normalized_path.split("/"):
            return {"error": "Path traversal not allowed"}
        
        home_dir = os.path.expanduser("~")
        if not normalized_path.startswith(home_dir) and not normalized_path.startswith("/tmp/"):
            return {"error": "Access outside allowed directories not permitted"}
        
        return None
    
    def _validate_shell_command(self, command: str) -> Optional[Dict[str, Any]]:
        if not command or not isinstance(command, str):
            return {"error": "Invalid shell command"}
        
        dangerous_patterns = [
            r"&&", r"\|\|", r"\|", r";", r"`", r"\$",
            r"sudo", r"rm\s+-rf", r"chmod", r"chown",
            r">", r"<", r"\*\*"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return {"error": f"Dangerous command pattern detected: {pattern}"}
        
        parts = command.strip().split()
        if not parts or parts[0] not in self.safe_shell_commands:
            return {"error": f"Command '{parts[0] if parts else ''}' not in safe commands list"}
        
        return None
    
    def _validate_url(self, url: str) -> Optional[Dict[str, Any]]:
        if not url or not isinstance(url, str):
            return {"error": "Invalid URL"}
        
        url_pattern = re.compile(
            r'^https?://'  
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  
            r'localhost|'  
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  
            r'(?::\d+)?'  
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return {"error": "Invalid URL format"}
        
        return None
