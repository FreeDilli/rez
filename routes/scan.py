from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from utils.logging_config import setup_logging
from utils.scan_logic import process_scan
from models.database import get_db
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def scan():
    logger.debug(f"Accessing /scan route with method: {request.method}")
    message = None

    if request.method == 'POST':
        raw_input = request.form.get('mdoc', '').strip()
        logger.debug(f"Received scan input: {raw_input}")

        if not raw_input:
            logger.warning("No MDOC provided in scan form.")
            message = "No barcode scanned."
            return render_template('scan.html', message=message)

        if '-' not in raw_input:
            logger.warning("Invalid scan format. Expected format: PREFIX-MDOC")
            message = "Invalid scan format. Expected format: PREFIX-MDOC"
            return render_template('scan.html', message=message)

        prefix, mdoc = raw_input.split('-', 1)
        logger.debug(f"Parsed prefix: {prefix}, mdoc: {mdoc}")

        try:
            message = process_scan(mdoc.strip(), prefix.strip().upper())
            logger.info(f"Successfully processed scan for mdoc: {mdoc}")
        except Exception as e:
            logger.error(f"Error processing scan for mdoc {mdoc}: {str(e)}")
            message = f"Error processing scan: {str(e)}"

    return render_template('scan.html', message=message)


@scan_bp.route('/_last_scan_partial')
@login_required
def last_scan_partial():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT s.mdoc, s.direction, s.timestamp, r.name, l.name as location
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
                LEFT JOIN locations l ON s.location = l.prefix
                ORDER BY s.timestamp DESC
                LIMIT 1
            """)
            scan = c.fetchone()
    except Exception as e:
        logger.error(f"Error fetching last scan: {e}")
        scan = None

    return render_template('partials/_last_scan_partial.html', last_scan=scan)
