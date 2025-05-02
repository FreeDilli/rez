from flask import Blueprint, render_template, request
from rezscan_app.models.database import get_db
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
import datetime

movement_board_bp = Blueprint('movement_board', __name__)

@movement_board_bp.route('/schedule/movement-board', methods=['GET'])
@login_required
@role_required('admin', 'scheduling')
def view_movement_schedule():
    selected_date = request.args.get('date') or datetime.date.today().strftime('%Y-%m-%d')
    selected_category = request.args.get('category', '').strip()
    selected_location = request.args.get('location', '').strip()
    selected_week = request.args.get('week', '') or 'current'

    db = get_db()
    c = db.cursor()

    # Fetch available filter options
    c.execute('SELECT DISTINCT category FROM schedule_groups ORDER BY category')
    categories = [row['category'] for row in c.fetchall()]

    c.execute('SELECT DISTINCT location FROM schedule_blocks ORDER BY location')
    locations = [row['location'] for row in c.fetchall()]

    # Fetch all schedule blocks with group info
    c.execute('''
        SELECT sb.day_of_week, sb.start_time, sb.end_time, sb.location, sb.week_type,
               sg.name AS group_name, sg.category, sg.id AS group_id
        FROM schedule_blocks sb
        JOIN schedule_groups sg ON sb.group_id = sg.id
        ORDER BY sb.start_time, sb.location
    ''')
    blocks = c.fetchall()

    # Fetch assigned residents
    c.execute('''
        SELECT rs.group_id, r.name, r.mdoc
        FROM resident_schedules rs
        JOIN residents r ON rs.mdoc = r.mdoc
    ''')
    residents_by_group = {}
    for row in c.fetchall():
        residents_by_group.setdefault(row['group_id'], []).append(row)

    # Determine day of week and current week type (A or B)
    day_of_week = datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A')
    current_week = 'A' if datetime.date.today().isocalendar()[1] % 2 == 0 else 'B'
    filter_week = selected_week if selected_week in ['A', 'B'] else current_week

    # Build filtered data
    schedule_data = []
    for block in blocks:
        if block['day_of_week'] != day_of_week:
            continue
        if block['week_type'] != 'both' and block['week_type'].upper() != filter_week.upper():
            continue
        if selected_category and block['category'] != selected_category:
            continue
        if selected_location and block['location'] != selected_location:
            continue

        schedule_data.append({
            'location': block['location'],
            'time': f"{block['start_time']} - {block['end_time']}",
            'group': block['group_name'],
            'category': block['category'],
            'residents': residents_by_group.get(block['group_id'], [])
        })

    return render_template('movement_board.html',
                           selected_date=selected_date,
                           selected_category=selected_category,
                           selected_location=selected_location,
                           selected_week=filter_week,
                           categories=categories,
                           locations=locations,
                           schedule_data=schedule_data)
