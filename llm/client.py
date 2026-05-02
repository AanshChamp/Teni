import json
import requests
"""
LLM Client - Dynamic model selection for optimal performance
"""

import requests
import json
from typing import Dict, Any, List, Optional
from config import Config
from .model_selector import ModelSelector

class LLMClient:
    def __init__(self):
        self.model_selector = ModelSelector()
        self.api_key = Config.NVIDIA_API_KEY
        self.base_endpoint = Config.LLM_ENDPOINT
        
        # Performance tracking
        self.request_stats = {
            "total_requests": 0,
            "fast_requests": 0,
            "balanced_requests": 0,
            "powerful_requests": 0,
            "ultra_requests": 0,
            "fallbacks": 0
        }
    
    def _make_request(self, messages: List[Dict[str, str]], user_input: str = "") -> Dict[str, Any]:
        """Make LLM request with dynamic model selection."""
        try:
            # Get user input for model selection (extract from messages if not provided)
            if not user_input and messages:
                user_input = messages[-1].get("content", "")
            
            # Make request with optimal model
            result = self.model_selector.make_request(messages, user_input)
            
            # Track usage
            self._track_request(user_input)
            
            return result
            
        except Exception as e:
            print(f"LLM request failed: {str(e)}")
            return None
    
    def _track_request(self, user_input: str):
        """Track model usage statistics."""
        self.request_stats["total_requests"] += 1
        
        # Determine which model tier was likely used
        task_type = self.model_selector._analyze_task_complexity(user_input)
        
        if task_type == "simple":
            self.request_stats["fast_requests"] += 1
        elif task_type == "medium":
            self.request_stats["balanced_requests"] += 1
        elif task_type == "complex":
            self.request_stats["powerful_requests"] += 1
        else:
            self.request_stats["ultra_requests"] += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get model usage statistics."""
        return {
            "usage": self.request_stats,
            "model_stats": self.model_selector.get_model_stats()
        }
    
    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            # Clean up the response
            content = content.strip()
            
            # Remove any markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Parse JSON
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Content: {content}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return self.model_selector.get_available_models()
    
    def test_model_performance(self, test_input: str) -> Dict[str, Any]:
        """Test performance with different models."""
        import time
        
        results = {}
        
        for tier_name, model_config in self.model_selector.models.items():
            if not self.model_selector.is_model_available(model_config["model"]):
                continue
            
            try:
                start_time = time.time()
                
                # Make test request
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": model_config["model"],
                    "messages": [{"role": "user", "content": test_input}],
                    "temperature": model_config["temperature"],
                    "max_tokens": model_config["max_tokens"]
                }
                
                response = requests.post(
                    self.model_selector.base_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                end_time = time.time()
                
                if response.status_code == 200:
                    results[tier_name] = {
                        "model": model_config["model"],
                        "response_time": end_time - start_time,
                        "success": True,
                        "tokens": response.json().get("usage", {}).get("total_tokens", 0)
                    }
                else:
                    results[tier_name] = {
                        "model": model_config["model"],
                        "response_time": end_time - start_time,
                        "success": False,
                        "error": response.status_code
                    }
                
            except Exception as e:
                results[tier_name] = {
                    "model": model_config["model"],
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def parse_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Parse user input into intent using dynamic model selection."""
        from .prompts import INTENT_SYSTEM_PROMPT
        
        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        result = self._make_request(messages, user_input)
        
        if not result:
            return None
        
        if result and "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"].strip()
            return self._parse_json_response(content)
        else:
            return None
    
    def get_conversational_response(self, user_input: str) -> str:
        """Get conversational response from LLM."""
        from .prompts import CONVERSATION_SYSTEM_PROMPT
        
        messages = [
            {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        result = self._make_request(messages, user_input)
        if not result:
            return "I'm having trouble understanding. Could you try again?"
        
        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return "I'm having trouble understanding. Could you try again?"
    
    def generate_email_draft(self, request: str) -> Optional[str]:
        messages = [
            {"role": "system", "content": EMAIL_DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": request}
        ]
        
        result = self._make_request(messages, request)
        if not result:
            return None
        
        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return None
        
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            print(f"Failed to parse email draft: {e}")
            return None
