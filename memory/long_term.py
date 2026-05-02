"""
Long-Term Memory — Persistent, LLM-powered memory system.
Remembers identity, preferences, projects, relationships across sessions.
Adapted from Mark-XXXV's memory_manager.py.
"""

import json
from datetime import datetime
from threading import Lock
from pathlib import Path

from config import Config


MEMORY_PATH = Path(Config.LONG_TERM_MEMORY_FILE)
_lock = Lock()
MAX_VALUE_LENGTH = 400


def _empty_memory() -> dict:
    return {
        "identity": {},
        "preferences": {},
        "projects": {},
        "relationships": {},
        "wishes": {},
        "notes": {}
    }


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _empty_memory()
    with _lock:
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()


def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        MEMORY_PATH.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict) -> bool:
    changed = False
    for key, value in updates.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            if isinstance(value, dict) and "value" in value:
                new_val = _truncate_value(str(value["value"]))
            else:
                new_val = _truncate_value(str(value))
            entry = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True
    return changed


def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()
    memory = load_memory()
    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print(f"[Memory] 💾 Saved: {list(memory_update.keys())}")
    return memory


def should_extract_memory(user_text: str, ai_text: str, api_key: str) -> bool:
    """Stage 1: Quick YES/NO check if conversation contains memorable facts."""
    try:
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel("gemini-2.0-flash-lite")

        combined = f"User: {user_text[:300]}\nAI: {ai_text[:200]}"
        check = model.generate_content(
            f"Does this conversation contain ANY of the following?\n"
            f"- Personal facts (name, age, city, job, birthday)\n"
            f"- Preferences or favorites (food, color, music, sport)\n"
            f"- Active projects or goals\n"
            f"- People in the user's life\n"
            f"- Future plans or wishes\n\n"
            f"Reply only YES or NO.\n\nConversation:\n{combined}"
        )
        return "YES" in check.text.upper()
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ Stage1 check failed: {e}")
        return False


def extract_memory(user_text: str, ai_text: str, api_key: str) -> dict:
    """Stage 2: Detailed extraction of memorable facts."""
    try:
        import re
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel("gemini-2.0-flash-lite")

        combined = f"User: {user_text[:500]}\nAI: {ai_text[:300]}"

        raw = model.generate_content(
            f"Extract ALL memorable personal facts from this conversation.\n"
            f"Return ONLY valid JSON. Use {{}} if nothing worth saving.\n\n"
            f"Categories:\n"
            f"  identity — name, age, birthday, city, job, school\n"
            f"  preferences — favorite things, hobbies, interests\n"
            f"  projects — active projects, goals\n"
            f"  relationships — friends, family, colleagues\n"
            f"  wishes — future plans, dreams\n"
            f"  notes — anything else worth remembering\n\n"
            f'Format: {{"identity":{{"name":{{"value":"Aansh"}}}}}}\n\n'
            f"Conversation:\n{combined}\n\nJSON:"
        ).text.strip()

        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        if not raw or raw == "{}":
            return {}
        return json.loads(raw)

    except json.JSONDecodeError:
        return {}
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ Extract failed: {e}")
        return {}


def format_memory_for_prompt(memory: dict | None) -> str:
    """Format memory into a prompt-ready string."""
    if not memory:
        return ""

    lines = []
    identity = memory.get("identity", {})
    for field in ["name", "age", "birthday", "city", "job", "school", "nationality"]:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")

    for cat_name, label in [
        ("preferences", "Preferences"),
        ("projects", "Active Projects"),
        ("relationships", "People"),
        ("wishes", "Wishes / Plans"),
        ("notes", "Notes"),
    ]:
        cat = memory.get(cat_name, {})
        if cat:
            lines.append(f"\n{label}:")
            for key, entry in list(cat.items())[:10]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    if not lines:
        return ""

    header = "[WHAT YOU KNOW ABOUT AANSH — use naturally, never recite like a list]\n"
    result = header + "\n".join(lines)
    return result[:2000] + "\n"


def remember(key: str, value: str, category: str = "notes") -> str:
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    update_memory({category: {key: {"value": value}}})
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    memory = load_memory()
    cat = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_memory(memory)
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"
