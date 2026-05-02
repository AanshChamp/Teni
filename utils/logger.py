import logging
import os
from datetime import datetime
from config import Config

class TeniLogger:
    def __init__(self):
        self.logs_dir = Config.LOGS_DIR
        os.makedirs(self.logs_dir, exist_ok=True)
        
        log_file = os.path.join(self.logs_dir, f"teni_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('teni')
    
    def log_router_mode(self, mode: str):
        self.logger.info(f"[ROUTER] → {mode} mode")
    
    def log_normalization(self, original: str, normalized: str):
        self.logger.info(f"[NORMALIZER] → action normalized: {original} → {normalized}")
    
    def log_command(self, user_input: str, intent: dict, execution_result: dict):
        self.logger.info(f"Input: {user_input}")
        self.logger.info(f"Intent: {intent}")
        self.logger.info(f"Result: {execution_result}")
        
        if execution_result.get("success"):
            self.logger.info("Command executed successfully")
        else:
            self.logger.error(f"Command failed: {execution_result.get('error', 'Unknown error')}")
    
    def log_error(self, error: str):
        self.logger.error(error)
    
    def log_info(self, message: str):
        self.logger.info(message)
