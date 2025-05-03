from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from rezscan_app.routes.common.auth import role_required

permissions_bp = Blueprint('permissions', __name__, url_prefix='/admin/permissions')

# Define what routes/pages are visible to each role
ROLE_ACCESS = {
    "viewer": [
        {"name": "Dashboard", "path": "/dashboard"},
        {"name": "Scan Log", "path": "/admin/scanlog"},
    ],
    "officer": [
        {"name": "Dashboard", "path": "/dashboard"},
        {"name": "Scan Residents", "path": "/scan"},
        {"name": "Manage Residents", "path": "/admin/residents"},
    ],
    "scheduling": [
        {"name": "Scheduling Dashboard", "path": "/admin/scheduling"},
        {"name": "Schedule Groups", "path": "/admin/schedules"},
        {"name": "Bulk Assign", "path": "/admin/schedules/bulk_assign"},
        {"name": "Print Schedule", "path": "/admin/schedules/print"},
    ],
    "admin": [
        {"name": "Admin Dashboard", "path": "/admin"},
        {"name": "Users", "path": "/admin/users"},
        {"name": "Audit Log", "path": "/auditlog"},
        {"name": "Settings", "path": "/admin/settings"},
    ]
}

@permissions_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def permission_test():
    selected_role = request.args.get('role', 'viewer')
    access_list = []

    # Combine viewer + lower roles for composite roles
    if selected_role == "officer":
        access_list = ROLE_ACCESS["viewer"] + ROLE_ACCESS["officer"]
    elif selected_role == "scheduling":
        access_list = ROLE_ACCESS["viewer"] + ROLE_ACCESS["scheduling"]
    elif selected_role == "admin":
        access_list = ROLE_ACCESS["viewer"] + ROLE_ACCESS["officer"] + ROLE_ACCESS["scheduling"] + ROLE_ACCESS["admin"]
    else:
        access_list = ROLE_ACCESS.get(selected_role, [])

    return render_template('admin/permission_test.html', selected_role=selected_role, access_list=access_list)
