# routes/schedules.py
from flask import Blueprint, render_template, request, redirect, url_for
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
        return redirect(url_for('schedules.list_schedules'))

    return render_template('schedule_form.html', action='Create', schedule={})

@schedules_bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
def edit_schedule(group_id):
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        c.execute('UPDATE schedule_groups SET name = ?, description = ?, category = ? WHERE id = ?', (name, description, category, group_id))
        conn.commit()
        conn.close()
        return redirect(url_for('schedules.list_schedules'))

    c.execute('SELECT * FROM schedule_groups WHERE id = ?', (group_id,))
    schedule = c.fetchone()
    conn.close()
    return render_template('schedule_form.html', action='Edit', schedule=schedule)

@schedules_bp.route('/<int:group_id>/delete')
def delete_schedule(group_id):
    conn = sqlite3.connect('rezscan.db')
    c = conn.cursor()
    c.execute('DELETE FROM schedule_groups WHERE id = ?', (group_id,))
    conn.commit()
    conn.close()
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
        return redirect(url_for('schedules.list_schedules'))

    c.execute('SELECT id, name, mdoc, area, housing_unit, level FROM residents')
    residents = c.fetchall()

    c.execute('SELECT mdoc FROM resident_schedules WHERE group_id = ?', (group_id,))
    assigned = {row[0] for row in c.fetchall()}

    c.execute('SELECT name FROM schedule_groups WHERE id = ?', (group_id,))
    group_name = c.fetchone()[0]
    conn.close()

    return render_template('schedule_assign.html', group_id=group_id, group_name=group_name, residents=residents, assigned=assigned)