import json
import os
import time
from typing import Dict, Any, List
from llm.client import LLMClient
from execution import ExecutionEngine
from core.awareness import SystemAwareness

class Agent:
    """
    Enhanced Planning Agent with Feedback Loop.
    Workflow: Plan -> Execute -> Verify -> Adapt
    """
    def __init__(self, llm_client: LLMClient, execution_engine: ExecutionEngine, personality=None):
        self.llm = llm_client
        self.executor = execution_engine
        self.personality = personality
        self.awareness = SystemAwareness()
        self.max_retries = 2

    def run(self, goal: str):
        print(f"[Agent] 🎯 Goal: {goal}")
        
        # 1. PLAN
        plan = self._generate_plan(goal)
        if not plan: return
        
        for step in plan:
            success = self._execute_step_with_retry(step, goal)
            if not success:
                print(f"[Agent] ❌ Failed to complete plan at step: {step.get('description')}")
                break

    def _generate_plan(self, goal: str) -> List[Dict[str, Any]]:
        """Generate a multi-step plan using the LLM."""
        prompt = f"Break this goal into a sequence of actionable steps: {goal}. Return a JSON list of steps. Each step: {{'description': '...', 'action': '...', 'parameters': {{}}}}"
        # In a real implementation, we'd use a dedicated AGENT_PROMPT
        response = self.llm.get_conversational_response(prompt) # Simplified for now
        try:
            # Basic extraction - in production we use _parse_json_response
            return json.loads(response)
        except:
            return []

    def _execute_step_with_retry(self, step: Dict[str, Any], goal: str) -> bool:
        retries = 0
        while retries <= self.max_retries:
            # 2. EXECUTE
            print(f"[Agent] ⚡ Executing: {step['description']}")
            result = self.executor.execute(step)
            
            # 3. VERIFY
            # We check if the execution was successful and if the state changed as expected
            if result.get("success"):
                if self.personality: self.personality.on_success()
                return True
            
            # 4. ADAPT
            print(f"[Agent] ⚠️ Step failed: {result.get('error')}. Adapting...")
            if self.personality: self.personality.on_failure()
            
            # Re-plan or adjust parameters via LLM
            step = self._adapt_step(step, result.get("error"), goal)
            retries += 1
            
        return False

    def _adapt_step(self, step, error, goal):
        """Ask LLM to fix the step based on the error."""
        # This would be a call to Gemini to 'replan' this specific part
        return step # Placeholder
