# routes/schedules.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3

schedules_bp = Blueprint('schedules', __name__, url_prefix='/admin/schedules')

@schedules_bp.route('/')
def list_schedules():
    category_filter = request.args.get('category')
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()

    if category_filter:
        c.execute('''
            SELECT sg.id, sg.name, sg.description, sg.category,
                COUNT(DISTINCT sb.id) AS block_count,
                COUNT(DISTINCT rs.mdoc) AS resident_count
            FROM schedule_groups sg
            LEFT JOIN schedule_blocks sb ON sg.id = sb.group_id
            LEFT JOIN resident_schedules rs ON sg.id = rs.group_id
            WHERE sg.category = ?
            GROUP BY sg.id
        ''', (category_filter,))
    else:
        c.execute('''
            SELECT sg.id, sg.name, sg.description, sg.category,
                COUNT(DISTINCT sb.id) AS block_count,
                COUNT(DISTINCT rs.mdoc) AS resident_count
            FROM schedule_groups sg
            LEFT JOIN schedule_blocks sb ON sg.id = sb.group_id
            LEFT JOIN resident_schedules rs ON sg.id = rs.group_id
            GROUP BY sg.id
        ''')

    groups = c.fetchall()
    conn.close()

    return render_template('schedules.html', groups=groups, category_filter=category_filter)

@schedules_bp.route('/create', methods=['GET', 'POST'])
def create_schedule():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']

        conn = sqlite3.connect('rezscan.db')
        c = conn.cursor()
        c.execute('INSERT INTO schedule_groups (name, description, category) VALUES (?, ?, ?)', (name, description, category))
        conn.commit()
        conn.close()
        flash('Schedule group created successfully.', 'success')
        return redirect(url_for('schedules.list_schedules'))

    return render_template('schedule_form.html', action='Create', schedule={})

@schedules_bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
def edit_schedule(group_id):
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()

    if request.method == 'POST':
        if 'block_editor' in request.form:
            day_list = request.form.getlist('day[]')
            location_list = request.form.getlist('location[]')
            start_list = request.form.getlist('start_time[]')
            end_list = request.form.getlist('end_time[]')
            week_list = request.form.getlist('week_type[]')
            remove_ids = request.form.getlist('remove[]')

            for block_id in remove_ids:
                c.execute('DELETE FROM schedule_blocks WHERE id = ? AND group_id = ?', (block_id, group_id))

            for i in range(len(day_list)):
                day = day_list[i].strip()
                location = location_list[i].strip()
                start = start_list[i].strip()
                end = end_list[i].strip()
                week = week_list[i].strip()

                if not day or not location or not start or not end:
                    continue

                if i < len(remove_ids):
                    continue

                c.execute('''
                    INSERT INTO schedule_blocks (group_id, day_of_week, location, start_time, end_time, week_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (group_id, day, location, start, end, week))

            conn.commit()
            conn.close()
            flash('Schedule blocks updated.', 'success')
            return redirect(url_for('schedules.edit_schedule', group_id=group_id))

        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        c.execute('UPDATE schedule_groups SET name = ?, description = ?, category = ? WHERE id = ?', (name, description, category, group_id))
        conn.commit()
        conn.close()
        flash('Schedule group updated successfully.', 'success')
        return redirect(url_for('schedules.list_schedules'))

    c.execute('SELECT * FROM schedule_groups WHERE id = ?', (group_id,))
    schedule = c.fetchone()

    c.execute('SELECT * FROM schedule_blocks WHERE group_id = ?', (group_id,))
    blocks = c.fetchall()

    c.execute('SELECT name FROM locations ORDER BY name')
    locations = [row[0] for row in c.fetchall()]

    conn.close()
    return render_template('admin/schedule_form.html', action='Edit', schedule=schedule, blocks=blocks, locations=locations)

@schedules_bp.route('/<int:group_id>/delete')
def delete_schedule(group_id):
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()
    c.execute('DELETE FROM schedule_groups WHERE id = ?', (group_id,))
    conn.commit()
    conn.close()
    flash('Schedule group deleted.', 'warning')
    return redirect(url_for('schedules.list_schedules'))

@schedules_bp.route('/<int:group_id>/assign', methods=['GET', 'POST'])
def assign_schedule(group_id):
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()

    if request.method == 'POST':
        selected_mdocs = request.form.getlist('assign[]')
        c.execute('DELETE FROM resident_schedules WHERE group_id = ?', (group_id,))
        for mdoc in selected_mdocs:
            c.execute('INSERT INTO resident_schedules (mdoc, group_id) VALUES (?, ?)', (mdoc, group_id))
        conn.commit()
        conn.close()
        flash('Resident assignments updated.', 'success')
        return redirect(url_for('schedules.list_schedules'))

    c.execute('SELECT id, name, mdoc, area, housing_unit, level FROM residents')
    residents = c.fetchall()

    c.execute('SELECT mdoc FROM resident_schedules WHERE group_id = ?', (group_id,))
    assigned = {row[0] for row in c.fetchall()}

    c.execute('SELECT name FROM schedule_groups WHERE id = ?', (group_id,))
    group_name = c.fetchone()[0]
    conn.close()

    return render_template('schedule_assign.html', group_id=group_id, group_name=group_name, residents=residents, assigned=assigned)
