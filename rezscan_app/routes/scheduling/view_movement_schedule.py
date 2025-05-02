from flask import Blueprint, render_template, request
from rezscan_app.models.database import get_db
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
import datetime

movement_board_bp = Blueprint('movement_schedule', __name__)

@movement_board_bp.route('/schedule/movement-schedule', methods=['GET'])
@login_required
@role_required('scheduling')
def view_movement_schedule():
    selected_date = request.args.get('date')
    selected_category = request.args.get('category', '').strip()

    if not selected_date:
        selected_date = datetime.date.today().strftime('%Y-%m-%d')

    db = get_db()
    c = db.cursor()

    # Get all available categories for dropdown
    c.execute('SELECT DISTINCT category FROM schedule_groups ORDER BY category')
    categories = [row['category'] for row in c.fetchall()]

    # Get all unique locations for potential future filtering
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

    # Fetch residents assigned to groups
    c.execute('''
        SELECT rs.group_id, r.name, r.mdoc
        FROM resident_schedules rs
        JOIN residents r ON rs.mdoc = r.mdoc
    ''')
    residents_by_group = {}
    for row in c.fetchall():
        residents_by_group.setdefault(row['group_id'], []).append(row)

    # Determine weekday and week type (A/B)
    day_of_week = datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A')
    current_week = 'A' if datetime.date.today().isocalendar()[1] % 2 == 0 else 'B'

    # Build filtered movement data
    schedule_data = []
    for block in blocks:
        if block['day_of_week'] != day_of_week:
            continue
        if block['week_type'] != 'both' and block['week_type'].lower() != current_week.lower():
            continue
        if selected_category and block['category'] != selected_category:
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
                           categories=categories,
                           locations=locations,
                           schedule_data=schedule_data)
