import logging
import requests
from flask import Blueprint, flash, redirect, url_for
from rezscan_app.models.database import get_db
from flask_login import login_required, current_user
from rezscan_app.routes.common.auth import role_required
from rezscan_app.config import Config
from rezscan_app.utils.audit_logging import log_audit_action

coris_bp = Blueprint('coris_import', __name__, url_prefix='/admin/import/coris')
logger = logging.getLogger(__name__)

def get_api_settings():
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute("SELECT value FROM settings WHERE category='api' AND key='coris_api_url'")
            row = c.fetchone()
            url = row[0] if row else Config.CORIS_API_URL
            c.execute("SELECT value FROM settings WHERE category='api' AND key='coris_api_key'")
            row = c.fetchone()
            key = row[0] if row else Config.CORIS_API_KEY
            return url, key
    except Exception as e:
        logger.error(f"Error fetching API settings: {str(e)}")
        return Config.CORIS_API_URL, Config.CORIS_API_KEY

@coris_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def import_coris_residents():
    username = current_user.username
    logger.debug(f"User {username} initiated CORIS import")
    
    CORIS_API_URL, CORIS_API_KEY = get_api_settings()
    headers = {'Authorization': f'Bearer {CORIS_API_KEY}'}
    
    try:
        response = requests.get(CORIS_API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        with get_db() as db:
            c = db.cursor()
            imported = 0

            for r in data:
                mdoc = r.get('mdoc')
                name = r.get('name')
                unit = r.get('area')  # Assuming API uses 'area', mapping to 'unit'
                housing = r.get('housing_unit')
                level = r.get('level')
                photo = r.get('photo')

                if not mdoc or not name:
                    continue

                c.execute("""
                    INSERT INTO residents (mdoc, name, unit, housing_unit, level, photo)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(mdoc) DO UPDATE SET
                        name=excluded.name,
                        unit=excluded.unit,
                        housing_unit=excluded.housing_unit,
                        level=excluded.level,
                        photo=excluded.photo
                """, (mdoc, name, unit, housing, level, photo))
                imported += 1

            db.commit()
            flash(f"✅ Imported or updated {imported} residents from CORIS.", "success")
            log_audit_action(username, 'import_coris', 'residents', f"Imported/updated {imported} residents")
            logger.info(f"User {username} successfully imported {imported} residents from CORIS")
    except Exception as e:
        flash(f"❌ CORIS import failed: {str(e)}", "danger")
        log_audit_action(username, 'import_coris_failed', 'residents', f"Import failed: {str(e)}")
        logger.error(f"User {username} failed to import from CORIS: {str(e)}")

    return redirect(url_for('admin.admin_dashboard'))