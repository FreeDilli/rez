import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Base directory of the Flask app
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # --- Security ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

    SESSION_COOKIE_SECURE = bool(int(os.getenv('SESSION_COOKIE_SECURE', 1)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

    # --- Database ---
    DB_PATH = os.getenv('DB_PATH', os.path.join(base_dir, 'data', 'rezscan.db'))

    # --- File Uploads ---
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(base_dir, 'static', 'uploads'))

    # --- Logging ---
    LOG_DIR = os.getenv('LOG_DIR', os.path.join(base_dir, 'logs'))
    APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')
    DEBUG_LOG_FILE = os.getenv('DEBUG_LOG_FILE', 'debug.log')
    ERROR_LOG_FILE = os.getenv('ERROR_LOG_FILE', 'error.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 7))   # 7 backup files
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

    # --- Localization ---
    TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')

    # --- Feature Toggles (optional future expansion) ---
    ENABLE_FEATURE_X = bool(int(os.getenv('ENABLE_FEATURE_X', 0)))
