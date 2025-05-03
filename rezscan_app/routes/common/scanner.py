from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from rezscan_app.utils.logging_config import setup_logging
from rezscan_app.utils.scan_logic import process_scan
from rezscan_app.models.database import get_db
import logging
import sqlite3
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.utils.audit_logging import log_audit_action
import re

setup_logging()
logger = logging.getLogger(__name__)

scanner_bp = Blueprint('scanner', __name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

@scanner_bp.route('/scanner', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@limiter.limit("50/hour", key_func=user_key_func)
def scanner():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /scan route with method: {request.method}")
    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"Request referrer: {request.referrer}")

    clear_input = False
    if request.method == 'POST':
        logger.debug(f"User {username} submitted form data: {request.form}")
        logger.debug(f"Raw POST data: {request.data}")

        raw_input = None
        if request.form:
            raw_input = request.form.get('mdoc', '').strip()
        elif request.data:
            try:
                raw_input = request.data.decode('utf-8').strip()
                logger.debug(f"User {username} submitted raw POST data: {raw_input}")
            except Exception as e:
                logger.error(f"Error decoding raw POST data for user {username}: {str(e)}")
                log_audit_action(
                    username=username,
                    action='error',
                    target='scan',
                    details=f"Error decoding POST data: {str(e)}"
                )
                flash("Invalid POST data received.", "danger")
                return render_template('common/scanner.html')

        if not raw_input:
            logger.warning(f"User {username} submitted scan with no MDOC")
            log_audit_action(
                username=username,
                action='scan_failed',
                target='scan',
                details='No MDOC provided'
            )
            flash("No barcode scanned.", "warning")
            return render_template('common/scanner.html')

        if '-' not in raw_input:
            logger.warning(f"User {username} submitted invalid scan format: {raw_input}")
            log_audit_action(
                username=username,
                action='scan_failed',
                target='scan',
                details='Invalid scan format (missing prefix-MDOC separator)'
            )
            flash("Invalid scan format. Expected format: PREFIX-MDOC", "warning")
            return render_template('common/scanner.html')

        prefix, mdoc = raw_input.split('-', 1)
        logger.debug(f"User {username} parsed prefix: {prefix}, mdoc: {mdoc}")

        if not re.match(r'^[a-zA-Z0-9]{1,10}$', prefix):
            logger.warning(f"User {username} submitted invalid prefix format: {prefix}")
            log_audit_action(
                username=username,
                action='scan_failed',
                target='scan',
                details='Invalid prefix format'
            )
            flash("Invalid prefix format. Use alphanumeric characters, max 10 characters.", "warning")
            return render_template('common/scanner.html')

        if not re.match(r'^\d{1,10}$', mdoc):
            logger.warning(f"User {username} submitted invalid MDOC format: {mdoc}")
            log_audit_action(
                username=username,
                action='scan_failed',
                target='scan',
                details='Invalid MDOC format'
            )
            flash("Invalid MDOC format. Use numeric characters, max 10 digits.", "warning")
            return render_template('common/scanner.html')

        try:
            message = process_scan(mdoc.strip(), prefix.strip().upper())
            logger.info(f"User {username} successfully processed scan for MDOC: {mdoc}")
            log_audit_action(
                username=username,
                action='scan',
                target='scan',
                details=f"Processed scan for MDOC: {mdoc}, Prefix: {prefix}"
            )
            flash(message, "success")
            clear_input = True
        except Exception as e:
            logger.error(f"Error processing scan for MDOC {mdoc} by user {username}: {str(e)}")
            log_audit_action(
                username=username,
                action='scan_failed',
                target='scan',
                details=f"Error processing scan for MDOC {mdoc}: {str(e)}"
            )
            flash(f"Error processing scan: {str(e)}", "danger")

    log_audit_action(
        username=username,
        action='view',
        target='scan',
        details='Accessed scanner page'
    )
    return render_template('common/scanner.html', clear_input=clear_input)

@scanner_bp.route('/scanner/_last_scan_partial')
@login_required
def last_scan_partial():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /_last_scan_partial route")
    
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
            logger.debug(f"User {username} fetched last scan: {'found' if scan else 'none'}")
            log_audit_action(
                username=username,
                action='view',
                target='last_scan_partial',
                details=f"Fetched last scan: {'found' if scan else 'none'}"
            )
    except sqlite3.Error as e:
        logger.error(f"Error fetching last scan for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='last_scan_partial',
            details=f"Database error fetching last scan: {str(e)}"
        )
        scan = None

    return render_template('partials/_last_scan_partial.html', last_scan=scan)