import subprocess
from typing import Dict, Any

class AppleScriptControl:
    def run_script(self, script_content: str) -> Dict[str, Any]:
        """Run raw AppleScript passed dynamically."""
        try:
            if not script_content:
                return {"success": False, "error": "No script content provided."}
                
            process = subprocess.Popen(
                ['osascript', '-e', script_content],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=15)
            
            if process.returncode == 0:
                return {"success": True, "message": f"AppleScript executed: {stdout.strip()}"}
            else:
                return {"success": False, "error": f"AppleScript failed: {stderr.strip()}"}
                
        except subprocess.TimeoutExpired:
            process.kill()
            return {"success": False, "error": "AppleScript execution timed out."}
        except Exception as e:
            return {"success": False, "error": f"Failed to execute AppleScript: {str(e)}"}
