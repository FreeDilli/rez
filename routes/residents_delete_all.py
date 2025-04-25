from flask import Blueprint, redirect, url_for, flash
from models.database import get_db
from routes.auth import login_required, role_required

residents_delete_all_bp = Blueprint('residents_delete_all', __name__)

@residents_delete_all_bp.route('/admin/residents/delete_all', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_all_residents():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM residents")
        conn.commit()
    flash("All residents deleted successfully.", "success")
    return redirect(url_for('residents.manage_residents'))