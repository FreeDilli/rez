import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Get the directory of the current module (utils)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, '..', 'logs')    
    
    # Create logs directory inside rezscan_app
    os.makedirs(log_dir, exist_ok=True)
    
    # Formatter for all logs
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    
    # Handler for INFO and above (app.log) with rotation
    info_handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=10485760, backupCount=2)
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    
    # Handler for DEBUG and above (debug.log) with rotation
    debug_handler = RotatingFileHandler(os.path.join(log_dir, 'debug.log'), maxBytes=10485760, backupCount=2)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    
    # Console handler for all logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Capture all levels
        handlers=[info_handler, debug_handler, console_handler]
    )