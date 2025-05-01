from flask import Blueprint, render_template, request, flash, send_file, redirect, url_for
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required
from datetime import datetime, timedelta
from collections import defaultdict
import io
import csv

calendar_bp = Blueprint('calendar_schedule', __name__, url_prefix='/admin/schedules/calendar')

@calendar_bp.route('/', methods=['GET'])
@login_required
def weekly_calendar():
    try:
        selected_date = request.args.get('week')
        selected_location = request.args.get('location', '')

        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        if selected_date:
            try:
                start_of_week = datetime.strptime(selected_date, '%Y-%m-%d')
            except ValueError:
                flash("Invalid date format.", "warning")

        week_days = [(start_of_week + timedelta(days=i)).strftime('%A') for i in range(7)]
        time_blocks = ['Morning', 'Afternoon', 'Evening']

        schedule = {day: {block: [] for block in time_blocks} for day in week_days}
        locations = set()

        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT r.name, r.mdoc, sb.day_of_week, sb.start_time, sb.end_time, sb.week_type,
                       sb.location, sg.name AS group_name
                FROM resident_schedules rs
                JOIN residents r ON rs.mdoc = r.mdoc
                JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                JOIN schedule_groups sg ON sg.id = sb.group_id
            ''')
            rows = c.fetchall()

            current_week_type = 'A' if (start_of_week.isocalendar()[1] % 2) == 1 else 'B'

            for row in rows:
                name, mdoc, day, start_time, end_time, week_type, location, group_name = row
                if selected_location and selected_location != location:
                    continue
                if week_type and week_type not in ('both', current_week_type):
                    continue

                if day in schedule:
                    hour = int(start_time.split(':')[0])
                    if hour < 12:
                        block = 'Morning'
                    elif hour < 17:
                        block = 'Afternoon'
                    else:
                        block = 'Evening'

                    schedule[day][block].append({
                        'name': name,
                        'mdoc': mdoc,
                        'location': location,
                        'group': group_name
                    })
                    locations.add(location)

        return render_template('calendar_schedule.html',
                               schedule=schedule,
                               week_days=week_days,
                               time_blocks=time_blocks,
                               locations=sorted(locations),
                               selected_date=start_of_week.strftime('%Y-%m-%d'),
                               selected_location=selected_location)
    except Exception as e:
        flash('Error loading calendar view.', 'danger')
        return render_template('calendar_schedule.html', schedule={}, week_days=[], time_blocks=[], locations=[], selected_date='', selected_location='')

@calendar_bp.route('/export', methods=['GET'])
@login_required
def export_csv():
    try:
        selected_date = request.args.get('week')
        selected_location = request.args.get('location', '')

        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        if selected_date:
            start_of_week = datetime.strptime(selected_date, '%Y-%m-%d')
        week_days = [(start_of_week + timedelta(days=i)).strftime('%A') for i in range(7)]

        time_blocks = ['Morning', 'Afternoon', 'Evening']
        current_week_type = 'A' if (start_of_week.isocalendar()[1] % 2) == 1 else 'B'

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Day", "Time Block", "Resident", "MDOC", "Group", "Location"])

        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT r.name, r.mdoc, sb.day_of_week, sb.start_time, sb.end_time, sb.week_type,
                       sb.location, sg.name AS group_name
                FROM resident_schedules rs
                JOIN residents r ON rs.mdoc = r.mdoc
                JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                JOIN schedule_groups sg ON sg.id = sb.group_id
            ''')
            rows = c.fetchall()

            for row in rows:
                name, mdoc, day, start_time, end_time, week_type, location, group_name = row
                if selected_location and selected_location != location:
                    continue
                if week_type and week_type not in ('both', current_week_type):
                    continue

                hour = int(start_time.split(':')[0])
                block = 'Morning' if hour < 12 else 'Afternoon' if hour < 17 else 'Evening'
                writer.writerow([day, block, name, mdoc, group_name, location])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='weekly_schedule_export.csv'
        )

    except Exception as e:
        flash('Failed to export schedule.', 'danger')
        return redirect(url_for('calendar_schedule.weekly_calendar'))