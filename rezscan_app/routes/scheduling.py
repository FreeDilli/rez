from flask import Blueprint, render_template
from rezscan_app.routes.auth import login_required

scheduling_bp = Blueprint('scheduling', __name__, url_prefix='/admin/scheduling')

@scheduling_bp.route('/')
@login_required
def dashboard():
    return render_template('scheduling_dashboard.html')
