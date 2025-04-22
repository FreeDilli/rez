from flask import Blueprint, render_template, request
from Utils.logging_config import setup_logging
from models.database import get_db
import csv
import io
from werkzeug.utils import secure_filename
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

residents_import_bp = Blueprint('residents_import', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'csv'}  # Restrict to CSV files only
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@residents_import_bp.route('/admin/residents/import', methods=['GET', 'POST'], strict_slashes=False)
def import_residents():
    logger.debug(f"Accessing /admin/residents/import route with method: {request.method}")
    messages = []
    import_count = 0
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or file.filename == '':
            logger.warning("No file selected for resident import")
            messages.append("No file selected.")
        elif not allowed_file(file.filename):
            logger.warning(f"Invalid file type for {file.filename}. Only CSV files are allowed")
            messages.append("Invalid file type. Only CSV files are allowed.")
        else:
            # Sanitize filename
            filename = secure_filename(file.filename)
            logger.debug(f"Processing CSV file: {filename}")
            try:
                stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
                reader = csv.DictReader(stream)
                db = get_db()
                c = db.cursor()
                c.execute("DELETE FROM residents")
                db.commit()
                logger.info("Deleted existing residents from database")
                for row in reader:
                    try:
                        c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                                  (row['name'], row['mdoc'], row['unit'], row['housing_unit'], row['level'], row.get('photo', '')))
                        import_count += 1
                        db.commit()
                        logger.info(f"Imported resident: {row['name']} (MDOC: {row['mdoc']})")
                        messages.append(f"✔ Imported {row['name']}")
                    except Exception as e:
                        logger.error(f"Error importing resident {row.get('name', 'Unknown')} (MDOC: {row.get('mdoc', 'Unknown')}): {str(e)}")
                        messages.append(f"✘ Error on {row.get('name', 'Unknown')}: {str(e)}")
                logger.info(f"Completed import: {import_count} residents imported")
            except Exception as e:
                logger.error(f"Error reading CSV file {filename}: {str(e)}")
                messages.append(f"Error reading CSV file: {str(e)}")
    return render_template('import_residents.html', messages=messages, import_count=import_count)