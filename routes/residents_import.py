from flask import Blueprint, render_template, request
from models.database import get_db
import csv
import io

residents_import_bp = Blueprint('residents_import', __name__)

@residents_import_bp.route('/admin/residents/import', methods=['GET', 'POST'], strict_slashes=False)
def import_residents():
    messages = []
    import_count = 0
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            messages.append("Invalid or missing CSV file.")
        else: 
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
    return render_template('import_residents.html', messages=messages, import_count=import_count)