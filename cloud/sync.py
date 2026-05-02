"""
Cloud Sync — Export/import memory and state for cloud persistence.
This module handles serialisation. Actual cloud transport (API, S3, etc.)
is plugged in later as a deployment step.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional


class CloudSync:
    """Handles packaging local state for cloud upload and restoring from cloud."""

    MEMORY_FILE = os.path.expanduser("~/teni/memory/memory.json")
    STATE_FILE = os.path.expanduser("~/Teni/state.json")
    SYNC_DIR = os.path.expanduser("~/teni/cloud_sync")

    def __init__(self):
        os.makedirs(self.SYNC_DIR, exist_ok=True)

    # ── Export (local → cloud) ──

    def export_snapshot(self) -> str:
        """
        Bundle memory + personality state into a timestamped snapshot file.
        Returns the path to the snapshot JSON.
        """
        snapshot: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "memory": self._read_json(self.MEMORY_FILE),
            "personality": self._read_json(self.STATE_FILE),
        }

        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.SYNC_DIR, filename)

        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2)

        # Keep only the last 10 snapshots
        self._prune_snapshots(keep=10)

        print(f"☁️  Snapshot exported: {path}")
        return path

    def get_latest_snapshot(self) -> Optional[str]:
        """Get the path to the most recent snapshot."""
        files = sorted(
            [f for f in os.listdir(self.SYNC_DIR) if f.startswith("snapshot_")],
            reverse=True,
        )
        return os.path.join(self.SYNC_DIR, files[0]) if files else None

    # ── Import (cloud → local) ──

    def import_snapshot(self, snapshot_path: str) -> bool:
        """Restore memory + personality from a snapshot file."""
        try:
            with open(snapshot_path, "r") as f:
                snapshot = json.load(f)

            # Restore memory
            if "memory" in snapshot and snapshot["memory"]:
                os.makedirs(os.path.dirname(self.MEMORY_FILE), exist_ok=True)
                with open(self.MEMORY_FILE, "w") as f:
                    json.dump(snapshot["memory"], f, indent=2)

            # Restore personality state
            if "personality" in snapshot and snapshot["personality"]:
                with open(self.STATE_FILE, "w") as f:
                    json.dump(snapshot["personality"], f, indent=2)

            print(f"☁️  Snapshot restored from: {snapshot_path}")
            return True

        except Exception as e:
            print(f"☁️  Restore failed: {e}")
            return False

    # ── Helpers ──

    def _read_json(self, path: str) -> Optional[Dict]:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _prune_snapshots(self, keep: int = 10):
        files = sorted(
            [f for f in os.listdir(self.SYNC_DIR) if f.startswith("snapshot_")]
        )
        while len(files) > keep:
            os.remove(os.path.join(self.SYNC_DIR, files.pop(0)))
