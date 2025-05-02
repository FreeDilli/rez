from flask import Blueprint, render_template, request, flash
from rezscan_app.models.database import get_db
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
from datetime import datetime

resident_schedule_bp = Blueprint('resident_schedule', __name__)

@resident_schedule_bp.route('/schedule/resident-schedule', methods=['GET'])
@login_required
def lookup():
    mdoc = request.args.get('mdoc', '').strip()
    selected_date = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
    found_name = None
    entries = []

    if mdoc:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            current_week_type = 'A' if date_obj.isocalendar()[1] % 2 == 1 else 'B'

            with get_db() as db:
                c = db.cursor()
                c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
                res = c.fetchone()
                if res:
                    found_name = res[0]
                    c.execute('''
                        SELECT sb.day_of_week, sb.start_time, sb.end_time, sb.location, sb.week_type, sg.name
                        FROM resident_schedules rs
                        JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                        JOIN schedule_groups sg ON sg.id = sb.group_id
                        WHERE rs.mdoc = ? AND sb.day_of_week = ?
                    ''', (mdoc, day_name))

                    rows = c.fetchall()
                    for row in rows:
                        week_type = row[4]
                        if week_type in ("both", current_week_type):
                            hour = int(row[1].split(":")[0])
                            if hour < 12:
                                block = 'Morning'
                            elif hour < 17:
                                block = 'Afternoon'
                            else:
                                block = 'Evening'

                            entries.append({
                                'block': block,
                                'location': row[3],
                                'group': row[5]
                            })
                else:
                    flash("No resident found with that MDOC.", "warning")

        except Exception as e:
            flash("Failed to look up schedule.", "danger")

    return render_template('resident_schedule_lookup.html',
                           schedule_entries=entries,
                           found_name=found_name,
                           selected_date=selected_date)
