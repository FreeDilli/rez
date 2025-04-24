from flask import Blueprint, redirect, url_for, flash
from models.database import get_db
from routes.auth import login_required, role_required

locations_delete_bp = Blueprint('locations_delete', __name__)

@locations_delete_bp.route('/admin/locations/delete/<int:location_id>', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_location(location_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        conn.commit()
    flash("Location deleted successfully.", "success")
    return redirect(url_for('locations.manage_locations'))