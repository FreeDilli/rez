from flask import Blueprint, render_template, request
from models.database import get_db
import csv
import io
from werkzeug.utils import secure_filename

residents_import_bp = Blueprint('residents_import', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'csv'}  # Restrict to CSV files only
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@residents_import_bp.route('/admin/residents/import', methods=['GET', 'POST'], strict_slashes=False)
def import_residents():
    messages = []
    import_count = 0
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or file.filename == '':
            messages.append("No file selected.")
        elif not allowed_file(file.filename):
            messages.append("Invalid file type. Only CSV files are allowed.")
        else:
            # Sanitize filename (optional, for logging or saving)
            filename = secure_filename(file.filename)
            try:
                stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
                reader = csv.DictReader(stream)
                db = get_db()
                c = db.cursor()
                c.execute("DELETE FROM residents")
                db.commit()
                for row in reader:
                    try:
                        c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                                  (row['name'], row['mdoc'], row['unit'], row['housing_unit'], row['level'], row.get('photo', '')))
                        import_count += 1
                        db.commit()
                        messages.append(f"✔ Imported {row['name']}")
                    except Exception as e:
                        messages.append(f"✘ Error on {row.get('name', 'Unknown')}: {str(e)}")
            except Exception as e:
                messages.append(f"Error reading CSV file: {str(e)}")
    return render_template('import_residents.html', messages=messages, import_count=import_count)