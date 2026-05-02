import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    NVIDIA_API_KEY = "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"
    LLM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
    MODEL = "mistralai/mistral-large-3-675b-instruct-2512"
    TEMPERATURE = 0.2
    MAX_TOKENS = 1024
    
    LOGS_DIR = os.path.expanduser("~/teni/logs")
    MEMORY_FILE = os.path.expanduser("~/teni/memory/memory.json")
    
    ALLOWED_ACTIONS = [
        "open_app",
        "close_app", 
        "open_website",
        "create_folder",
        "rename_file",
        "move_file",
        "delete_file",
        "list_files",
        "search_web",
        "split_screen",
        "write_email_draft",
        "run_shell_safe",
        "safari_control",
        "play_music",
        "manage_apps",
        "system_info",
        "volume_control",
        "screenshot",
        "find_file",
        "calendar_add",
        "reminder_add",
        "login_helper"
    ]
    
    SAFE_SHELL_COMMANDS = [
        "ls", "pwd", "open", "mkdir", "echo"
    ]
