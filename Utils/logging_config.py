import logging
import os

def setup_logging():
    os.makedirs('./logs', exist_ok=True)
    
    # Formatter for all logs
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    
    # Handler for INFO and above (app.log)
    info_handler = logging.FileHandler('./logs/app.log')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    
    # Handler for DEBUG and above (debug.log)
    debug_handler = logging.FileHandler('./logs/debug.log')
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