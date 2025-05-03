from flask import Blueprint, render_template
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required

scheduling_bp = Blueprint('scheduling', __name__)

@scheduling_bp.route('/schedule')
@login_required
def dashboard():
    return render_template('schedule/scheduling_dashboard.html')
