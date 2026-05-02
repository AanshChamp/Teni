from typing import Dict, Any, Optional

class IntentNormalizer:
    ACTION_ALIASES = {
        "list": "list_files",
        "show_files": "list_files", 
        "files_list": "list_files",
        "display_files": "list_files",
        "show": "list_files",
        "search": "search_web",
        "web_search": "search_web",
        "google_search": "search_web",
        "find": "search_web"
    }
    
    SAFARI_ACTION_ALIASES = {
        "open_last_tab": "reopen_last_tab",
        "last_tab": "reopen_last_tab", 
        "reopen_tab": "reopen_last_tab",
        "reopen_last_tab": "reopen_last_tab",
        "open_tab": "reopen_last_tab",
        "restore_tab": "reopen_last_tab"
    }
    
    @staticmethod
    def normalize(intent: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(intent, dict):
            return {"error": "Invalid intent format"}
        
        # Ensure required fields exist
        if "parameters" not in intent:
            intent["parameters"] = {}
        
        if "requires_confirmation" not in intent:
            intent["requires_confirmation"] = False
        
        # Normalize action
        action = intent.get("action")
        if not action:
            return {"error": "Missing action field"}
        
        # Map action aliases
        if action in IntentNormalizer.ACTION_ALIASES:
            original_action = action
            intent["action"] = IntentNormalizer.ACTION_ALIASES[action]
        
        # Normalize Safari sub-actions
        if intent["action"] == "safari_control":
            target = intent.get("target")
            if target and target in IntentNormalizer.SAFARI_ACTION_ALIASES:
                intent["target"] = IntentNormalizer.SAFARI_ACTION_ALIASES[target]
        
        return intent
