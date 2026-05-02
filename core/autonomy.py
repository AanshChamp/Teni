"""
Autonomy Engine — Lets Teni proactively suggest and queue tasks.
The heartbeat checks this engine during idle time.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class AutonomyEngine:
    """
    Manages a queue of autonomous tasks that Teni can suggest or execute
    when idle, based on learned patterns from memory.
    """

    TASK_FILE = os.path.expanduser("~/teni/memory/autonomous_tasks.json")

    def __init__(self):
        self.pending_tasks: List[Dict[str, Any]] = []
        self._load_tasks()

    # ── Task Queue ──

    def suggest_task(self, description: str, action: Dict[str, Any], priority: int = 5):
        """
        Queue a proactive task. Priority 1-10 (10 = urgent).
        These get surfaced to the user during idle periods.
        """
        task = {
            "id": len(self.pending_tasks) + 1,
            "description": description,
            "action": action,
            "priority": priority,
            "suggested_at": datetime.now().isoformat(),
            "status": "pending",  # pending | approved | rejected | completed
        }
        self.pending_tasks.append(task)
        self._save_tasks()

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending tasks sorted by priority (highest first)."""
        return sorted(
            [t for t in self.pending_tasks if t["status"] == "pending"],
            key=lambda t: t["priority"],
            reverse=True,
        )

    def approve_task(self, task_id: int):
        for t in self.pending_tasks:
            if t["id"] == task_id:
                t["status"] = "approved"
                self._save_tasks()
                return t
        return None

    def reject_task(self, task_id: int):
        for t in self.pending_tasks:
            if t["id"] == task_id:
                t["status"] = "rejected"
                self._save_tasks()
                return
        return None

    def complete_task(self, task_id: int):
        for t in self.pending_tasks:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                self._save_tasks()
                return

    # ── Pattern-based suggestions ──

    def analyse_and_suggest(self, memory_data: Dict[str, Any]):
        """
        Look at memory patterns and generate proactive suggestions.
        Called by the Heartbeat during long idle periods.
        """
        suggestions_made = 0

        # 1. If the user has many failed commands, suggest retrying
        stats = memory_data.get("stats", {})
        failed = stats.get("failed_commands", 0)
        total = stats.get("total_commands", 0)

        if total > 10 and failed / total > 0.3:
            self.suggest_task(
                "Your recent command failure rate is high. Want me to review and retry failed commands?",
                {"action": "review_failures"},
                priority=7,
            )
            suggestions_made += 1

        # 2. If there are upcoming deadlines, remind
        deadlines = memory_data.get("deadlines", [])
        for deadline in deadlines[:3]:
            self.suggest_task(
                f"Upcoming deadline: {deadline.get('title', 'Unknown')}",
                {"action": "reminder_add", "parameters": {"title": deadline.get("title")}},
                priority=8,
            )
            suggestions_made += 1

        # 3. Suggest organizing downloads if there are many recent file operations
        recent_files = memory_data.get("recent_files", [])
        if len(recent_files) > 20:
            self.suggest_task(
                "You have a lot of recent file activity. Want me to organize your Downloads folder?",
                {"action": "agent_task", "parameters": {"goal": "organize Downloads folder by file type"}},
                priority=4,
            )
            suggestions_made += 1

        return suggestions_made

    # ── Persistence ──

    def _load_tasks(self):
        try:
            if os.path.exists(self.TASK_FILE):
                with open(self.TASK_FILE, "r") as f:
                    self.pending_tasks = json.load(f)
        except Exception:
            self.pending_tasks = []

    def _save_tasks(self):
        try:
            os.makedirs(os.path.dirname(self.TASK_FILE), exist_ok=True)
            with open(self.TASK_FILE, "w") as f:
                json.dump(self.pending_tasks, f, indent=2)
        except Exception:
            pass
