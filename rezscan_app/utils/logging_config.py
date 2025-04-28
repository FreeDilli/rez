import logging
import os
from logging import Filter
from logging.handlers import TimedRotatingFileHandler
from concurrent_log_handler import ConcurrentRotatingFileHandler
import sys

class InfoFilter(Filter):
    def filter(self, record):
        return record.levelno >= logging.INFO

def setup_logging(
    log_dir: str = None,
    app_log_file: str = 'app.log',
    debug_log_file: str = 'debug.log',
    error_log_file: str = 'error.log',
    max_bytes: int = 10485760,
    backup_count: int = 7
):
    # Use a custom logger instead of root
    logger = logging.getLogger('rezscan_app')
    if logger.handlers:  # Avoid duplicate setup
        return

    # Set default log directory
    if log_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(base_dir, '..', 'logs')
    # Create log directory with error handling
    try:
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError as e:
        print(f"Failed to create log directory {log_dir}: {e}. Falling back to console logging.", file=sys.stderr)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s')
        )
        logger.handlers = [console_handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        return

    # Enhanced formatter with module, function, and line number
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s'
    )

    # Info handler (INFO and above, daily rotation)
    info_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, app_log_file),
        when='midnight',
        interval=1,
        backupCount=backup_count
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    info_handler.addFilter(InfoFilter())

    # Debug handler (DEBUG and above, size-based rotation, thread/process-safe)
    debug_handler = ConcurrentRotatingFileHandler(
        os.path.join(log_dir, debug_log_file),
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)

    # Error handler (ERROR and above, size-based rotation, thread/process-safe)
    error_handler = ConcurrentRotatingFileHandler(
        os.path.join(log_dir, error_log_file),
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Configure logger
    logger.setLevel(logging.DEBUG)
    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    logger.propagate = False