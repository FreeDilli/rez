from werkzeug.utils import secure_filename
import os
from rezscan_app.config import Config

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def save_uploaded_file(file, upload_folder=Config.UPLOAD_FOLDER):
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return os.path.join('static', 'uploads', filename).replace("\\", "/")
    return ""