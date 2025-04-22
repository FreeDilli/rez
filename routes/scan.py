from flask import Blueprint, render_template, request
from Utils.logging_config import setup_logging
from Utils.scan_logic import process_scan
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan', methods=['GET', 'POST'], strict_slashes=False)
def scan():
    logger.debug(f"Accessing /scan route with method: {request.method}")
    message = None
    if request.method == 'POST':
        raw_input = request.form['mdoc'].strip()
        logger.debug(f"Received scan input: {raw_input}")
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