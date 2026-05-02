import os
import subprocess
from typing import Dict, Any
from config import Config

class ShellControl:
    @staticmethod
    def run_safe_command(command: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.path.expanduser("~")
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": result.stdout.strip(),
                    "stderr": result.stderr.strip()
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip(),
                    "stdout": result.stdout.strip()
                }
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": f"Command execution error: {str(e)}"}
