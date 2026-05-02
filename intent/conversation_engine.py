from llm.client import LLMClient
from llm.prompts import EMAIL_DRAFT_SYSTEM_PROMPT

class ConversationEngine:
    def __init__(self):
        self.llm_client = LLMClient()
    
    def get_conversational_response(self, user_input: str) -> str:
        conversational_prompt = """You are Teni, a calm and intelligent AI assistant for macOS.
You respond conversationally and helpfully to user questions and casual conversation.
Keep responses concise and friendly.
If the user asks about your capabilities, mention you can help with:
- Opening and controlling applications
- File system operations
- Web browsing and searches
- System automation
- Email drafts
Be helpful but not overly verbose."""
        
        messages = [
            {"role": "system", "content": conversational_prompt},
            {"role": "user", "content": user_input}
        ]
        
        result = self.llm_client._make_request(messages)
        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return "I'm here to help! I can assist with macOS automation, file operations, web browsing, and more. What would you like to do?"
