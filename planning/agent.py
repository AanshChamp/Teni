import json
import os
from typing import Dict, Any, List
from llm.client import LLMClient
from execution import ExecutionEngine
from utils.logger import TeniLogger
from security.permission_layer import PermissionLayer
from core.awareness import SystemAwareness

class Agent:
    def __init__(self, llm_client: LLMClient, execution_engine: ExecutionEngine, logger: TeniLogger, permission_layer: PermissionLayer, personality=None):
        self.llm_client = llm_client
        self.executor = execution_engine
        self.logger = logger
        self.permission_layer = permission_layer
        self.personality = personality
        self.awareness = SystemAwareness()
        self.state_file = os.path.expanduser("~/Teni/state.json")
        self.max_steps = 10

    def run(self, goal: str) -> None:
        """Run the iterative plan -> act -> observe -> adapt loop."""
        from llm.prompts import AGENT_SYSTEM_PROMPT
        
        print(f"🧠 Agent started for goal: '{goal}'")
        self.logger.log_router_mode("agent_loop")
        
        system_prompt = AGENT_SYSTEM_PROMPT
        if self.personality:
            state_prompt = self.personality.get_state_prompt()
            if state_prompt:
                system_prompt += f"\n\nCURRENT STATE: {state_prompt}"
        
        # Inject live system context
        ctx = self.awareness.get_context()
        ctx_str = f"\nCurrent context: Frontmost app={ctx.get('frontmost_app','?')}, Window={ctx.get('window_title','?')}, Running apps={ctx.get('running_apps',[])}\nClipboard: {ctx.get('clipboard','')[:200]}"
        
        self._set_overlay_state("thinking")
        
        history: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Goal: {goal}{ctx_str}\nBegin."}
        ]
        
        step = 1
        while step <= self.max_steps:
            print(f"\n--- Step {step} ---")
            
            # 1. PLAN / REASON
            result = self.llm_client._make_request(history, goal)
            if not result or "choices" not in result or len(result["choices"]) == 0:
                print("Teni Agent: LLM failed to respond.")
                break
            
            content = result["choices"][0]["message"]["content"].strip()
            # Try parsing the JSON
            parsed_response = self.llm_client._parse_json_response(content)
            
            if not parsed_response:
                print("Teni Agent: Failed to parse LLM response.")
                # Feed error back to LLM
                history.append({"role": "assistant", "content": content})
                history.append({"role": "user", "content": "Error: Invalid JSON response. Please provide valid JSON conforming to the schema."})
                step += 1
                continue
            
            history.append({"role": "assistant", "content": json.dumps(parsed_response)})
            
            thought = parsed_response.get("thought", "No thought provided.")
            is_complete = parsed_response.get("is_complete", False)
            next_action = parsed_response.get("next_action", {})
            
            print(f"💭 Thought: {thought}")
            
            # Check completion
            if is_complete or not next_action or not next_action.get("action"):
                print("✅ Teni Agent: Goal achieved or completed.")
                break
                
            # 2. ACT
            action_name = next_action.get("action")
            action_params = next_action.get("parameters", {})
            
            print(f"⚡ Action: {action_name} | Target: {next_action.get('target')} | Params: {action_params}")
            
            # Check permissions
            if self.permission_layer.requires_confirmation(action_name, action_params):
                confirm_message = self.permission_layer.get_confirmation_message(action_name, action_params)
                confirm = input(f"⚠️ {confirm_message}\nContinue? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Teni Agent: Action cancelled by user. Terminating loop.")
                    break
            
            # Execute
            execution_result = self.executor.execute(next_action)
            
            # 3. OBSERVE
            success = execution_result.get("success", False)
            message = execution_result.get("message") or execution_result.get("error") or "No message"
            
            if success:
                print(f"✓ Success: {message}")
                if self.personality:
                    self.personality.on_success()
            else:
                print(f"✗ Failed: {message}")
                if self.personality:
                    self.personality.on_failure()
                
            # 4. ADAPT (Feed result back into history)
            self._set_overlay_state("thinking")
            history.append({
                "role": "user", 
                "content": f"Action result: {json.dumps(execution_result)}\n\nWhat is the next step? (Set is_complete to true if finished)"
            })
            
            step += 1
            
        self._set_overlay_state("idle")
        if step > self.max_steps:
            print("❌ Teni Agent: Max steps reached. Terminating loop to prevent infinite loops.")

    def _set_overlay_state(self, activity: str):
        """Write activity state to state.json so the overlay can react."""
        try:
            data = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    data = json.load(f)
            data["activity"] = activity  # "thinking", "speaking", "acting", "idle"
            with open(self.state_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

