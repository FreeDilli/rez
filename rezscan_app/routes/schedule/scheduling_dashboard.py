from flask import Blueprint, render_template
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required

scheduling_bp = Blueprint('scheduling', __name__)

@scheduling_bp.route('/schedule', strict_slashes=False)
@login_required
@role_required('admin', 'scheduling')
def dashboard():
    return render_template('common/scheduling_dashboard.html')
