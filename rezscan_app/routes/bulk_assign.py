from flask import Blueprint, render_template, request, redirect, url_for, flash
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required

bulk_bp = Blueprint('bulk_assign', __name__, url_prefix='/admin/schedules/bulk_assign')

@bulk_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin','scheduling')
def bulk_assign():
    try:
        with get_db() as db:
            c = db.cursor()

            # Fetch schedule groups
            c.execute('SELECT id, name, category FROM schedule_groups ORDER BY category, name')
            groups = c.fetchall()

            # Fetch all residents
            c.execute('SELECT mdoc, name, area, housing_unit, level FROM residents ORDER BY name')
            residents = c.fetchall()

            if request.method == 'POST':
                selected_group = request.form.get('group_id')
                selected_mdocs = request.form.getlist('assign[]')

                if not selected_group or not selected_mdocs:
                    flash("Please select both a group and at least one resident.", "warning")
                    return redirect(url_for('bulk_assign.bulk_assign'))

                # Remove existing assignments for selected residents to prevent duplicates
                for mdoc in selected_mdocs:
                    c.execute("DELETE FROM resident_schedules WHERE mdoc = ? AND group_id = ?", (mdoc, selected_group))
                    c.execute("INSERT INTO resident_schedules (mdoc, group_id) VALUES (?, ?)", (mdoc, selected_group))
                db.commit()

                flash(f"Successfully assigned {len(selected_mdocs)} resident(s) to group.", "success")
                return redirect(url_for('schedules.manage_schedules'))

            return render_template('bulk_assign.html', groups=groups, residents=residents)

    except Exception as e:
        flash("An error occurred while assigning residents.", "danger")
        return redirect(url_for('schedules.manage_schedules'))
