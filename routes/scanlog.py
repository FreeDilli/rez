from flask import Blueprint, render_template
from models.database import get_db
from routes.auth import login_required
from utils.logging_config import setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

scanlog_bp = Blueprint('scanlog', __name__)

@scanlog_bp.route('/admin/scanlog', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def scanlog():
    logger.debug("Accessing /admin/scanlog route")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM scans_with_residents ORDER BY timestamp DESC')
            data = c.fetchall()
            logger.debug(f"Fetched {len(data)} scan records")
            
            c.execute('SELECT DISTINCT status FROM scans_with_residents ORDER BY status')
            status_options = [row[0] for row in c.fetchall() if row[0]]
            logger.debug(f"Fetched {len(status_options)} status options")
            
            c.execute('SELECT DISTINCT location FROM scans_with_residents ORDER BY location')
            location_options = [row[0] for row in c.fetchall() if row[0]]
            logger.debug(f"Fetched {len(location_options)} location options")
            
            logger.info("Successfully retrieved scanlog data")
            return render_template('scanlog.html', scans=data, status_options=status_options, location_options=location_options)
    except Exception as e:
        logger.error(f"Database error in scanlog: {str(e)}")
        return render_template('error.html', message=f"Database error: {str(e)}"), 500