# rezscan_app/routes/movement_exports.py

from flask import Blueprint, request, send_file, flash, redirect, url_for
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required
import datetime
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

movement_exports_bp = Blueprint('movement_exports', __name__, url_prefix='/admin/movement')

@movement_exports_bp.route('/export_csv', methods=['GET'])
@login_required
@role_required('admin', 'scheduling')
def export_movement_csv():
    selected_date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    try:
        db = get_db()
        c = db.cursor()

        c.execute('''
            SELECT sb.start_time, sb.end_time, sb.location, sg.name AS group_name, sg.category, rs.mdoc, r.name
            FROM schedule_blocks sb
            JOIN schedule_groups sg ON sb.group_id = sg.id
            LEFT JOIN resident_schedules rs ON rs.group_id = sg.id
            LEFT JOIN residents r ON rs.mdoc = r.mdoc
            WHERE sb.day_of_week = ?
        ''', (datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A'),))
        rows = c.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Start Time', 'End Time', 'Location', 'Group', 'Category', 'MDOC', 'Name'])

        for row in rows:
            writer.writerow([row['start_time'], row['end_time'], row['location'], row['group_name'], row['category'], row['mdoc'], row['name']])

        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()),
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name=f'movement_board_{selected_date}.csv')
    except Exception as e:
        flash(f"Error exporting CSV: {str(e)}", "danger")
        return redirect(url_for('movement_board.view_movement_schedule'))

@movement_exports_bp.route('/export_pdf', methods=['GET'])
@login_required
@role_required('admin','scheduling')
def export_movement_pdf():
    selected_date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    try:
        db = get_db()
        c = db.cursor()

        c.execute('''
            SELECT sb.start_time, sb.end_time, sb.location, sg.name AS group_name, sg.category, rs.mdoc, r.name
            FROM schedule_blocks sb
            JOIN schedule_groups sg ON sb.group_id = sg.id
            LEFT JOIN resident_schedules rs ON rs.group_id = sg.id
            LEFT JOIN residents r ON rs.mdoc = r.mdoc
            WHERE sb.day_of_week = ?
        ''', (datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A'),))
        rows = c.fetchall()

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f"Movement Board - {selected_date}")
        pdf.drawString(50, 750, f"Movement Board - {selected_date}")

        y = 730
        pdf.setFont("Helvetica", 10)
        for row in rows:
            pdf.drawString(50, y, f"{row['start_time']} - {row['end_time']} | {row['location']} | {row['group_name']} | {row['category']} | {row['mdoc']} | {row['name']}")
            y -= 15
            if y < 50:
                pdf.showPage()
                y = 750

        pdf.save()
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f'movement_board_{selected_date}.pdf')
    except Exception as e:
        flash(f"Error exporting PDF: {str(e)}", "danger")
        return redirect(url_for('movement_board.view_movement_schedule'))
