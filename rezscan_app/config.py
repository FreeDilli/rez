import os

# Base directory of the Flask app
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for sessions
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

    # Path to the SQLite database (inside /data directory)
    DB_PATH = os.getenv('DB_PATH', os.path.join(base_dir, 'data', 'rezscan.db'))

    # Upload directory for logo/icons/images
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(base_dir, 'static', 'uploads'))

    # Logging configuration
    LOG_DIR = os.getenv('LOG_DIR', os.path.join(base_dir, 'logs'))
    APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')
    DEBUG_LOG_FILE = os.getenv('DEBUG_LOG_FILE', 'debug.log')
    ERROR_LOG_FILE = os.getenv('ERROR_LOG_FILE', 'error.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB default
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 7))  # 7 backups default
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')  # Default to DEBUG

    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Timezone for local time
    TIMEZONE = 'America/New_York'