#!/usr/bin/env python3
import sys
import signal
import subprocess
from typing import Dict, Any
from intent.parser import IntentParser
from intent.validator import IntentValidator
from intent.intent_normalizer import IntentNormalizer
from intent.conversation_engine import ConversationEngine
from execution import ExecutionEngine
from memory.memory import Memory
from utils.logger import TeniLogger
from security.permission_layer import PermissionLayer
from security.input_sanitizer import InputSanitizer
from planning.agent import Agent
from daemon.heartbeat import Heartbeat
from core.personality import PersonalityEngine
from voice.listener import VoiceListener
from voice.speaker import VoiceSpeaker
from voice.gestures import GestureController
from core.autonomy import AutonomyEngine
from cloud.sync import CloudSync

class TeniCLI:
    def __init__(self):
        self.parser = IntentParser()
        self.validator = IntentValidator()
        self.normalizer = IntentNormalizer()
        self.executor = ExecutionEngine()
        self.conversation_engine = ConversationEngine()
        self.memory = Memory()
        self.logger = TeniLogger()
        self.permission_layer = PermissionLayer()
        self.sanitizer = InputSanitizer()
        self.personality = PersonalityEngine()
        self.agent = Agent(self.parser.llm_client, self.executor, self.logger, self.permission_layer, self.personality)
        self.heartbeat = Heartbeat(self.memory, self.personality)
        self.speaker = VoiceSpeaker()
        self.voice_listener = VoiceListener(callback=self._voice_command)
        self.autonomy = AutonomyEngine()
        self.cloud_sync = CloudSync()
        self.gesture_controller = GestureController(callback=self._gesture_command)
        self.voice_active = True
        self.gesture_active = False
        self.running = True
        
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\nTeni: Goodbye!")
        self.running = False
        if hasattr(self, 'heartbeat'):
            self.heartbeat.stop()
        if hasattr(self, 'ui_process'):
            self.ui_process.terminate()
    
    def _print_response(self, result: dict):
        if result.get("success"):
            message = result.get("message", "Command completed successfully")
            if "draft" in result:
                print(f"Teni: {message}\n{result['draft']}")
            elif "files" in result:
                print(f"Teni: {message}\nFiles: {', '.join(result['files'])}")
            else:
                print(f"Teni: {message}")
        else:
            error = result.get("error", "Unknown error occurred")
            print(f"Teni: Error - {error}")
    
    def _resolve_template_variables(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve template variables like {{current_user}} in intent."""
        import os
        
        def resolve_value(value):
            if isinstance(value, str):
                # Replace common template variables
                value = value.replace("{{current_user}}", os.path.expanduser("~").split("/")[-1])
                value = value.replace("{{home}}", os.path.expanduser("~"))
                value = value.replace("{{desktop}}", os.path.expanduser("~/Desktop"))
                value = value.replace("{{documents}}", os.path.expanduser("~/Documents"))
                value = value.replace("{{downloads}}", os.path.expanduser("~/Downloads"))
                return value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(intent)
    
    def _set_activity(self, activity: str):
        """Update state.json with current activity."""
        try:
            state_file = os.path.expanduser("~/Teni/state.json")
            data = {}
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    data = json.load(f)
            data["activity"] = activity
            with open(state_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _process_command(self, user_input: str):
        # 1. Update UI to Thinking
        self._set_activity("thinking")
        
        # Sanitize user input
        safe_input = self.sanitizer.sanitize_search_query(user_input)
        
        # Parse intent
        intent = self.parser.parse(safe_input)
        
        # Resolve template variables in intent
        if intent:
            intent = self._resolve_template_variables(intent)
        
        if not intent or "error" in intent or not intent.get("action"):
            self.logger.log_router_mode("conversation")
            response = self.conversation_engine.get_conversational_response(safe_input)
            print(f"Teni: {response}")
            self._set_activity("speaking")
            self.speaker.speak(response)
            self._set_activity("idle")
            return

        
        # Check for multi-action format
        if "actions" in intent:
            # Multi-action command
            self.logger.log_router_mode("command")
            
            # Validate multi-action intent
            validation_error = self.validator.validate(intent)
            if validation_error:
                self.logger.log_router_mode("conversation")
                response = self.conversation_engine.get_conversational_response(safe_input)
                print(f"Teni: {response}")
                return
            
            # Check for confirmations - override LLM with security layer
            requires_confirm = any(
                self.permission_layer.requires_confirmation(action.get("action"), action.get("parameters", {}))
                for action in intent.get("actions", [])
            )
            
            if requires_confirm:
                # Get confirmation message from security layer
                first_risky = next((action for action in intent.get("actions", []) 
                    if self.permission_layer.requires_confirmation(action.get("action"), action.get("parameters", {}))), None)
                
                if first_risky:
                    confirm_message = self.permission_layer.get_confirmation_message(
                        first_risky.get("action"), first_risky.get("parameters")
                    )
                else:
                    confirm_message = "Execute this multi-action command?"
                
                confirm = input(f"Teni: {confirm_message}\nContinue? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Teni: Command cancelled")
                    return
            
            # Execute multi-action
            result = self.executor.execute(intent)
            
            if result.get("success"):
                completed = len(result.get("results", []))
                print(f"Teni: Successfully executed {completed} actions")
            else:
                failed_actions = [r for r in result.get("results", []) if not r.get("success")]
                print(f"Teni: Partial execution - {len(failed_actions)} actions failed")
            
            self.memory.add_command(safe_input, intent, result)
            self.logger.log_command(safe_input, intent, result)
            return
        
        if "action" not in intent or not intent["action"]:
            self.logger.log_router_mode("conversation")
            response = self.conversation_engine.get_conversational_response(safe_input)
            print(f"Teni: {response}")
            self.speaker.speak(response)
            return
        
        # Normalize intent
        normalized_intent = self.normalizer.normalize(intent)
        if "error" in normalized_intent:
            self.logger.log_router_mode("conversation")
            response = self.conversation_engine.get_conversational_response(safe_input)
            print(f"Teni: {response}")
            self.speaker.speak(response)
            return
        
        # Log normalization if action changed
        if intent.get("action") != normalized_intent.get("action"):
            self.logger.log_normalization(intent.get("action"), normalized_intent.get("action"))
        
        # Validate normalized intent
        validation_error = self.validator.validate(normalized_intent)
        if validation_error:
            self.logger.log_router_mode("conversation")
            response = self.conversation_engine.get_conversational_response(safe_input)
            print(f"Teni: {response}")
            self.speaker.speak(response)
            return
        
        # Override LLM confirmation with security layer
        action_name = normalized_intent.get("action")
        action_params = normalized_intent.get("parameters", {})
        
        if self.permission_layer.requires_confirmation(action_name, action_params):
            # Get security confirmation message
            confirm_message = self.permission_layer.get_confirmation_message(action_name, action_params)
            confirm = input(f"Teni: {confirm_message}\nContinue? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Teni: Command cancelled")
                return
        
        # Execute command
        self.logger.log_router_mode("command")
        self._set_activity("acting")
        
        result = self.executor.execute(normalized_intent)
        
        self.memory.add_command(safe_input, normalized_intent, result)
        self.logger.log_command(safe_input, normalized_intent, result)
        
        self._print_response(result)
        self._set_activity("speaking")
        if result.get("success"):
            self.speaker.speak(result.get("message", "Done"))
        else:
            self.speaker.speak(f"Error: {result.get('error')}")
        self._set_activity("idle")

    
    def _show_stats(self):
        """Show system statistics."""
        stats = self.memory.get_stats()
        
        print("\n📊 Teni Statistics:")
        print(f"Total commands: {stats.get('total_commands', 0)}")
        print(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        
        frequent_apps = stats.get('frequent_apps', {})
        if frequent_apps:
            print("\nFrequently used apps:")
            for app, count in list(frequent_apps.items())[:5]:
                print(f"  • {app}: {count} times")
        
        # Show LLM model usage stats
        llm_stats = self.parser.llm_client.get_usage_stats()
        usage = llm_stats.get("usage", {})
        model_stats = llm_stats.get("model_stats", {})
        
        print(f"\n🤖 LLM Model Usage:")
        print(f"  Total requests: {usage.get('total_requests', 0)}")
        print(f"  Fast model: {usage.get('fast_requests', 0)}")
        print(f"  Balanced model: {usage.get('balanced_requests', 0)}")
        print(f"  Powerful model: {usage.get('powerful_requests', 0)}")
        print(f"  Ultra model: {usage.get('ultra_requests', 0)}")
        
        available_models = model_stats.get("available_models", [])
        if available_models:
            print(f"\nAvailable models: {len(available_models)}")
            print(f"  Top models: {', '.join(available_models[:3])}")
        
        # Show pending confirmations
        pending = self.permission_layer.get_pending_confirmations()
        if pending:
            print("\n⚠️  Pending confirmations:")
            for conf in pending[:3]:
                print(f"  • {conf['action']}: {conf['message']}")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
🚀 Teni AI System - Enhanced with Dynamic Model Selection

Commands:
• Apps: "open safari", "split screen safari and notes", "close safari"
• Files: "create folder named Projects on Desktop", "list files in Downloads"
• Web: "search web for IB chemistry acids", "open website google.com"
• Safari: "reopen last tab", "go back", "go forward"
• System: "volume up", "take screenshot", "system info", "find file"
• Media: "play music", "pause music", "next track"
• Calendar: "add calendar event 'Meeting' tomorrow 2pm"
• Reminders: "add reminder 'Submit assignment' due Friday"

Advanced Features:
• Multi-action chaining: "open safari and search IB chemistry and split screen with notes"
• Context awareness: Understands "it", "this", "that app"
• Security override: Always confirms risky operations, ignores LLM "requires_confirmation": false
• Dynamic model selection: Uses optimal LLM model for each task

Performance Optimization:
• Fast model (nemotron-mini) for simple commands
• Balanced model (mistral-nemotron) for complex tasks
• Powerful model (step-3.5-flash) for reasoning
• Ultra model (mistral-large-3) for difficult tasks
• Automatic fallback to available models

Special commands:
• "stats" - Show usage statistics and model performance
• "help" - Show this help
• "exit" - Exit Teni

Security Features:
• Input sanitization prevents injection attacks
• Permission layer overrides LLM confirmation settings
• Risky operations always require user approval
• Safe argument handling for all commands

Performance:
• Simple commands: ~1-2 seconds (fast model)
• Complex commands: ~2-3 seconds (balanced model)
• Reasoning tasks: ~3-5 seconds (powerful model)
• Automatic optimization based on task complexity

Just talk naturally! Teni understands context and uses optimal AI models for each task.
        """
        print(help_text)
    
    def _voice_command(self, text: str):
        """Callback from voice listener — process spoken commands."""
        print(f"\n🎙️  Voice command: {text}")
        self.heartbeat.reset_idle()
        
        # Handle "enroll" command vocally
        if "enroll" in text.lower():
            self.speaker.speak("I am ready to learn your voice. Please speak clearly for five seconds starting now.")
            print("👤 Voice Enrollment Active...")
            self.voice_listener.enroll_mode = True
            return

        if text.startswith("agent"):
            goal = text.replace("agent", "", 1).strip()
            if goal:
                self.agent.run(goal)
        else:
            self._process_command(text)


    def _gesture_command(self, gesture: str):
        """Callback from gesture controller."""
        print(f"\n✋ Gesture detected: {gesture}")
        self.heartbeat.reset_idle()
        if gesture == "approve":
            # Auto-approve the top pending autonomous task
            pending = self.autonomy.get_pending()
            if pending:
                task = self.autonomy.approve_task(pending[0]["id"])
                if task:
                    print(f"✅ Gesture-approved task: {task['description']}")
                    self.agent.run(task.get("action", {}).get("parameters", {}).get("goal", task["description"]))
                    self.autonomy.complete_task(pending[0]["id"])
        elif gesture == "stop":
            print("✋ Stop gesture — pausing.")
        elif gesture == "confirm":
            print("✊ Confirm gesture received.")

    def run(self):
        print("🚀 Teni AI System — Jarvis Edition")
        print("Voice • Agent • Personality • System Control • Autonomy")
        print("Type 'help' for commands or 'exit' to quit")
        print()

        # Start voice listener by default
        self.voice_listener.start()
        self.speaker.speak("Teni system online. I'm listening, Aansh.")
        
        self.heartbeat.start()
        
        # Start UI overlay
        self.ui_process = subprocess.Popen(["python3", "ui/overlay.py"])
        
        while self.running:
            try:
                self.heartbeat.reset_idle()
                user_input = input("Teni > ").strip()
                
                if user_input.lower() == "exit":
                    print("Teni: Goodbye!")
                    self.speaker.speak("Goodbye.")
                    self.heartbeat.stop()
                    self.voice_listener.stop()
                    if hasattr(self, 'ui_process'): self.ui_process.terminate()
                    break
                
                if user_input.lower() == "help":
                    self._show_help()
                    continue
                
                if user_input.lower() == "stats":
                    self._show_stats()
                    continue
                
                if user_input.lower() == "voice":
                    if not self.voice_active:
                        self.voice_listener.start()
                        self.voice_active = True
                        self.speaker.speak("Voice mode activated. Say Teni followed by your command.")
                    else:
                        self.voice_listener.stop()
                        self.voice_active = False
                        print("🔇 Voice listener stopped.")
                    continue
                    
                if user_input.lower() == "gestures":
                    if not self.gesture_active:
                        self.gesture_controller.start()
                        self.gesture_active = True
                    else:
                        self.gesture_controller.stop()
                        self.gesture_active = False
                        print("✋ Gesture control stopped.")
                    continue
                
                if user_input.lower() == "enroll":
                    print("👤 Voice Enrollment: Please say 'Teni' followed by 'This is Aansh' in 3... 2... 1...")
                    self.voice_listener.enroll_mode = True
                    if not self.voice_active:
                        self.voice_listener.start()
                        self.voice_active = True
                    continue
                    
                if user_input.lower() == "tasks":
                    pending = self.autonomy.get_pending()
                    if pending:
                        print("\n🤖 Autonomous Suggestions:")
                        for t in pending[:5]:
                            print(f"  [{t['id']}] (P{t['priority']}) {t['description']}")
                        print("  → Type 'approve <id>' or 'reject <id>'")
                    else:
                        print("\n🤖 No pending autonomous suggestions.")
                    continue
                    
                if user_input.lower().startswith("approve "):
                    try:
                        task_id = int(user_input.split()[1])
                        task = self.autonomy.approve_task(task_id)
                        if task:
                            print(f"✅ Approved task {task_id}. Executing...")
                            self.agent.run(task.get('action', {}).get('parameters', {}).get('goal', task['description']))
                            self.autonomy.complete_task(task_id)
                        else:
                            print("Task not found.")
                    except (ValueError, IndexError):
                        print("Usage: approve <task_id>")
                    continue
                    
                if user_input.lower().startswith("reject "):
                    try:
                        task_id = int(user_input.split()[1])
                        self.autonomy.reject_task(task_id)
                        print(f"❌ Rejected task {task_id}.")
                    except (ValueError, IndexError):
                        print("Usage: reject <task_id>")
                    continue
                    
                if user_input.lower() == "sync":
                    self.cloud_sync.export_snapshot()
                    continue
                
                if not user_input:
                    continue
                
                if user_input.lower().startswith("agent:"):
                    goal = user_input[6:].strip()
                    if goal:
                        self.agent.run(goal)
                    else:
                        print("Teni: Please specify a goal after 'agent:' (e.g., 'agent: create a folder and put a file in it')")
                    continue
                
                self._process_command(user_input)
                
            except KeyboardInterrupt:
                print("\nTeni: Goodbye!")
                self.heartbeat.stop()
                if hasattr(self, 'ui_process'): self.ui_process.terminate()
                break
            except EOFError:
                print("\nTeni: Goodbye!")
                self.heartbeat.stop()
                if hasattr(self, 'ui_process'): self.ui_process.terminate()
                break
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"Teni: {error_msg}")
                self.logger.log_error(error_msg)

if __name__ == "__main__":
    cli = TeniCLI()
    cli.run()
