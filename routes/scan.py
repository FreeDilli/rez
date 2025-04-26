from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from utils.logging_config import setup_logging
from utils.scan_logic import process_scan
from models.database import get_db
import logging

setup_logging()
logger = logging.getLogger(__name__)

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def scan():
    logger.debug(f"Accessing /scan route with method: {request.method}")
    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"Request referrer: {request.referrer}")

    clear_input = False
    if request.method == 'POST':
        logger.debug(f"Form data received: {request.form}")
        logger.debug(f"Raw POST data: {request.data}")

        raw_input = None
        if request.form:
            raw_input = request.form.get('mdoc', '').strip()
        elif request.data:
            try:
                raw_input = request.data.decode('utf-8').strip()
                logger.debug(f"Raw POST data received: {raw_input}")
            except Exception as e:
                logger.error(f"Error decoding raw POST data: {e}")
                flash("Invalid POST data received.", "danger")
                return render_template('scan.html')

        if not raw_input:
            logger.warning("No MDOC provided in scan form or POST body.")
            flash("No barcode scanned.", "danger")
            return render_template('scan.html')

        if '-' not in raw_input:
            logger.warning("Invalid scan format. Expected format: PREFIX-MDOC")
            flash("Invalid scan format. Expected format: PREFIX-MDOC", "danger")
            return render_template('scan.html')

        prefix, mdoc = raw_input.split('-', 1)
        logger.debug(f"Parsed prefix: {prefix}, mdoc: {mdoc}")

        try:
            message = process_scan(mdoc.strip(), prefix.strip().upper())
            logger.info(f"Successfully processed scan for mdoc: {mdoc}")
            flash(message, "success")
            clear_input = True
        except Exception as e:
            logger.error(f"Error processing scan for mdoc {mdoc}: {str(e)}")
            flash(f"Error processing scan: {str(e)}", "danger")

    return render_template('scan.html', clear_input=clear_input)

@scan_bp.route('/_last_scan_partial')
@login_required
def last_scan_partial():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT s.mdoc, s.status AS direction, s.date || ' ' || s.time AS timestamp, r.name, l.name AS location
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
                LEFT JOIN locations l ON s.location = l.prefix
                ORDER BY s.date DESC, s.time DESC
                LIMIT 1
            """)
            scan = c.fetchone()
    except Exception as e:
        logger.error(f"Error fetching last scan: {e}")
        scan = None

    return render_template('partials/_last_scan_partial.html', last_scan=scan)