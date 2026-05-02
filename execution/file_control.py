import os
import shutil
import subprocess
from typing import Dict, Any

class FileControl:
    @staticmethod
    def create_folder(path: str, name: str = None) -> Dict[str, Any]:
        try:
            expanded_path = os.path.expanduser(path)
            
            if name:
                # Create folder with name in the specified path
                folder_path = os.path.join(expanded_path, name)
            else:
                # Use the path directly as the folder name
                folder_path = expanded_path
            
            os.makedirs(folder_path, exist_ok=True)
            return {"success": True, "message": f"Created folder: {folder_path}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to create folder: {str(e)}"}
    
    @staticmethod
    def rename_file(old_path: str, new_name: str) -> Dict[str, Any]:
        try:
            expanded_old_path = os.path.expanduser(old_path)
            if not os.path.exists(expanded_old_path):
                return {"success": False, "error": f"File does not exist: {expanded_old_path}"}
            
            directory = os.path.dirname(expanded_old_path)
            new_path = os.path.join(directory, new_name)
            
            os.rename(expanded_old_path, new_path)
            return {"success": True, "message": f"Renamed to: {new_path}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to rename file: {str(e)}"}
    
    @staticmethod
    def move_file(source_path: str, target_path: str) -> Dict[str, Any]:
        try:
            expanded_source = os.path.expanduser(source_path)
            expanded_target = os.path.expanduser(target_path)
            
            if not os.path.exists(expanded_source):
                return {"success": False, "error": f"Source does not exist: {expanded_source}"}
            
            shutil.move(expanded_source, expanded_target)
            return {"success": True, "message": f"Moved to: {expanded_target}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to move file: {str(e)}"}
    
    @staticmethod
    def delete_file(path: str) -> Dict[str, Any]:
        try:
            expanded_path = os.path.expanduser(path)
            if not os.path.exists(expanded_path):
                return {"success": False, "error": f"File does not exist: {expanded_path}"}
            
            result = subprocess.run(["trash", expanded_path], capture_output=True, text=True)
            if result.returncode == 0:
                return {"success": True, "message": f"Moved to trash: {expanded_path}"}
            else:
                return {"success": False, "error": f"Failed to move to trash: {result.stderr}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete file: {str(e)}"}
    
    @staticmethod
    def list_files(path: str) -> Dict[str, Any]:
        try:
            expanded_path = os.path.expanduser(path)
            if not os.path.exists(expanded_path):
                return {"success": False, "error": f"Path does not exist: {expanded_path}"}
            
            if os.path.isfile(expanded_path):
                return {"success": True, "files": [os.path.basename(expanded_path)]}
            
            items = []
            for item in os.listdir(expanded_path):
                item_path = os.path.join(expanded_path, item)
                if os.path.isdir(item_path):
                    items.append(f"{item}/")
                else:
                    items.append(item)
            
            return {"success": True, "files": sorted(items)}
        except Exception as e:
            return {"success": False, "error": f"Failed to list files: {str(e)}"}
