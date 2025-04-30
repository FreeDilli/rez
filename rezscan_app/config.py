import os
import secrets
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Base directory of the Flask app (rezscan_app/)
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration for the Flask application."""
    # --- Security ---
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)  # Secure random key if not set
    SESSION_COOKIE_SECURE = bool(int(os.getenv('SESSION_COOKIE_SECURE', 1)))  # Enforce HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')  # CSRF protection

    # --- Database ---
    DB_PATH = os.getenv('DB_PATH', os.path.join(base_dir, 'data', 'rezscan.db'))
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # Ensure DB directory exists

    # --- File Uploads ---
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(base_dir, 'static', 'uploads'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure upload directory exists
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'csv').split(','))

    # --- Logging ---
    LOG_DIR = os.getenv('LOG_DIR', os.path.join(base_dir, 'logs'))
    os.makedirs(LOG_DIR, exist_ok=True)  # Ensure log directory exists
    APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')
    DEBUG_LOG_FILE = os.getenv('DEBUG_LOG_FILE', 'debug.log')
    ERROR_LOG_FILE = os.getenv('ERROR_LOG_FILE', 'error.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 3))   # 7 backup files
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

    # --- Localization ---
    TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')

    # --- Feature Toggles ---
    ENABLE_FEATURE_X = bool(int(os.getenv('ENABLE_FEATURE_X', 0)))

class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

class ProductionConfig(Config):
    """Configuration for production environment."""
    DEBUG = False
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SESSION_COOKIE_SECURE = True  # Enforce HTTPS in production

class TestingConfig(Config):
    """Configuration for testing environment."""
    TESTING = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'CRITICAL')
    DB_PATH = os.getenv('DB_PATH', os.path.join(base_dir, 'data', 'test.db'))