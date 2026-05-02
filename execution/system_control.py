"""
System Control - Advanced macOS operations with admin access
"""

import subprocess
import os
import json
from typing import Dict, Any, List
from datetime import datetime
from security.input_sanitizer import InputSanitizer
from security.permission_layer import PermissionLayer

class SystemControl:
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.permission_layer = PermissionLayer()
    
    def play_music(self, action: str, app: str = "Spotify") -> Dict[str, Any]:
        """Control music playback with admin access."""
        try:
            # Sanitize inputs
            safe_action = self.sanitizer.sanitize_applescript_string(action)
            safe_app = self.sanitizer.sanitize_app_name(app)
            
            if not safe_action or not safe_app:
                return {"success": False, "error": "Invalid music control parameters"}
            
            if app.lower() == "spotify":
                if safe_action == "play":
                    script = f'''
                    tell application "{safe_app}"
                        play
                    end tell
                    '''
                elif safe_action == "pause":
                    script = f'''
                    tell application "{safe_app}"
                        pause
                    end tell
                    '''
                elif safe_action == "next":
                    script = f'''
                    tell application "{safe_app}"
                        next track
                    end tell
                    '''
                elif safe_action == "previous":
                    script = f'''
                    tell application "{safe_app}"
                        previous track
                    end tell
                    '''
                else:
                    return {"success": False, "error": f"Unknown music action: {safe_action}"}
            elif app.lower() == "music" or app.lower() == "itunes":
                if safe_action == "play":
                    script = f'''
                    tell application "Music"
                        play
                    end tell
                    '''
                elif safe_action == "pause":
                    script = f'''
                    tell application "Music"
                        pause
                    end tell
                    '''
                elif safe_action == "next":
                    script = f'''
                    tell application "Music"
                        next track
                    end tell
                    '''
                elif safe_action == "previous":
                    script = f'''
                    tell application "Music"
                        previous track
                    end tell
                    '''
                else:
                    return {"success": False, "error": f"Unknown music action: {safe_action}"}
            else:
                return {"success": False, "error": f"Unsupported music app: {safe_app}"}
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"{safe_action.capitalize()} {safe_app}"}
            else:
                return {"success": False, "error": f"Music control failed: {result.stderr}"}
        
        except Exception as e:
            return {"success": False, "error": f"Music control error: {str(e)}"}
    
    def volume_control(self, action: str, level: int = None) -> Dict[str, Any]:
        """Control system volume with admin access."""
        try:
            # Sanitize inputs
            safe_action = self.sanitizer.sanitize_applescript_string(action)
            safe_level = str(level) if level is not None else None
            
            if not safe_action:
                return {"success": False, "error": "Invalid volume control action"}
            
            if safe_action == "set" and safe_level:
                try:
                    level_int = int(safe_level)
                    if level_int < 0 or level_int > 100:
                        return {"success": False, "error": "Volume level must be between 0 and 100"}
                except ValueError:
                    return {"success": False, "error": "Invalid volume level"}
                
                script = f'''
                set volume output volume {level_int}
                '''
            elif safe_action == "mute":
                script = '''
                set volume output muted true
                '''
            elif safe_action == "unmute":
                script = '''
                set volume output muted false
                '''
            elif safe_action == "up":
                script = '''
                set volume output volume (output volume of (get volume settings) + 10)
                '''
            elif safe_action == "down":
                script = '''
                set volume output volume (output volume of (get volume settings) - 10)
                '''
            else:
                return {"success": False, "error": f"Unknown volume action: {safe_action}"}
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Volume {safe_action}"}
            else:
                return {"success": False, "error": f"Volume control failed: {result.stderr}"}
        
        except Exception as e:
            return {"success": False, "error": f"Volume control error: {str(e)}"}
    
    def manage_apps(self, action: str, app_name: str = None) -> Dict[str, Any]:
        """Advanced app management with admin access."""
        try:
            # Sanitize inputs
            safe_action = self.sanitizer.sanitize_applescript_string(action)
            safe_app = self.sanitizer.sanitize_app_name(app_name) if app_name else None
            
            if not safe_action:
                return {"success": False, "error": "Invalid app management action"}
            
            if safe_action == "list":
                script = '''
                tell application "System Events"
                    set appList to name of every process whose background only is false
                end tell
                '''
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    apps = [app.strip() for app in result.stdout.split(",")]
                    return {"success": True, "message": "Running apps", "apps": apps}
                else:
                    return {"success": False, "error": "Failed to list apps"}
            
            elif safe_action == "force_quit" and safe_app:
                script = f'''
                tell application "{safe_app}" to quit
                '''
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    return {"success": True, "message": f"Force quit {safe_app}"}
                else:
                    return {"success": False, "error": f"Failed to force quit {safe_app}"}
            
            elif safe_action == "minimize" and safe_app:
                script = f'''
                tell application "{safe_app}"
                    set minimized of window 1 to true
                end tell
                '''
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    return {"success": True, "message": f"Minimized {safe_app}"}
                else:
                    return {"success": False, "error": f"Failed to minimize {safe_app}"}
            
            elif safe_action == "maximize" and safe_app:
                script = f'''
                tell application "{safe_app}"
                    set zoomed of window 1 to True
                end tell
                '''
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    return {"success": True, "message": f"Maximized {safe_app}"}
                else:
                    return {"success": False, "error": f"Failed to maximize {safe_app}"}
            
            else:
                return {"success": False, "error": "Invalid app management action"}
        
        except Exception as e:
            return {"success": False, "error": f"App management error: {str(e)}"}
    
    def screenshot(self, screenshot_type: str, path: str = None) -> Dict[str, Any]:
        """Take screenshots with admin access."""
        try:
            # Sanitize inputs
            safe_type = self.sanitizer.sanitize_applescript_string(screenshot_type)
            safe_path = self.sanitizer.sanitize_file_path(path) if path else None
            
            if not safe_type:
                return {"success": False, "error": "Invalid screenshot type"}
            
            if not safe_path:
                safe_path = os.path.expanduser("~/Desktop")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if safe_type == "screen":
                filename = f"screenshot_{timestamp}.png"
                full_path = os.path.join(safe_path, filename)
                
                script = f'''
                do shell script "screencapture {full_path}"
                '''
            elif safe_type == "window":
                filename = f"window_screenshot_{timestamp}.png"
                full_path = os.path.join(safe_path, filename)
                
                script = f'''
                do shell script "screencapture -w {full_path}"
                '''
            elif safe_type == "selection":
                filename = f"selection_screenshot_{timestamp}.png"
                full_path = os.path.join(safe_path, filename)
                
                script = f'''
                do shell script "screencapture -i {full_path}"
                '''
            else:
                return {"success": False, "error": f"Unknown screenshot type: {safe_type}"}
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Screenshot saved to {full_path}", "path": full_path}
            else:
                return {"success": False, "error": f"Screenshot failed: {result.stderr}"}
        
        except Exception as e:
            return {"success": False, "error": f"Screenshot error: {str(e)}"}
    
    def system_info(self, info_type: str = "all") -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            # Sanitize input
            safe_type = self.sanitizer.sanitize_applescript_string(info_type)
            
            if not safe_type:
                return {"success": False, "error": "Invalid system info type"}
            
            info = {}
            
            if info_type in ["all", "hardware"]:
                # Get hardware info
                script = '''
                tell application "System Events"
                    set hardwareInfo to {}
                    set hardwareInfo's item 1 to system version
                    set hardwareInfo's item 2 to machine model
                    set hardwareInfo's item 3 to physical memory
                    return hardwareInfo
                end tell
                '''
                result = subprocess.run([
                    "osascript", "-e", script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    info["hardware"] = result.stdout.strip()
            
            if info_type in ["all", "storage"]:
                # Get storage info
                result = subprocess.run([
                    "df", "-h", "/"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    if len(lines) >= 2:
                        info["storage"] = lines[1]
            
            if info_type in ["all", "battery"]:
                # Get battery info
                result = subprocess.run([
                    "pmset", "-g", "batt"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    info["battery"] = result.stdout.strip()
            
            if info_type in ["all", "network"]:
                # Get network info
                result = subprocess.run([
                    "ifconfig", "en0"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    info["network"] = "Network interface available"
            
            return {"success": True, "message": "System information", "info": info}
        
        except Exception as e:
            return {"success": False, "error": f"System info error: {str(e)}"}
    
    def find_file(self, filename: str, search_path: str = None) -> Dict[str, Any]:
        """Find files with admin access."""
        try:
            # Sanitize inputs
            safe_filename = self.sanitizer.sanitize_search_query(filename)
            safe_path = self.sanitizer.sanitize_file_path(search_path) if search_path else None
            
            if not safe_filename or not safe_path:
                return {"success": False, "error": "Invalid search parameters"}
            
            if not safe_path:
                safe_path = os.path.expanduser("~")
            
            # Use find command with proper argument separation
            result = subprocess.run([
                "find", safe_path, "-name", f"*{safe_filename}*", "-type", "f"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                return {"success": True, "message": f"Found {len(files)} files", "files": files}
            else:
                return {"success": False, "error": "File search failed"}
        
        except Exception as e:
            return {"success": False, "error": f"File search error: {str(e)}"}
    
    def search_in_safari(self, query: str) -> Dict[str, Any]:
        """Search in Safari without opening new window."""
        try:
            # Sanitize query
            safe_query = self.sanitizer.sanitize_search_query(query)
            
            script = f'''
            tell application "Safari"
                activate
                delay 0.5
                tell application "System Events"
                    tell process "Safari"
                        keystroke "f" using command down
                    delay 0.5
                        keystroke "{safe_query}" using command down
                        delay 1
                        keystroke "return"
                    end tell
                end tell
            end tell
            '''
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Searched Safari for: {safe_query}"}
            else:
                return {"success": False, "error": f"Safari search failed: {result.stderr}"}
        
        except Exception as e:
            return {"success": False, "error": f"Safari search error: {str(e)}"}
    
    def reminder_add(self, title: str, due_date: str = None) -> Dict[str, Any]:
        """Add reminders with admin access."""
        try:
            # Sanitize inputs
            safe_title = self.sanitizer.sanitize_title_string(title)
            safe_date = self.sanitizer.sanitize_date_string(due_date) if due_date else None
            
            if not safe_title:
                return {"success": False, "error": "Invalid reminder parameters"}
            
            if safe_date:
                script = f'''
                tell application "Reminders"
                    tell list "Reminders"
                        make new reminder with properties {{name:"{safe_title}", due date:date "{safe_date}"}}
                    end tell
                end tell
                '''
            else:
                script = f'''
                tell application "Reminders"
                    tell list "Reminders"
                        make new reminder with properties {{name:"{safe_title}"}}
                    end tell
                end tell
                '''
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Added reminder: {safe_title}"}
            else:
                return {"success": False, "error": f"Reminder add failed: {result.stderr}"}
        
        except Exception as e:
            return {"success": False, "error": f"Reminder error: {str(e)}"}
    
    def is_app_running(self, app_name: str) -> bool:
        """Check if an application is currently running."""
        try:
            # Sanitize app name
            safe_app = self.sanitizer.sanitize_app_name(app_name)
            
            script = f'''
            tell application "System Events"
                if (exists process "{safe_app}") then
                    return "running"
                else
                    return "not_running"
                end if
            end tell
            '''
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return "running" in result.stdout.strip()
            
            return False
            
        except Exception as e:
            return False
