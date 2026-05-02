from typing import Optional, Dict, Any
from llm.client import LLMClient

class IntentParser:
    def __init__(self):
        self.llm_client = LLMClient()
    
    def parse(self, user_input: str) -> Optional[Dict[str, Any]]:
        if not user_input or not user_input.strip():
            return None
        
        return self.llm_client.parse_intent(user_input.strip())
