from flask import Blueprint, redirect, url_for, flash
from config import Config
import sqlite3
from routes.auth import login_required, role_required

residents_delete_bp = Blueprint('residents_delete', __name__)

@residents_delete_bp.route('/admin/residents/delete/<int:mdoc>', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_resident(mdoc):
    with sqlite3.connect(Config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM residents WHERE id = ?", (mdoc,))
        conn.commit()
        flash("Resident deleted successfully.", "success")
    return redirect(url_for('residents.manage_residents'))