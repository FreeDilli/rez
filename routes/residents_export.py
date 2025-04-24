from flask import Blueprint, send_file
from models.database import get_db
import csv
import io
from routes.auth import login_required, role_required

residents_export_bp = Blueprint('residents_export', __name__)

@residents_export_bp.route('/admin/residents/export')
@login_required
@role_required('admin')
def export_residents():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'mdoc', 'unit', 'Housing Unit', 'Level', 'Photo'])
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents ORDER BY name")
    for row in c.fetchall():
        writer.writerow(row)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='residents.csv')