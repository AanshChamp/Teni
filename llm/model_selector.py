"""
Model Selector - Dynamic LLM model selection for optimal performance
"""

import requests
import json
import urllib3
from typing import Dict, Any, List, Optional
from config import Config

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ModelSelector:
    def __init__(self):
        self.api_key = Config.NVIDIA_API_KEY
        self.base_endpoint = Config.LLM_ENDPOINT
        
        # Model configurations using NVIDIA NIM models based on user preference
        self.models = {
            "fast": {
                "model": "nvidia/nemotron-mini-4b-instruct",
                "temperature": 0.1,
                "max_tokens": 300,
                "description": "Ultra-fast SLM for simple commands and function calling",
                "use_cases": ["simple_commands", "app_control", "basic_file_ops"]
            },
            "balanced": {
                "model": "mistralai/mistral-nemotron",
                "temperature": 0.2,
                "max_tokens": 600,
                "description": "Built for agentic workflows, coding, function calling",
                "use_cases": ["multi_action", "web_search", "complex_commands"]
            },
            "powerful": {
                "model": "stepfun-ai/step-3.5-flash",
                "temperature": 0.2,
                "max_tokens": 2048,
                "description": "Most capable for complex reasoning and agentic tasks",
                "use_cases": ["context_aware", "complex_chaining", "ambiguous_commands"]
            },
            "ultra": {
                "model": "mistralai/mistral-large-3-675b-instruct-2512",
                "temperature": 0.2,
                "max_tokens": 4096,
                "description": "Maximum capability MoE VLM for difficult tasks",
                "use_cases": ["error_recovery", "complex_reasoning", "creative_tasks"]
            }
        }
        
        # Task complexity mapping
        self.task_complexity = {
            "simple": ["open_app", "close_app", "volume_control", "play_music", "activate_app", "type_text"],
            "medium": ["search_web", "create_folder", "list_files", "safari_control", "open_url", "open_website"],
            "complex": ["split_screen", "split_windows", "multi_action", "file_operations", "calendar_add", "compose_email", "add_calendar_event"],
            "very_complex": ["ambiguous_commands", "error_recovery", "context_aware", "run_applescript"]
        }
    
    def select_model(self, user_input: str, task_type: str = "auto") -> Dict[str, Any]:
        """Select optimal model based on task complexity and input characteristics."""
        
        if task_type == "auto":
            task_type = self._analyze_task_complexity(user_input)
        
        # Map task type to model tier
        if task_type == "simple":
            tier = "fast"
        elif task_type == "medium":
            tier = "balanced"
        elif task_type == "complex":
            tier = "powerful"
        else:
            tier = "ultra"
        
        # Check if input suggests higher complexity
        if self._requires_advanced_reasoning(user_input):
            tier = "powerful"
        
        # Check for multi-action commands
        if self._is_multi_action(user_input):
            tier = "balanced" if tier == "fast" else tier
        
        return self.models[tier]
    
    def _analyze_task_complexity(self, user_input: str) -> str:
        """Analyze user input to determine task complexity."""
        input_lower = user_input.lower()
        
        # Check for simple commands
        simple_keywords = ["open", "close", "play", "pause", "stop", "volume", "mute"]
        if any(keyword in input_lower for keyword in simple_keywords):
            return "simple"
        
        # Check for medium complexity
        medium_keywords = ["search", "create", "list", "find", "delete", "move", "rename"]
        if any(keyword in input_lower for keyword in medium_keywords):
            return "medium"
        
        # Check for complex commands
        complex_keywords = ["split screen", "multi", "chain", "sequence", "calendar", "reminder"]
        if any(keyword in input_lower for keyword in complex_keywords):
            return "complex"
        
        # Check for very complex (ambiguous, context-dependent)
        complex_indicators = ["it", "this", "that", "the", "again", "same", "previous"]
        if any(indicator in input_lower for indicator in complex_indicators):
            return "very_complex"
        
        # Check for multi-action indicators
        if " and " in input_lower or " then " in input_lower:
            return "complex"
        
        return "medium"  # Default to medium
    
    def _requires_advanced_reasoning(self, user_input: str) -> bool:
        """Check if input requires advanced reasoning capabilities."""
        input_lower = user_input.lower()
        
        advanced_indicators = [
            "figure out", "decide", "recommend", "suggest", "optimize",
            "why", "how", "explain", "analyze", "compare", "best way"
        ]
        
        return any(indicator in input_lower for indicator in advanced_indicators)
    
    def _is_multi_action(self, user_input: str) -> bool:
        """Check if input represents a multi-action command."""
        input_lower = user_input.lower()
        
        multi_action_indicators = [
            " and ", " then ", " after ", " before ",
            "first", "second", "next", "finally"
        ]
        
        return any(indicator in input_lower for indicator in multi_action_indicators)
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [m["model"] for m in self.models.values()]
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available."""
        available_models = self.get_available_models()
        return model_name in available_models
    
    def get_fallback_model(self, preferred_tier: str) -> Dict[str, Any]:
        """Get fallback model if preferred model is not available."""
        # Try preferred tier first
        if self.is_model_available(self.models[preferred_tier]["model"]):
            return self.models[preferred_tier]
        
        # Fallback hierarchy
        fallback_order = ["balanced", "fast", "powerful", "ultra"]
        
        for tier in fallback_order:
            if tier != preferred_tier and self.is_model_available(self.models[tier]["model"]):
                return self.models[tier]
        
        # Last resort - use any available model
        available_models = self.get_available_models()
        if available_models:
            return {
                "model": available_models[0],
                "temperature": 0.2,
                "max_tokens": 512,
                "description": "Fallback model"
            }
        
        # Ultimate fallback
        return self.models["balanced"]
    
    def make_request(self, messages: List[Dict[str, str]], user_input: str = "") -> Dict[str, Any]:
        """Make LLM request with optimal model selection."""
        # Select model based on task
        model_config = self.select_model(user_input)
        
        # Make request directly (skip availability check for now to test)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_config["model"],
            "messages": messages,
            "temperature": model_config["temperature"],
            "max_tokens": model_config["max_tokens"]
        }
        
        try:
            response = requests.post(
                self.base_endpoint,
                headers=headers,
                json=payload,
                timeout=15,
                verify=False
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Try fallback model on failure
                if model_config["model"] != self.models["balanced"]["model"]:
                    fallback_config = self.models["balanced"]
                    payload["model"] = fallback_config["model"]
                    payload["temperature"] = fallback_config["temperature"]
                    payload["max_tokens"] = fallback_config["max_tokens"]
                    
                    response = requests.post(
                        self.base_endpoint,
                        headers=headers,
                        json=payload,
                        timeout=15,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                
                return {"error": f"Model request failed: {response.status_code}"}
        
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about available models and usage."""
        available_models = self.get_available_models()
        
        return {
            "available_models": available_models,
            "total_models": len(available_models),
            "configured_models": list(self.models.keys()),
            "current_selection": "dynamic based on task complexity"
        }
