from flask import Blueprint, send_file
from models.database import get_db
import csv
import io
from routes.auth import login_required, role_required

scanlog_export_bp = Blueprint('scanlog_export', __name__)

@scanlog_export_bp.route('/admin/scanlog/export')
@login_required
@role_required('admin')
def export_scanlog():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['MDOC', 'Name', 'Date', 'Time', 'Status', 'Location'])
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM scans_with_residents ORDER BY time desc")
    for row in c.fetchall():
        writer.writerow(row)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='scanlog.csv')