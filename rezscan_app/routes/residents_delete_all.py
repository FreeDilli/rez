from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user  # Import from flask_login
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required
import logging

residents_delete_all_bp = Blueprint('residents_delete_all', __name__)

@residents_delete_all_bp.route('/admin/residents/delete_all', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_all_residents():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM residents")
            deleted_rows = c.rowcount
            # Get username safely
            username = current_user.username if current_user.is_authenticated and hasattr(current_user, 'username') else 'unknown_admin'
            c.execute(
                "INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)",
                (username, "DELETE_ALL_RESIDENTS", "residents", f"Deleted {deleted_rows} resident(s)")
            )
            conn.commit()
            logging.info(f"User {username} deleted {deleted_rows} resident(s) from residents table")
            logging.debug(f"Details: DELETE FROM residents executed, affected {deleted_rows} rows")
            if deleted_rows == 0:
                flash("No residents found to delete.", "info")
            else:
                flash(f"Successfully deleted {deleted_rows} resident(s).", "success")
    except Exception as e:
        logging.error(f"Error deleting all residents: {str(e)}")
        flash(f"Error deleting residents: {str(e)}", "error")
    return redirect(url_for('residents.residents'))