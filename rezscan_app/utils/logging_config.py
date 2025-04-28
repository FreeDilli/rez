import logging
import os
import sys
import yaml
import logging.config
from concurrent_log_handler import ConcurrentRotatingFileHandler
from rezscan_app.config import Config

class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.INFO

def setup_logging():
    logger = logging.getLogger('rezscan_app')
    if logger.handlers:
        return

    try:
        os.makedirs(Config.LOG_DIR, exist_ok=True)
    except PermissionError as e:
        print(f"Failed to create log directory {Config.LOG_DIR}: {e}. Falling back to console logging.", file=sys.stderr)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s')
        )
        logger.handlers = [console_handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        return

    logging_yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.yaml')
    try:
        with open(logging_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['handlers']['info_file']['filename'] = os.path.join(Config.LOG_DIR, Config.APP_LOG_FILE)
        config['handlers']['info_file']['backupCount'] = Config.LOG_BACKUP_COUNT
        config['handlers']['debug_file']['filename'] = os.path.join(Config.LOG_DIR, Config.DEBUG_LOG_FILE)
        config['handlers']['debug_file']['maxBytes'] = Config.LOG_MAX_BYTES
        config['handlers']['debug_file']['backupCount'] = Config.LOG_BACKUP_COUNT
        config['handlers']['debug_file']['level'] = 'DEBUG'  # Ensure debug.log always captures DEBUG
        config['handlers']['error_file']['filename'] = os.path.join(Config.LOG_DIR, Config.ERROR_LOG_FILE)
        config['handlers']['error_file']['maxBytes'] = Config.LOG_MAX_BYTES
        config['handlers']['error_file']['backupCount'] = Config.LOG_BACKUP_COUNT
        
        config['filters'] = {
            'info_filter': {
                '()': 'rezscan_app.utils.logging_config.InfoFilter'
            }
        }
        config['handlers']['info_file']['filters'] = ['info_filter']
        
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG)
        config['loggers']['rezscan_app']['level'] = log_level
        
        logging.config.dictConfig(config)
    except Exception as e:
        print(f"Failed to load logging configuration: {e}. Falling back to console logging.", file=sys.stderr)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s')
        )
        logger.handlers = [console_handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False