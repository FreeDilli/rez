import requests
from flask import Blueprint, flash, redirect, url_for
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import login_required, role_required

coris_bp = Blueprint('coris_import', __name__, url_prefix='/admin/import/coris')

CORIS_API_URL = 'https://coris.example.gov/api/residents'
CORIS_API_KEY = 'your_coris_api_key_here'  # Replace with real value

@coris_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def import_coris_residents():
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
                area = r.get('area')
                housing = r.get('housing_unit')
                level = r.get('level')
                photo = r.get('photo')  # assumed to be URL or base64

                if not mdoc or not name:
                    continue  # skip incomplete records

                c.execute("""
                    INSERT INTO residents (mdoc, name, area, housing_unit, level, photo)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(mdoc) DO UPDATE SET
                        name=excluded.name,
                        area=excluded.area,
                        housing_unit=excluded.housing_unit,
                        level=excluded.level,
                        photo=excluded.photo
                """, (mdoc, name, area, housing, level, photo))
                imported += 1

            db.commit()
            flash(f"✅ Imported or updated {imported} residents from CORIS.", "success")
    except Exception as e:
        flash(f"❌ CORIS import failed: {str(e)}", "danger")

    return redirect(url_for('scheduling.dashboard'))
