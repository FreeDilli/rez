from flask import Blueprint, render_template, request
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from collections import defaultdict

conflict_bp = Blueprint('conflict_checker', __name__)

@conflict_bp.route('/schedule/conflicts', methods=['GET'])
@login_required
def check_conflicts():
    selected_date = request.args.get('week', datetime.today().strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(selected_date, '%Y-%m-%d')
        week_type = 'A' if start_date.isocalendar()[1] % 2 == 1 else 'B'
        days_of_week = [(start_date + timedelta(days=i)).strftime('%A') for i in range(7)]

        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT r.name, r.mdoc, sb.day_of_week, sb.start_time, sb.location, sg.name
                FROM resident_schedules rs
                JOIN residents r ON rs.mdoc = r.mdoc
                JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                JOIN schedule_groups sg ON sg.id = sb.group_id
                WHERE sb.week_type IN (?, 'both')
            ''', (week_type,))

            schedule_map = defaultdict(lambda: defaultdict(list))  # {mdoc: {day+block: [entries]}}
            entries = c.fetchall()

            for name, mdoc, day, start, location, group_name in entries:
                try:
                    hour = int(start.split(':')[0])
                    if hour < 12:
                        block = 'Morning'
                    elif hour < 17:
                        block = 'Afternoon'
                    else:
                        block = 'Evening'
                    key = f"{day}_{block}"
                    schedule_map[(name, mdoc)][key].append({"group": group_name, "location": location})
                except Exception:
                    continue

            # Identify conflicts (2+ entries in same block)
            conflicts = []
            for (name, mdoc), blocks in schedule_map.items():
                for key, group_list in blocks.items():
                    if len(group_list) > 1:
                        day, block = key.split('_')
                        conflicts.append({
                            'name': name,
                            'mdoc': mdoc,
                            'day': day,
                            'block': block,
                            'groups': group_list
                        })

        return render_template('conflict_checker.html', selected_date=selected_date, conflicts=conflicts)

    except Exception as e:
        return render_template('conflict_checker.html', selected_date=selected_date, conflicts=[])
