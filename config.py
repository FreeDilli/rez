import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    DB_PATH = os.getenv('DB_PATH', 'rezscan.db')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')