from flask import Blueprint, redirect, url_for, flash
from models.database import get_db
from routes.auth import login_required, role_required

scanlog_delete_bp = Blueprint('scanlog_delete', __name__)

@scanlog_delete_bp.route('/admin/scanlog/delete', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_scanlog():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM scans")
        conn.commit()
    flash("All scan logs deleted successfully.", "success")
    return redirect(url_for('scanlog.scanlog'))