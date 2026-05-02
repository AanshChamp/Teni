import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── NVIDIA (Legacy LLM) ──
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    LLM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
    MODEL = "mistralai/mistral-large-3-675b-instruct-2512"
    TEMPERATURE = 0.2
    MAX_TOKENS = 1024

    # ── Gemini Live Audio ──
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
    GEMINI_VOICE = "Charon"
    SEND_SAMPLE_RATE = 16000
    RECEIVE_SAMPLE_RATE = 24000
    AUDIO_CHANNELS = 1
    AUDIO_CHUNK_SIZE = 1024

    # ── Paths ──
    LOGS_DIR = os.path.expanduser("~/Teni/logs")
    MEMORY_FILE = os.path.expanduser("~/Teni/memory/memory.json")
    LONG_TERM_MEMORY_FILE = os.path.expanduser("~/Teni/memory/long_term.json")
    STATE_FILE = os.path.expanduser("~/Teni/state.json")
    VOICE_PROFILE = os.path.expanduser("~/Teni/voice_profile.npy")
    
    ALLOWED_ACTIONS = [
        "open_app", "close_app", "activate_app", "minimize_app", "fullscreen_app",
        "open_website", "create_folder", "rename_file", "move_file", "delete_file",
        "list_files", "search_web", "split_screen", "split_windows",
        "write_email_draft", "compose_email", "run_shell_safe",
        "safari_control", "safari_fill_field", "safari_click", "safari_read_page",
        "play_music", "manage_apps", "system_info", "volume_control", "screenshot",
        "find_file", "calendar_add", "reminder_add", "login_helper", "auto_login",
        "create_note", "append_note", "list_notes",
        "type_text", "press_key",
        "keychain_get",
        "git_status", "git_push", "github_issues", "github_me",
        "screen_process", "browser_control",
        "save_memory",
    ]
    
    SAFE_SHELL_COMMANDS = [
        "ls", "pwd", "open", "mkdir", "echo", "git", "gh"
    ]
