"""
Input Sanitizer - Critical security for all user inputs
"""

import re
import os
from typing import Dict, Any, List

class InputSanitizer:
    def __init__(self):
        # Dangerous patterns to block
        self.dangerous_patterns = [
            r'[;&|`$()]',           # Command injection
            r'\.\./',               # Path traversal
            r'rm\s+-rf',            # Dangerous rm
            r'sudo\s+',             # Sudo usage
            r'chmod\s+[0-7]',       # Permission changes
            r'curl.*\|',             # Piping with curl
            r'\$\(.*\)',            # Command substitution
            r'<script',             # Script tags
            r'javascript:',         # JavaScript URLs
            r'data:',                # Data URLs
        ]
    
    def sanitize_applescript_string(self, input_str: str) -> str:
        """Sanitize strings for AppleScript injection."""
        if not input_str:
            return ""
        
        # Escape quotes and backslashes
        sanitized = input_str.replace('\\', '\\\\')  # Escape backslashes first
        sanitized = sanitized.replace('"', '\\"')    # Escape double quotes
        sanitized = sanitized.replace("'", "\\'")    # Escape single quotes
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|;$`()]', '', sanitized)
        
        # Limit length
        return sanitized[:1000]
    
    def sanitize_file_path(self, path: str) -> str:
        """Sanitize file paths to prevent traversal and injection."""
        if not path:
            return ""
        
        # Expand user path first
        expanded = os.path.expanduser(path)
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|;$`()]', '', expanded)
        
        # Prevent path traversal
        sanitized = os.path.normpath(sanitized)
        if '..' in sanitized:
            # Remove any remaining traversal attempts
            parts = sanitized.split('/')
            clean_parts = []
            for part in parts:
                if part != '..':
                    clean_parts.append(part)
            sanitized = '/'.join(clean_parts)
        
        # Ensure path is within safe directories
        safe_prefixes = [
            os.path.expanduser("~"),
            "/tmp",
            "/var/tmp"
        ]
        
        is_safe = any(sanitized.startswith(prefix) for prefix in safe_prefixes)
        if not is_safe:
            # Default to user directory if unsafe
            sanitized = os.path.expanduser("~")
        
        return sanitized
    
    def sanitize_shell_command(self, command: str) -> str:
        """Sanitize shell commands."""
        if not command:
            return ""
        
        # Only allow safe commands
        safe_commands = ['ls', 'pwd', 'open', 'mkdir', 'echo', 'cat', 'find']
        
        # Extract base command
        parts = command.split()
        if not parts:
            return ""
        
        base_command = parts[0]
        if base_command not in safe_commands:
            return ""
        
        # Sanitize arguments
        sanitized_args = []
        for arg in parts[1:]:
            # Remove dangerous characters
            clean_arg = re.sub(r'[<>&|;$`()]', '', arg)
            if clean_arg:
                sanitized_args.append(clean_arg)
        
        return ' '.join([base_command] + sanitized_args)
    
    def sanitize_search_query(self, query: str) -> str:
        """Sanitize search queries."""
        if not query:
            return ""
        
        # Remove dangerous characters but keep most text
        sanitized = re.sub(r'[<>&|$`()]', '', query)
        
        # Limit length
        return sanitized[:500]
    
    def sanitize_url(self, url: str) -> str:
        """Sanitize URLs."""
        if not url:
            return ""
        
        # Block dangerous protocols
        dangerous_protocols = [
            "file://", "javascript:", "data:", "ftp://", "ssh://"
        ]
        
        for protocol in dangerous_protocols:
            if url.startswith(protocol):
                return ""
        
        # Only allow http/https
        if not (url.startswith("http://") or url.startswith("https://")):
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|$`()]', '', url)
        
        return sanitized[:1000]
    
    def sanitize_app_name(self, app_name: str) -> str:
        """Sanitize application names."""
        if not app_name:
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|;$`()]', '', app_name)
        
        # Escape for AppleScript
        sanitized = sanitized.replace('"', '\\"')
        sanitized = sanitized.replace("'", "\\'")
        
        # Limit length
        return sanitized[:100]
    
    def sanitize_date_string(self, date_str: str) -> str:
        """Sanitize date strings."""
        if not date_str:
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|;$`()]', '', date_str)
        
        # Basic date format validation
        date_pattern = r'^\d{4}-\d{2}-\d{2}(\s+\d{1,2}:\d{2})?$'
        if not re.match(date_pattern, sanitized):
            return ""
        
        return sanitized
    
    def sanitize_title_string(self, title: str) -> str:
        """Sanitize title strings (calendar events, reminders, etc.)."""
        if not title:
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>&|$`()]', '', title)
        
        # Escape for AppleScript
        sanitized = sanitized.replace('"', '\\"')
        sanitized = sanitized.replace("'", "\\'")
        
        # Limit length
        return sanitized[:200]
    
    def validate_shell_arguments(self, command: str, args: List[str]) -> List[str]:
        """Validate shell arguments using argument lists (not string interpolation)."""
        safe_args = []
        
        for arg in args:
            # Remove dangerous characters
            clean_arg = re.sub(r'[<>&|;$`()]', '', str(arg))
            
            # Check for path traversal
            if '..' in clean_arg:
                continue
            
            # Check length
            if len(clean_arg) > 1000:
                continue
            
            safe_args.append(clean_arg)
        
        return safe_args
    
    def check_for_injection(self, input_str: str) -> bool:
        """Check if input contains injection patterns."""
        if not input_str:
            return False
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        
        return False
    
    def sanitize_all_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all parameters in a parameter dictionary."""
        sanitized = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                if key in ["path", "target", "source"]:
                    sanitized[key] = self.sanitize_file_path(value)
                elif key == "app":
                    sanitized[key] = self.sanitize_app_name(value)
                elif key == "command":
                    sanitized[key] = self.sanitize_shell_command(value)
                elif key == "query":
                    sanitized[key] = self.sanitize_search_query(value)
                elif key == "url":
                    sanitized[key] = self.sanitize_url(value)
                elif key == "date":
                    sanitized[key] = self.sanitize_date_string(value)
                elif key in ["title", "name", "subject"]:
                    sanitized[key] = self.sanitize_title_string(value)
                else:
                    sanitized[key] = self.sanitize_applescript_string(value)
            else:
                sanitized[key] = value
        
        return sanitized
