from flask import Blueprint, render_template, request
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import login_required
from datetime import datetime, timedelta
from collections import defaultdict

printer_bp = Blueprint('schedule_printer', __name__, url_prefix='/admin/schedules/print')

@printer_bp.route('/', methods=['GET'])
@login_required
def print_schedule():
    selected_date = request.args.get('week', datetime.today().strftime('%Y-%m-%d'))
    try:
        start_of_week = datetime.strptime(selected_date, '%Y-%m-%d')
        week_days = [(start_of_week + timedelta(days=i)).strftime('%A') for i in range(7)]
        time_blocks = ['Morning', 'Afternoon', 'Evening']
        current_week_type = 'A' if start_of_week.isocalendar()[1] % 2 == 1 else 'B'

        schedule = {day: {block: [] for block in time_blocks} for day in week_days}

        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT r.name, r.mdoc, sb.day_of_week, sb.start_time, sb.location, sg.name AS group_name
                FROM resident_schedules rs
                JOIN residents r ON rs.mdoc = r.mdoc
                JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                JOIN schedule_groups sg ON sg.id = sb.group_id
                WHERE sb.week_type IN (?, 'both')
            ''', (current_week_type,))

            rows = c.fetchall()
            for name, mdoc, day, start_time, location, group_name in rows:
                try:
                    hour = int(start_time.split(':')[0])
                    if hour < 12:
                        block = 'Morning'
                    elif hour < 17:
                        block = 'Afternoon'
                    else:
                        block = 'Evening'

                    if day in schedule and block in schedule[day]:
                        schedule[day][block].append({
                            'name': name,
                            'mdoc': mdoc,
                            'location': location,
                            'group': group_name
                        })
                except Exception:
                    continue

        return render_template('schedule_printer.html',
                               selected_date=selected_date,
                               week_days=week_days,
                               time_blocks=time_blocks,
                               schedule=schedule)
    except Exception as e:
        return render_template('schedule_printer.html', selected_date=selected_date, week_days=[], time_blocks=[], schedule={})
