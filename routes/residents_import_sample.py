from flask import Blueprint, send_file
import csv
import io

residents_sample_bp = Blueprint('residents_import_sample', __name__)

@residents_sample_bp.route('/admin/residents/sample', strict_slashes=False)
def sample_csv():
    sample = io.StringIO()
    writer = csv.writer(sample)
    writer.writerow(['name', 'mdoc', 'unit', 'housing_unit', 'level', 'photo'])
    writer.writerow(['John Doe', '1001', 'Unit 1', 'Delta', '1', ''])
    writer.writerow(['Jane Smith', '1002', 'Unit 2', 'Dorm 5', '2', ''])
    sample.seek(0)
    return send_file(io.BytesIO(sample.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='sample_residents.csv')