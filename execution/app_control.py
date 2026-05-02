import subprocess
from typing import Dict, Any, Optional

class AppControl:
    @staticmethod
    def open_app(app_name: str) -> Dict[str, Any]:
        try:
            # Smart Activation: Don't quit, just bring to front or launch
            script = f'''
            tell application "System Events"
                if (exists process "{app_name}") then
                    tell application "{app_name}" to activate
                    return "Activated existing process"
                else
                    tell application "{app_name}" to activate
                    return "Launched new process"
                end if
            end tell
            '''
            
            result = subprocess.run([
                "osascript", "-e", script
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Opened {app_name}"}
            else:
                # Fallback to direct launch
                subprocess.run(["open", "-a", app_name])
                return {"success": True, "message": f"Launched {app_name} via fallback"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout opening {app_name}"}
        except Exception as e:
            return {"success": False, "error": f"Error opening {app_name}: {str(e)}"}

    
    @staticmethod
    def focus_app(app_name: str) -> Dict[str, Any]:
        """Focus an application."""
        try:
            result = subprocess.run([
                "osascript", "-e", f'tell application "{app_name}" to activate'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Focused {app_name}"}
            else:
                return {"success": False, "error": f"Failed to focus {app_name}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout focusing {app_name}"}
        except Exception as e:
            return {"success": False, "error": f"Error focusing {app_name}: {str(e)}"}
    
    @staticmethod
    def close_app(app_name: str) -> Dict[str, Any]:
        try:
            result = subprocess.run([
                "osascript", "-e", f'tell application "{app_name}" to quit'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "message": f"Closed {app_name}"}
            else:
                return {"success": False, "error": f"Failed to close {app_name}: {result.stderr}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout closing {app_name}"}
        except Exception as e:
            return {"success": False, "error": f"Error closing {app_name}: {str(e)}"}
