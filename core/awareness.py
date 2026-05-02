"""
System Awareness — Full macOS control and awareness.
Uses AppleScript for native app control, Keychain access, and page interaction.
"""

import subprocess
import json
import time
from typing import Dict, Any, Optional, List


class SystemAwareness:
    """Real-time awareness + deep control of macOS."""

    # ═══════════════════════ AWARENESS ═══════════════════════

    def get_context(self) -> Dict[str, Any]:
        """Full snapshot of current system state."""
        return {
            "frontmost_app": self.get_frontmost_app(),
            "window_title": self.get_window_title(),
            "clipboard": self.get_clipboard(),
            "running_apps": self.get_running_apps(),
            "screen_size": self.get_screen_size(),
        }

    def get_deep_context(self) -> Dict[str, Any]:
        """Extended snapshot of system state."""
        ctx = self.get_context()
        ctx.update({
            "battery": self.get_battery(),
            "time": time.strftime("%H:%M"),
            "desktop_analysis": self.get_desktop_analysis(),
        })
        return ctx

    def get_battery(self) -> str:
        try:
            r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
            return r.stdout.split("\n")[1].split(";")[0].split("\t")[1].strip()
        except: return "N/A"

    def get_desktop_analysis(self) -> Dict[str, Any]:
        """Scan desktop for file count and types."""
        desktop = os.path.expanduser("~/Desktop")
        try:
            files = os.listdir(desktop)
            return {
                "file_count": len(files),
                "clutter_score": min(100, len(files) * 5),
                "types": list(set([os.path.splitext(f)[1] for f in files if "." in f]))
            }
        except: return {}

    def get_frontmost_app(self) -> str:
        return self._run_osascript(
            'tell application "System Events" to return name of first process whose frontmost is true'
        )

    def get_window_title(self) -> str:
        return self._run_osascript(
            'tell application "System Events" to return name of front window of (first process whose frontmost is true)'
        )

    def get_clipboard(self) -> str:
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            return result.stdout.strip()[:500]
        except Exception:
            return ""

    def get_running_apps(self) -> list:
        raw = self._run_osascript(
            'tell application "System Events" to return name of every process whose background only is false'
        )
        if raw:
            return [a.strip() for a in raw.split(",")]
        return []

    def get_screen_size(self) -> Dict[str, int]:
        raw = self._run_osascript(
            'tell application "Finder" to get bounds of window of desktop'
        )
        try:
            parts = [int(x.strip()) for x in raw.split(",")]
            return {"width": parts[2], "height": parts[3]}
        except Exception:
            return {"width": 1440, "height": 900}

    # ═══════════════════════ TEXT INPUT ═══════════════════════

    def type_text(self, text: str) -> Dict[str, Any]:
        """Type text into the currently focused app using clipboard paste (fast & reliable)."""
        try:
            # Save current clipboard
            old_clip = self.get_clipboard()
            # Set clipboard to our text
            subprocess.run(["pbcopy"], input=text.encode(), timeout=2)
            # Paste via Cmd+V
            self._run_osascript(
                'tell application "System Events" to keystroke "v" using command down'
            )
            time.sleep(0.3)
            # Restore old clipboard
            if old_clip:
                subprocess.run(["pbcopy"], input=old_clip.encode(), timeout=2)
            return {"success": True, "message": f"Typed {len(text)} characters"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def press_key(self, key: str, modifiers: str = "") -> Dict[str, Any]:
        """Press a key combo. modifiers: comma-separated (command, shift, option, control)."""
        mod_str = ""
        if modifiers:
            parts = [f"{m.strip()} down" for m in modifiers.split(",")]
            mod_str = " using {" + ", ".join(parts) + "}"

        # Handle special keys
        special_keys = {
            "return": "return", "enter": "return", "tab": "tab",
            "escape": "escape", "esc": "escape",
            "delete": "delete", "backspace": "delete",
            "space": "space", "up": "up arrow", "down": "down arrow",
            "left": "left arrow", "right": "right arrow",
        }

        if key.lower() in special_keys:
            return self._run_osascript_result(
                f'tell application "System Events" to key code {self._key_code(key.lower())}{mod_str}'
            )
        else:
            return self._run_osascript_result(
                f'tell application "System Events" to keystroke "{key}"{mod_str}'
            )

    def _key_code(self, key: str) -> int:
        codes = {"return": 36, "tab": 48, "escape": 53, "delete": 51, "space": 49,
                 "up": 126, "down": 125, "left": 123, "right": 124}
        return codes.get(key, 36)

    # ═══════════════════════ NOTES.APP ═══════════════════════

    def create_note(self, title: str, body: str) -> Dict[str, Any]:
        """Create a new note in Notes.app with title and body."""
        escaped_body = body.replace('"', '\\"').replace('\n', '\\n')
        script = f'''
tell application "Notes"
    activate
    tell account "iCloud"
        make new note at folder "Notes" with properties {{name:"{title}", body:"{escaped_body}"}}
    end tell
end tell
'''
        return self._run_osascript_result(script)

    def append_to_note(self, title: str, text: str) -> Dict[str, Any]:
        """Append text to an existing note by title."""
        escaped = text.replace('"', '\\"')
        script = f'''
tell application "Notes"
    activate
    set targetNote to first note whose name is "{title}"
    set body of targetNote to (body of targetNote) & "<br>" & "{escaped}"
end tell
'''
        return self._run_osascript_result(script)

    def list_notes(self) -> Dict[str, Any]:
        """List the names of the most recent notes."""
        script = '''
tell application "Notes"
    set noteNames to {}
    repeat with n in (notes 1 thru (min of {10, count of notes}))
        set end of noteNames to name of n
    end repeat
    return noteNames
end tell
'''
        result = self._run_osascript(script)
        return {"success": True, "message": result}

    # ═══════════════════════ WINDOW MANAGEMENT ═══════════════════════

    def split_windows(self, app1: str, app2: str) -> Dict[str, Any]:
        """Tile two apps side by side using actual screen resolution."""
        screen = self.get_screen_size()
        w = screen["width"]
        h = screen["height"]
        half_w = w // 2
        menu_bar = 25

        # First activate both apps so their windows exist
        self._run_osascript(f'tell application "{app1}" to activate')
        time.sleep(0.5)
        self._run_osascript(f'tell application "{app2}" to activate')
        time.sleep(0.5)

        script = f'''
tell application "System Events"
    tell process "{app1}"
        set position of front window to {{0, {menu_bar}}}
        set size of front window to {{{half_w}, {h - menu_bar}}}
    end tell
    tell process "{app2}"
        set position of front window to {{{half_w}, {menu_bar}}}
        set size of front window to {{{half_w}, {h - menu_bar}}}
    end tell
end tell
'''
        return self._run_osascript_result(script)

    def activate_app(self, app_name: str) -> Dict[str, Any]:
        """Open/activate an app."""
        return self._run_osascript_result(f'tell application "{app_name}" to activate')

    def minimize_app(self, app_name: str) -> Dict[str, Any]:
        """Minimize the front window of an app."""
        return self._run_osascript_result(
            f'tell application "System Events" to tell process "{app_name}" to set miniaturized of front window to true'
        )

    def fullscreen_app(self, app_name: str) -> Dict[str, Any]:
        """Toggle fullscreen on an app's front window."""
        return self._run_osascript_result(
            f'tell application "System Events" to tell process "{app_name}" to set value of attribute "AXFullScreen" of front window to true'
        )

    # ═══════════════════════ SAFARI / WEB ═══════════════════════

    def open_url_in_safari(self, url: str) -> Dict[str, Any]:
        """Open a URL in Safari."""
        return self._run_osascript_result(
            f'tell application "Safari"\n  activate\n  open location "{url}"\nend tell'
        )

    def safari_type_in_field(self, field_name: str, value: str) -> Dict[str, Any]:
        """Set a value in a web form field by name/id using JavaScript."""
        escaped_val = value.replace('"', '\\"').replace("'", "\\'")
        script = f'''
tell application "Safari"
    do JavaScript "
        var el = document.querySelector('[name=\\"{field_name}\\"]') || document.querySelector('#{field_name}') || document.querySelector('[id=\\"{field_name}\\"]');
        if (el) {{ el.value = '{escaped_val}'; el.dispatchEvent(new Event('input', {{bubbles:true}})); 'OK'; }}
        else {{ 'NOT_FOUND'; }}
    " in front document
end tell
'''
        return self._run_osascript_result(script)

    def safari_click_button(self, button_text: str) -> Dict[str, Any]:
        """Click a button on the current Safari page by its text or type=submit."""
        script = f'''
tell application "Safari"
    do JavaScript "
        var btns = document.querySelectorAll('button, input[type=submit], a');
        var found = false;
        btns.forEach(function(b) {{
            if (b.textContent.trim().toLowerCase().includes('{button_text.lower()}') || 
                (b.value && b.value.toLowerCase().includes('{button_text.lower()}'))) {{
                b.click(); found = true;
            }}
        }});
        found ? 'CLICKED' : 'NOT_FOUND';
    " in front document
end tell
'''
        return self._run_osascript_result(script)

    def safari_get_page_text(self) -> str:
        """Get visible text content of the current Safari page."""
        return self._run_osascript(
            'tell application "Safari" to do JavaScript "document.body.innerText.substring(0, 1000)" in front document'
        )

    def safari_get_url(self) -> str:
        """Get the current URL in Safari."""
        return self._run_osascript(
            'tell application "Safari" to return URL of front document'
        )

    def safari_wait_for_load(self, timeout: int = 10) -> bool:
        """Wait for the Safari page to finish loading."""
        for _ in range(timeout * 2):
            state = self._run_osascript(
                'tell application "Safari" to do JavaScript "document.readyState" in front document'
            )
            if state == "complete":
                return True
            time.sleep(0.5)
        return False

    # ═══════════════════════ KEYCHAIN ═══════════════════════

    def keychain_get_password(self, service: str) -> Dict[str, Any]:
        """Retrieve a password from macOS Keychain by service name."""
        try:
            # Try internet passwords first (websites)
            result = subprocess.run(
                ["security", "find-internet-password", "-s", service, "-w"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return {"success": True, "password": result.stdout.strip()}

            # Try generic passwords
            result = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-w"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return {"success": True, "password": result.stdout.strip()}

            return {"success": False, "error": f"No password found for '{service}' in Keychain"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def keychain_get_account(self, service: str) -> Dict[str, Any]:
        """Get the account name (username) for a service from Keychain."""
        try:
            result = subprocess.run(
                ["security", "find-internet-password", "-s", service],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if '"acct"' in line:
                        # Extract value between quotes
                        parts = line.split('"')
                        if len(parts) >= 4:
                            return {"success": True, "account": parts[3]}

            return {"success": False, "error": f"No account found for '{service}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def auto_login_safari(self, service: str) -> Dict[str, Any]:
        """
        Attempt to auto-fill login on the current Safari page using Keychain credentials.
        Tries common field names: email, username, login, user, password, passwd, pass.
        """
        # Get credentials
        account = self.keychain_get_account(service)
        password = self.keychain_get_password(service)

        if not account.get("success") or not password.get("success"):
            return {"success": False, "error": f"Could not retrieve credentials for '{service}' from Keychain. Save them in Keychain first."}

        username = account["account"]
        pwd = password["password"]

        # Try common username field names
        user_fields = ["email", "username", "login", "user", "Email", "Username", "signin-email"]
        for field in user_fields:
            r = self.safari_type_in_field(field, username)
            if "OK" in r.get("message", ""):
                break

        time.sleep(0.3)

        # Try common password field names
        pass_fields = ["password", "passwd", "pass", "Password", "signin-password"]
        for field in pass_fields:
            r = self.safari_type_in_field(field, pwd)
            if "OK" in r.get("message", ""):
                break

        time.sleep(0.3)

        # Try to click submit
        submit_texts = ["log in", "login", "sign in", "signin", "submit", "continue"]
        for text in submit_texts:
            r = self.safari_click_button(text)
            if "CLICKED" in r.get("message", ""):
                return {"success": True, "message": f"Auto-login attempted for {service} as {username}"}

        return {"success": True, "message": f"Filled credentials for {username}. Submit button not auto-detected — you may need to click it."}

    # ═══════════════════════ EMAIL ═══════════════════════

    def compose_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Compose an email in Mail.app."""
        escaped_body = body.replace('"', '\\"').replace('\n', '\\n')
        script = f'''
tell application "Mail"
    activate
    set newMsg to make new outgoing message with properties {{subject:"{subject}", content:"{escaped_body}", visible:true}}
    tell newMsg
        make new to recipient at end of to recipients with properties {{address:"{to}"}}
    end tell
end tell
'''
        return self._run_osascript_result(script)

    # ═══════════════════════ CALENDAR ═══════════════════════

    def add_calendar_event(self, title: str, date: str, time_str: str = "09:00") -> Dict[str, Any]:
        """Add a calendar event."""
        script = f'''
tell application "Calendar"
    activate
    tell calendar "Home"
        set startDate to date "{date} {time_str}"
        set endDate to startDate + 3600
        make new event at end with properties {{summary:"{title}", start date:startDate, end date:endDate}}
    end tell
end tell
'''
        return self._run_osascript_result(script)
    # ═══════════════════════ GITHUB / GIT ═══════════════════════

    def git_status(self, path: str = ".") -> Dict[str, Any]:
        """Get git status for a directory."""
        try:
            r = subprocess.run(["git", "-C", path, "status", "-s"], capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                return {"success": False, "error": "Not a git repository"}
            return {"success": True, "message": r.stdout.strip() or "Clean"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_push(self, path: str = ".", message: str = "Updates from Teni") -> Dict[str, Any]:
        """Commit all changes and push to origin."""
        try:
            subprocess.run(["git", "-C", path, "add", "."], check=True)
            subprocess.run(["git", "-C", path, "commit", "-m", message], capture_output=True)
            r = subprocess.run(["git", "-C", path, "push"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return {"success": True, "message": "Changes committed and pushed to GitHub."}
            return {"success": False, "error": r.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def github_list_issues(self, repo: str = "") -> Dict[str, Any]:
        """List open issues for a repository."""
        try:
            cmd = ["gh", "issue", "list", "--limit", "5"]
            if repo: cmd.extend(["-R", repo])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return {"success": True, "message": r.stdout.strip() or "No open issues found."}
            return {"success": False, "error": r.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def github_user_info(self) -> Dict[str, Any]:
        """Get information about the logged-in GitHub user."""
        try:
            r = subprocess.run(["gh", "api", "user", "--jq", ".login + ' (' + .name + ')'"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return {"success": True, "message": f"Connected to GitHub as {r.stdout.strip()}"}
            return {"success": False, "error": "Not logged in to GitHub CLI"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════ HELPERS ═══════════════════════

    def _run_osascript(self, script: str) -> str:
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    def _run_osascript_result(self, script: str) -> Dict[str, Any]:
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                return {"success": True, "message": r.stdout.strip() or "Done"}
            return {"success": False, "error": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

