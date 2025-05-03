from flask import Blueprint, render_template, request, redirect, url_for, flash
from rezscan_app.models.database import get_db
import logging
from rezscan_app.utils.logging_config import setup_logging
from rezscan_app.routes.common.auth import role_required
from rezscan_app.routes.admin.audit_log import log_audit_action
import sqlite3
from datetime import datetime
from flask_login import login_required, current_user


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route('/schedule/schedules')
@login_required
def manage_schedules():
    category_filter = request.args.get('category')
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute('SELECT DISTINCT category FROM schedule_groups ORDER BY category')
            categories = [row['category'] for row in c.fetchall()]

            query = '''
                SELECT sg.id, sg.name, sg.description, sg.category,
                       COUNT(DISTINCT sb.id) AS block_count,
                       COUNT(DISTINCT rs.mdoc) AS resident_count
                FROM schedule_groups sg
                LEFT JOIN schedule_blocks sb ON sg.id = sb.group_id
                LEFT JOIN resident_schedules rs ON sg.id = rs.group_id
                {}
                GROUP BY sg.id
            '''
            params = []
            if category_filter:
                query = query.format('WHERE sg.category = ?')
                params = [category_filter]
            else:
                query = query.format('')
            c.execute(query, params)
            groups = c.fetchall()

            return render_template('schedule/schedules.html', groups=groups, category_filter=category_filter, categories=categories)
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        flash('An error occurred while retrieving schedules.', 'danger')
        return render_template('schedule/schedules.html', groups=[], category_filter=category_filter, categories=[])

@schedules_bp.route('/schedule/create', methods=['GET', 'POST'])
@login_required
def create_schedule():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')

        if not name or not category:
            flash('Name and category are required.', 'warning')
            return redirect(url_for('schedules.create_schedule'))

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO schedule_groups (name, description, category) VALUES (?, ?, ?)",
                    (name, description, category)
                )
                conn.commit()
            flash('Schedule group created successfully.', 'success')
            return redirect(url_for('schedules.manage_schedules'))
        except Exception as e:
            flash(f'Error creating schedule group: {e}', 'danger')
            return redirect(url_for('schedules.create_schedule'))

    return render_template('schedule/schedule_form.html', action='Create', schedule={})

@schedules_bp.route('/schedule/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_schedule(group_id):
    try:
        with get_db() as db:
            c = db.cursor()

            if request.method == 'POST':
                if 'block_editor' in request.form:
                    day_list = request.form.getlist('day[]')
                    location_list = request.form.getlist('location[]')
                    start_list = request.form.getlist('start_time[]')
                    end_list = request.form.getlist('end_time[]')
                    week_list = request.form.getlist('week_type[]')
                    remove_ids = request.form.getlist('remove[]')

                    valid_week_types = {'both', 'A', 'B'}
                    try:
                        for block_id in remove_ids:
                            c.execute('DELETE FROM schedule_blocks WHERE id = ? AND group_id = ?', (block_id, group_id))

                        for i in range(len(day_list)):
                            day = day_list[i].strip()
                            location = location_list[i].strip()
                            start = start_list[i].strip()
                            end = end_list[i].strip()
                            week = week_list[i].strip()

                            if not all([day, location, start, end]):
                                continue
                            if week and week not in valid_week_types:
                                flash(f'Invalid week type: {week}. Skipping block.', 'warning')
                                continue

                            c.execute(
                                '''
                                INSERT INTO schedule_blocks (group_id, day_of_week, location, start_time, end_time, week_type)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ''',
                                (group_id, day, location, start, end, week or 'both')
                            )

                        db.commit()
                        flash('Schedule blocks updated.', 'success')
                        return redirect(url_for('schedules.edit_schedule', group_id=group_id))
                    except sqlite3.Error as e:
                        logger.error(f"Database error updating schedule blocks for group_id {group_id}: {e}")
                        flash('Database error while updating schedule blocks.', 'danger')

                else:
                    name = request.form['name'].strip()
                    description = request.form['description'].strip()
                    category = request.form['category'].strip()

                    if not name or not category:
                        flash('Name and category are required.', 'warning')
                        return redirect(url_for('schedules.edit_schedule', group_id=group_id))

                    c.execute(
                        'UPDATE schedule_groups SET name = ?, description = ?, category = ? WHERE id = ?',
                        (name, description, category, group_id)
                    )
                    if c.rowcount == 0:
                        flash('Schedule group not found.', 'warning')
                        return redirect(url_for('schedules.manage_schedules'))
                    db.commit()
                    flash('Schedule group updated successfully.', 'success')
                    return redirect(url_for('schedules.manage_schedules'))

            # GET request: Display edit form
            c.execute('SELECT * FROM schedule_groups WHERE id = ?', (group_id,))
            schedule = c.fetchone()
            if not schedule:
                flash('Schedule group not found.', 'warning')
                return redirect(url_for('schedules.manage_schedules'))

            c.execute('SELECT * FROM schedule_blocks WHERE group_id = ?', (group_id,))
            blocks = c.fetchall()

            c.execute('SELECT name FROM locations ORDER BY name')
            locations = [row[0] for row in c.fetchall()]

            return render_template('schedule/schedule_form.html', action='Edit', schedule=schedule, blocks=blocks, locations=locations)
    except Exception as e:
        logger.error(f"Error in edit_schedule for group_id {group_id}: {e}")
        flash('An error occurred while accessing the schedule.', 'danger')
        return redirect(url_for('schedules.manage_schedules'))

@schedules_bp.route('/schedule/<int:group_id>/delete')
@login_required
@role_required('admin')
def delete_schedule(group_id):
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute('DELETE FROM schedule_groups WHERE id = ?', (group_id,))
            if c.rowcount == 0:
                flash('Schedule group not found.', 'warning')
            else:
                db.commit()
                log_audit_action(
                    username=current_user.username,
                    action="delete_schedule_group",
                    target=f"group_id:{group_id}",
                    details="Deleted schedule group"
                )
                flash('Schedule group deleted.', 'warning')
            return redirect(url_for('schedules.manage_schedules'))
    except Exception as e:
        logger.error(f"Error deleting schedule group {group_id}: {e}")
        flash('An error occurred while deleting the schedule group.', 'danger')
        return redirect(url_for('schedules.manage_schedules'))

@schedules_bp.route('/schedule/<int:group_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_schedule(group_id):
    try:
        with get_db() as db:
            c = db.cursor()

            if request.method == 'POST':
                selected_mdocs = request.form.getlist('assign[]')

                c.execute('DELETE FROM resident_schedules WHERE group_id = ?', (group_id,))
                log_audit_action(
                    username=current_user.username,
                    action="clear_assignments",
                    target=f"schedule_group:{group_id}",
                    details="Cleared all resident assignments for this group"
                )

                for mdoc in selected_mdocs:
                    c.execute('INSERT INTO resident_schedules (mdoc, group_id) VALUES (?, ?)', (mdoc, group_id))
                    log_audit_action(
                        username=current_user.username,
                        action="assign_resident",
                        target=f"schedule_group:{group_id}",
                        details=f"Assigned MDOC {mdoc} to schedule group {group_id}"
                    )

                db.commit()
                flash('Resident assignments updated.', 'success')
                return redirect(url_for('schedules.manage_schedules'))

            c.execute('SELECT id, name, mdoc, area, housing_unit, level FROM residents')
            residents = c.fetchall()

            c.execute('SELECT mdoc FROM resident_schedules WHERE group_id = ?', (group_id,))
            assigned = {row[0] for row in c.fetchall()}

            c.execute('SELECT name FROM schedule_groups WHERE id = ?', (group_id,))
            group = c.fetchone()
            if not group:
                flash('Schedule group not found.', 'warning')
                return redirect(url_for('schedules.manage_schedules'))

            return render_template('schedule/schedule_assign.html', group_id=group_id, group_name=group[0], residents=residents, assigned=assigned)
    except Exception as e:
        logger.error(f"Error in assign_schedule for group_id {group_id}: {e}")
        flash('An error occurred while accessing resident assignments.', 'danger')
        return redirect(url_for('schedules.manage_schedules'))

@schedules_bp.route('/schedule/live')
@login_required
def live_schedule():
    try:
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        current_day = now.strftime('%A')

        log_audit_action(
            username=current_user.username,
            action="view",
            target="live_schedule",
            details=f"Viewed live schedule at {now.isoformat()}"
        )

        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT r.name AS resident_name, r.mdoc, sg.name AS group_name, sb.day_of_week,
                       sb.start_time, sb.end_time, sb.location
                FROM resident_schedules rs
                JOIN residents r ON rs.mdoc = r.mdoc
                JOIN schedule_blocks sb ON rs.group_id = sb.group_id
                JOIN schedule_groups sg ON sg.id = sb.group_id
                WHERE sb.day_of_week = ?
                  AND sb.start_time <= ?
                  AND sb.end_time >= ?
                ORDER BY sb.location, sb.start_time
            ''', (current_day, current_time, current_time))

            active_rows = c.fetchall()

        return render_template('schedule/live_schedule.html', active_rows=active_rows, current_day=current_day, current_time=current_time)
    except Exception as e:
        logger.error(f"Error loading live schedule: {e}")
        flash('An error occurred while loading the live schedule.', 'danger')
        return render_template('schedule/live_schedule.html', active_rows=[], current_day='Unknown', current_time='--:--')
    
@schedules_bp.route('/schedule/import')
@login_required
def import_schedule():
    return render_template('schedule/import_schedule.html')
