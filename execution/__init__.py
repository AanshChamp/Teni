from typing import Dict, Any
import os
import json
from .app_control import AppControl
from .file_control import FileControl
from .window_control import WindowControl
from .system_control import SystemControl
from .applescript import AppleScriptControl
from core.awareness import SystemAwareness

class ExecutionEngine:
    def __init__(self):
        self.app_control = AppControl()
        self.file_control = FileControl()
        self.window_control = WindowControl()
        self.system_control = SystemControl()
        self.applescript_control = AppleScriptControl()
        self.awareness = SystemAwareness()
    
    def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intent with multi-action support and smart app state awareness."""
        action = intent.get("action")
        target = intent.get("target")
        params = intent.get("parameters", {})
        
        # Handle multi-action commands
        if "actions" in intent:
            return self._execute_multi_action(intent)
        
        # Single action execution with smart app state
        return self._execute_single_action(action, target, params)
    
    def _execute_multi_action(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple actions in sequence."""
        actions = intent.get("actions", [])
        results = []
        
        for i, action in enumerate(actions):
            action_name = action.get("action")
            action_target = action.get("target")
            action_params = action.get("parameters", {})
            
            # Smart app state awareness
            enhanced_action = self._enhance_action_with_app_state(action_name, action_target, action_params)
            
            result = self._execute_single_action(enhanced_action["action"], enhanced_action["target"], enhanced_action["parameters"])
            results.append(result)
            
            # Stop if any action fails
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"Action {i+1} failed: {result.get('error')}",
                    "completed_actions": results[:-1],
                    "failed_action": result
                }
        
        return {
            "success": True,
            "message": f"Successfully executed {len(actions)} actions",
            "results": results
        }
    
    def _enhance_action_with_app_state(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance action with smart app state awareness."""
        enhanced_action = {
            "action": action,
            "target": target,
            "parameters": params
        }
        
        # Smart app state awareness
        if action == "open_app":
            app_name = params.get("app") or target
            if self.system_control.is_app_running(app_name):
                # App is already running, focus it instead of reopening
                enhanced_action["action"] = "focus_app"
                enhanced_action["target"] = app_name
                enhanced_action["parameters"] = {"app": app_name}
            else:
                # App is not running, open it normally
                pass
        
        elif action == "safari_control":
            # Always use safari_control for Safari operations
            pass
        
        elif action == "search_web":
            # If Safari is open, use direct search instead of opening new Safari
            if self.system_control.is_app_running("Safari"):
                enhanced_action["action"] = "safari_search"
                enhanced_action["parameters"] = {"query": params.get("query")}
            else:
                # Open Safari first, then search
                pass
        
        return enhanced_action
    
    def _execute_single_action(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action with smart enhancements."""
        try:
            if action == "open_app":
                app = params.get("app") or target
                return self.app_control.open_app(app)
            
            elif action == "close_app":
                app = params.get("app") or target
                return self.app_control.close_app(app)
            
            elif action == "open_website":
                url = params.get("url")
                return self.window_control.open_website_in_safari(url)
            
            elif action == "search_web":
                query = params.get("query")
                return self.window_control.search_web_in_safari(query)
            
            elif action == "split_screen":
                apps = params.get("apps", [])
                if len(apps) >= 2:
                    return self.window_control.split_screen(apps[0], apps[1])
                else:
                    # Fallback to old parsing
                    app1 = params.get("app") or target
                    app2 = params.get("target")
                    return self.window_control.split_screen(app1, app2)
            
            elif action == "create_folder":
                path = params.get("path")
                name = params.get("name")
                target = params.get("target")
                
                # Handle different parameter formats from LLM
                if not path and target:
                    # Convert target to path
                    if target.lower() == "desktop":
                        path = os.path.expanduser("~/Desktop")
                    elif target.lower() == "documents":
                        path = os.path.expanduser("~/Documents")
                    elif target.lower() == "downloads":
                        path = os.path.expanduser("~/Downloads")
                    else:
                        path = os.path.expanduser(f"~/{target}")
                
                return self.file_control.create_folder(path, name)
            
            elif action == "rename_file":
                path = params.get("path")
                new_name = params.get("name")
                return self.file_control.rename_file(path, new_name)
            
            elif action == "move_file":
                source = params.get("path")
                target_path = params.get("target")
                return self.file_control.move_file(source, target_path)
            
            elif action == "delete_file":
                path = params.get("path")
                return self.file_control.delete_file(path)
            
            elif action == "list_files":
                path = params.get("path")
                return self.file_control.list_files(path)
            
            elif action == "write_email_draft":
                to = params.get("to")
                subject = params.get("subject")
                body = params.get("body")
                return self.file_control.write_email_draft(to, subject, body)
            
            elif action == "run_shell_safe":
                command = params.get("command")
                return self.file_control.run_shell_safe(command)
                
            elif action == "run_applescript":
                script_content = params.get("script")
                return self.applescript_control.run_script(script_content)
            
            elif action == "safari_control":
                control_action = params.get("content") or "reopen_last_tab"
                return self.window_control.safari_control(control_action)
            
            elif action == "play_music":
                music_action = params.get("action", "play")
                app = params.get("app", "Spotify")
                return self.system_control.play_music(music_action, app)
            
            elif action == "manage_apps":
                app_action = params.get("action", "list")
                app_name = params.get("app")
                return self.system_control.manage_apps(app_action, app_name)
            
            elif action == "system_info":
                info_type = params.get("type", "all")
                return self.system_control.system_info(info_type)
            
            elif action == "volume_control":
                # Handle different parameter formats from LLM
                volume_action = params.get("action", params.get("operation", "set"))
                level = params.get("level", params.get("increment"))
                
                # Convert operation to action
                if volume_action == "increase":
                    volume_action = "up"
                elif volume_action == "decrease":
                    volume_action = "down"
                
                return self.system_control.volume_control(volume_action, level)
            
            elif action == "screenshot":
                screenshot_type = params.get("type", "screen")
                path = params.get("path")
                return self.system_control.screenshot(screenshot_type, path)
            
            elif action == "find_file":
                filename = params.get("filename")
                search_path = params.get("path")
                return self.system_control.find_file(filename, search_path)
            
            elif action == "calendar_add":
                title = params.get("title")
                date = params.get("date")
                time = params.get("time")
                return self.system_control.calendar_add(title, date, time)
            
            elif action == "reminder_add":
                title = params.get("title")
                due_date = params.get("due_date")
                return self.system_control.reminder_add(title, due_date)
            
            elif action == "login_helper":
                app = params.get("app")
                username = params.get("username")
                password = params.get("password")
                return self.system_control.login_helper(app, username, password)
            
            # Handle enhanced actions from smart state awareness
            elif action == "focus_app":
                app = params.get("app")
                return self.app_control.focus_app(app)
            
            elif action == "safari_search":
                query = params.get("query")
                return self.window_control.search_in_safari(query)
            
            elif action == "type_text":
                text = params.get("text") or params.get("content", "")
                return self.awareness.type_text(text)
            
            elif action == "compose_email":
                to = params.get("to", "")
                subject = params.get("subject", "")
                body = params.get("body") or params.get("content", "")
                return self.awareness.compose_email(to, subject, body)
            
            elif action == "add_calendar_event":
                title = params.get("title", "")
                date = params.get("date", "")
                time_str = params.get("time", "09:00")
                return self.awareness.add_calendar_event(title, date, time_str)
            
            elif action == "split_windows":
                app1 = params.get("app1") or params.get("app", "")
                app2 = params.get("app2") or params.get("target", "")
                return self.awareness.split_windows(app1, app2)
            
            elif action == "activate_app":
                app_name = params.get("app", "")
                return self.awareness.activate_app(app_name)
            
            elif action == "get_context":
                ctx = self.awareness.get_context()
                return {"success": True, "message": json.dumps(ctx, indent=2)}
            
            elif action == "open_url":
                url = params.get("url", "")
                return self.awareness.open_url_in_safari(url)
            
            elif action == "create_note":
                title = params.get("title", "Untitled")
                body = params.get("body") or params.get("content") or params.get("text", "")
                return self.awareness.create_note(title, body)
            
            elif action == "append_note":
                title = params.get("title", "")
                text = params.get("text") or params.get("content", "")
                return self.awareness.append_to_note(title, text)
            
            elif action == "list_notes":
                return self.awareness.list_notes()
            
            elif action == "press_key":
                key = params.get("key", "")
                mods = params.get("modifiers", "")
                return self.awareness.press_key(key, mods)
            
            elif action == "minimize_app":
                app_name = params.get("app", "")
                return self.awareness.minimize_app(app_name)
            
            elif action == "fullscreen_app":
                app_name = params.get("app", "")
                return self.awareness.fullscreen_app(app_name)
            
            elif action == "safari_fill_field":
                field = params.get("field", "")
                value = params.get("value") or params.get("text", "")
                return self.awareness.safari_type_in_field(field, value)
            
            elif action == "safari_click":
                button_text = params.get("button") or params.get("text", "")
                return self.awareness.safari_click_button(button_text)
            
            elif action == "safari_read_page":
                text = self.awareness.safari_get_page_text()
                return {"success": True, "message": text[:500]}
            
            elif action == "auto_login":
                service = params.get("service") or params.get("app", "")
                return self.awareness.auto_login_safari(service)
            
            elif action == "keychain_get":
                service = params.get("service", "")
                return self.awareness.keychain_get_password(service)
            
            elif action == "git_status":
                path = params.get("path", ".")
                return self.awareness.git_status(path)
            
            elif action == "git_push":
                path = params.get("path", ".")
                msg = params.get("message", "Updates from Teni")
                return self.awareness.git_push(path, msg)
            
            elif action == "github_issues":
                repo = params.get("repo", "")
                return self.awareness.github_list_issues(repo)
            
            elif action == "github_me":
                return self.awareness.github_user_info()
            
            elif action == "screen_process":
                try:
                    from actions.vision import screen_process
                    text = params.get("text", "What's on my screen?")
                    angle = params.get("angle", "screen")
                    result_msg = screen_process({"text": text, "angle": angle})
                    return {"success": True, "message": result_msg}
                except Exception as e:
                    return {"success": False, "error": f"Vision error: {str(e)}"}
            
            elif action == "save_memory":
                try:
                    from memory.long_term import update_memory
                    cat = params.get("category", "notes")
                    key = params.get("key", "")
                    val = params.get("value", "")
                    if key and val:
                        update_memory({cat: {key: {"value": val}}})
                    return {"success": True, "message": "Memory saved."}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        except Exception as e:
            return {"success": False, "error": f"Execution error: {str(e)}"}
