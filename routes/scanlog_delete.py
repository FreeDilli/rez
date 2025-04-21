from flask import Blueprint, redirect, url_for
from models.database import get_db

scanlog_delete_bp = Blueprint('scanlog_delete', __name__)

@scanlog_delete_bp.route('/admin/scanlog/delete', methods=['POST'])
def delete_scanlog():
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM scans")
    db.commit()
    return redirect(url_for('scanlog.scanlog'))