import os

# Base directory of the Flask app
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for sessions
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

    # Path to the SQLite database (inside /data directory)
    DB_PATH = os.getenv('DB_PATH', os.path.join(base_dir, '..', 'rezscan.db'))

    # Upload directory for logo/icons/images
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(base_dir, 'static', 'uploads'))

