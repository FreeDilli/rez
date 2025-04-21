from flask import Blueprint, redirect, url_for, flash
from config import Config
import sqlite3

residents_delete_all_bp = Blueprint('residents_delete_all', __name__)

@residents_delete_all_bp.route('/admin/residents/delete_all', methods=['POST'], strict_slashes=False)
def delete_all_residents():
    with sqlite3.connect(Config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM residents")
        conn.commit()
    flash("All residents deleted successfully.", "success")
    return redirect(url_for('residents.manage_residents'))