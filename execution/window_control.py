import subprocess
from typing import Dict, Any

class WindowControl:
    @staticmethod
    def open_website_in_safari(url: str) -> Dict[str, Any]:
        try:
            activate_result = subprocess.run([
                "osascript", "-e", 'tell application "Safari" to activate'
            ], capture_output=True, text=True, timeout=5)
            
            if activate_result.returncode != 0:
                return {"success": False, "error": f"Failed to activate Safari: {activate_result.stderr}"}
            
            open_result = subprocess.run([
                "osascript", "-e", f'tell application "Safari" to open location "{url}"'
            ], capture_output=True, text=True, timeout=10)
            
            if open_result.returncode == 0:
                return {"success": True, "message": f"Opened {url} in Safari"}
            else:
                return {"success": False, "error": f"Failed to open URL: {open_result.stderr}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout opening website"}
        except Exception as e:
            return {"success": False, "error": f"Error opening website: {str(e)}"}
    
    @staticmethod
    def search_web_in_safari(query: str) -> Dict[str, Any]:
        search_url = f"https://www.google.com/search?q={query}"
        return WindowControl.open_website_in_safari(search_url)
    
    @staticmethod
    def safari_control(action: str) -> Dict[str, Any]:
        try:
            # Add retry logic for Safari control
            for attempt in range(2):
                if action == "reopen_last_tab" or action == "open_last_tab":
                    script = '''
                    tell application "Safari" to activate
                    delay 0.5
                    tell application "System Events"
                        tell process "Safari"
                            keystroke "t" using command down
                            delay 0.2
                            keystroke "w" using command down
                            delay 0.2
                            keystroke "z" using command down
                        end tell
                    end tell
                    '''
                elif action == "go_back":
                    script = '''
                    tell application "Safari" to activate
                    delay 0.5
                    tell application "System Events"
                        tell process "Safari"
                            keystroke "[" using command down
                        end tell
                    end tell
                    '''
                elif action == "go_forward":
                    script = '''
                    tell application "Safari" to activate
                    delay 0.5
                    tell application "System Events"
                        tell process "Safari"
                            keystroke "]" using command down
                        end tell
                    end tell
                    '''
                else:
                    return {"success": False, "error": f"Unknown Safari control action: {action}"}
                
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    return {"success": True, "message": f"Safari control executed: {action}"}
                elif attempt == 0:
                    # Retry once on first attempt
                    continue
                else:
                    return {"success": False, "error": f"Safari control failed: {result.stderr}"}
            
            return {"success": False, "error": "Safari control timeout after retry"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Safari control timeout after retry"}
        except Exception as e:
            return {"success": False, "error": f"Safari control error: {str(e)}"}
    
    @staticmethod
    def split_screen(app1: str, app2: str) -> Dict[str, Any]:
        try:
            if not app2:
                return {"success": False, "error": "Second app not specified for split screen"}
            
            # Launch and activate both apps
            launch_script = f'''
            tell application "{app1}" to launch
            delay 1
            tell application "{app1}" to activate
            delay 0.5
            
            tell application "{app2}" to launch
            delay 1
            tell application "{app2}" to activate
            delay 0.5
            '''
            
            # Special handling for Safari to create a new window
            if app1.lower() == "safari":
                safari_script = '''
                tell application "Safari"
                    make new document
                    activate
                end tell
                delay 1
                '''
                subprocess.run(["osascript", "-e", safari_script], capture_output=True, text=True, timeout=5)
            
            if app2.lower() == "safari":
                safari_script = '''
                tell application "Safari"
                    make new document
                    activate
                end tell
                delay 1
                '''
                subprocess.run(["osascript", "-e", safari_script], capture_output=True, text=True, timeout=5)
            
            launch_result = subprocess.run([
                "osascript", "-e", launch_script
            ], capture_output=True, text=True, timeout=10)
            
            if launch_result.returncode != 0:
                return {"success": False, "error": f"Failed to launch apps: {launch_result.stderr}"}
            
            # Use native macOS split screen
            split_script = f'''
            tell application "{app1}" to activate
            delay 1
            
            tell application "System Events"
                tell process "{app1}"
                    -- Make sure window is not maximized first
                    try
                        keystroke "f" using {{control down, command down}}
                        delay 0.5
                    end try
                    
                    -- Move window to left edge to trigger split screen
                    set position of window 1 to {{0, 0}}
                    delay 0.5
                    
                    -- Hold option and click the green button to trigger split screen
                    tell application "System Events"
                        key down option
                        delay 0.2
                        -- Click the green button (zoom button) in window title bar
                        click button 1 of window 1 of process "{app1}"
                        delay 0.2
                        key up option
                    end tell
                end tell
            end tell
            
            delay 3
            
            tell application "{app2}" to activate
            delay 1
            
            tell application "System Events"
                tell process "{app2}"
                    -- The second app should automatically appear in the right space
                    -- If not, try to select it from Mission Control
                    delay 1
                end tell
            end tell
            '''
            
            result = subprocess.run([
                "osascript", "-e", split_script
            ], capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Split screen {app1} and {app2}"}
            else:
                # Fallback to manual positioning if native split screen fails
                fallback_script = f'''
                tell application "{app1}" to activate
                delay 1
                tell application "System Events"
                    tell process "{app1}"
                        if windows exists then
                            set position of window 1 to {{0, 0}}
                            set size of window 1 to {{960, 1080}}
                        end if
                    end tell
                end tell
                
                delay 0.5
                
                tell application "{app2}" to activate
                delay 1
                tell application "System Events"
                    tell process "{app2}"
                        if windows exists then
                            set position of window 1 to {{960, 0}}
                            set size of window 1 to {{960, 1080}}
                        end if
                    end tell
                end tell
                '''
                
                fallback_result = subprocess.run([
                    "osascript", "-e", fallback_script
                ], capture_output=True, text=True, timeout=15)
                
                if fallback_result.returncode == 0:
                    return {"success": True, "message": f"Split screen {app1} and {app2} (manual positioning)"}
                else:
                    return {"success": False, "error": f"Failed to split screen: {result.stderr}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout setting up split screen"}
        except Exception as e:
            return {"success": False, "error": f"Error setting up split screen: {str(e)}"}
