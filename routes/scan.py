from flask import Blueprint, render_template, request
from Utils.scan_logic import process_scan

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan', methods=['GET', 'POST'], strict_slashes=False)
def scan():
    message = None
    if request.method == 'POST':
        raw_input = request.form['mdoc'].strip()
        if '-' not in raw_input:
            message = "Invalid scan format. Expected format: PREFIX-MDOC"
            return render_template('scan.html', message=message)
        prefix, mdoc = raw_input.split('-', 1)
        try:
            message = process_scan(mdoc.strip(), prefix.strip().upper())
        except Exception as e:
            message = f"Error processing scan: {str(e)}"
    return render_template('scan.html', message=message)