#schedule_match_review
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.routes.common.auth import role_required
from rezscan_app.models.database import get_db
from difflib import SequenceMatcher
from flask import session
import logging

logger = logging.getLogger(__name__)

schedule_review_bp = Blueprint('schedule_review', __name__, url_prefix='/schedule')

@schedule_review_bp.route('/review_matches', methods=['GET'])
@login_required
@role_required('admin', 'scheduling')
def review_matches():
    from rezscan_app.utils.schedule_parser import parse_source_line
    
    # Enables Auto-Approve feature
    auto_approve_enabled = session.get("auto_approve_enabled", True)

    logger.debug(f"User {current_user.username} accessing schedule match review page.")
    matches = []
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Fetch all residents
            c.execute("SELECT mdoc, name, housing_unit FROM residents")
            residents = c.fetchall()
            residents_by_mdoc = {r['mdoc']: r for r in residents if r['mdoc']}
            all_residents = residents

            # Fetch review queue
            c.execute('''
                SELECT id, block_title, block_time, source_line,
                       suggested_name, suggested_mdoc, suggested_housing,
                       match_type, status
                FROM schedule_match_review
                WHERE status = 'pending'
                ORDER BY id DESC
            ''')
            rows = c.fetchall()

            for row in rows:
                suggested_name = row['suggested_name']
                mdoc = row['suggested_mdoc']
                housing = row['suggested_housing']
                match_type = row['match_type']
                db_check = False
                candidates = []
                can_auto_approve = False

                # Fallback: try to extract missing values from source line
                if not suggested_name or not mdoc or not housing:
                    parsed = parse_source_line(row['source_line'] or "")
                    if not suggested_name:
                        suggested_name = parsed.get("suggested_name")
                    if not mdoc:
                        mdoc = parsed.get("suggested_mdoc")
                    if not housing:
                        housing = parsed.get("suggested_housing")
                    logger.debug(f"[PARSE FILL] Row {row['id']}: name={suggested_name}, mdoc={mdoc}, housing={housing}")

                # Direct MDOC match
                if mdoc and mdoc in residents_by_mdoc and auto_approve_enabled:
                    db_check = True
                    can_auto_approve = True
                    match_type = 'fuzzy'

                # Fuzzy/conflict name match
                elif suggested_name and suggested_name.strip():
                    suggested_name = suggested_name.strip()

                    if ',' not in suggested_name:
                        logger.debug(f"[MATCH DEBUG] Skipping invalid name format: '{suggested_name}'")
                    else:
                        last, *first_parts = suggested_name.split(',')
                        last = last.strip()
                        first_initial = first_parts[0].strip()[0] if first_parts else ''

                        # Start broad: last name only
                        possible = [r for r in all_residents if r['name'].split(',')[0].strip().lower() == last.lower()]

                        if housing:
                            possible = [r for r in possible if r['housing_unit'] and housing.lower() in r['housing_unit'].lower()]

                        if first_initial:
                            possible = [
                                r for r in possible
                                if len(r['name'].split(',')) > 1 and r['name'].split(',')[1].strip().startswith(first_initial)
                            ]

                        # Fuzzy fallback
                        if not possible:
                            threshold = 0.85
                            def similar(a, b):
                                return SequenceMatcher(None, a.lower(), b.lower()).ratio()

                            possible = [r for r in all_residents if similar(r['name'], suggested_name) >= threshold]

                        if possible:
                            db_check = True
                            candidates = possible
                            logger.debug(f"[MATCH DEBUG] Candidates for '{suggested_name}' in block {row['id']}: {[r['name'] for r in possible]}")
                        else:
                            logger.debug(f"[MATCH DEBUG] No candidates found for '{suggested_name}' in block {row['id']}")

                # Auto-approve logic for MDOC match
                if can_auto_approve:
                    try:
                        c.execute("SELECT id FROM schedule_groups WHERE name = ?", (row['block_title'],))
                        group = c.fetchone()
                        if group:
                            group_id = group['id']
                            c.execute("INSERT OR IGNORE INTO resident_schedules (mdoc, group_id) VALUES (?, ?)", (mdoc, group_id))
                            c.execute("""
                                UPDATE schedule_match_review
                                SET status = 'approved',
                                    reviewed_by = ?,
                                    reviewed_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (current_user.username, row['id']))
                            conn.commit()
                            flash(f"✅ Auto-approved match for MDOC {mdoc} in block '{row['block_title']}'", "success")
                    except Exception as e:
                        logger.error(f"❌ Error during auto-approval: {e}")

                matches.append({
                    'id': row['id'],
                    'block_title': row['block_title'],
                    'block_time': row['block_time'],
                    'source_line': row['source_line'],
                    'suggested_name': suggested_name,
                    'suggested_mdoc': mdoc,
                    'suggested_housing': housing,
                    'match_type': match_type or 'unmatched',
                    'status': row['status'],
                    'db_check': db_check,
                    'candidates': candidates,
                    'can_auto_approve': can_auto_approve,
                })

    except Exception as e:
        logger.error(f"\u274c Error fetching schedule matches: {str(e)}", exc_info=True)
        flash("Failed to load schedule match review data.", "danger")

    return render_template('schedule/review_matches.html', matches=matches)

@schedule_review_bp.route('/review/<int:match_id>/approve', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def approve_match_by_id(match_id):  # <-- rename the function

    db = get_db()
    c = db.cursor()

    try:
        c.execute("SELECT suggested_mdoc, block_title FROM schedule_match_review WHERE id = ?", (match_id,))
        row = c.fetchone()

        if not row:
            flash("Match not found.", "warning")
            return redirect(url_for('schedule_review.review_matches'))

        mdoc, block_title = row['suggested_mdoc'], row['block_title']

        c.execute("SELECT id FROM schedule_groups WHERE name = ?", (block_title,))
        group = c.fetchone()

        if not group:
            flash(f"No matching schedule group found for '{block_title}'.", "danger")
            return redirect(url_for('schedule_review.review_matches'))

        group_id = group['id']

        c.execute("INSERT OR IGNORE INTO resident_schedules (mdoc, group_id) VALUES (?, ?)", (mdoc, group_id))

        c.execute("""
            UPDATE schedule_match_review
            SET status = 'approved',
                reviewed_by = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (current_user.username, match_id))

        db.commit()
        flash("✅ Match approved and assigned.", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error approving match: {str(e)}")
        flash("Failed to approve match.", "danger")

    return redirect(url_for('schedule_review.review_matches'))


@schedule_review_bp.route('/review/<int:match_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def delete_match(match_id):
    db = get_db()
    c = db.cursor()

    try:
        c.execute("""
            UPDATE schedule_match_review
            SET status = 'rejected',
                reviewed_by = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (current_user.username, match_id))

        db.commit()
        flash("🚫 Match rejected.", "info")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error rejecting match: {str(e)}")
        flash("Failed to reject match.", "danger")

    return redirect(url_for('schedule_review.review_matches'))


@schedule_review_bp.route('/review/approve_manual', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def approve_manual():
    match_id = request.form.get("match_id")
    selected_mdoc = request.form.get("selected_mdoc")

    if not match_id or not selected_mdoc:
        flash("Missing match ID or MDOC for approval.", "warning")
        return redirect(url_for("schedule_review.review_matches"))

    db = get_db()
    c = db.cursor()

    try:
        c.execute("SELECT block_title FROM schedule_match_review WHERE id = ?", (match_id,))
        row = c.fetchone()

        if not row:
            flash("Match not found.", "danger")
            return redirect(url_for("schedule_review.review_matches"))

        block_title = row["block_title"]

        c.execute("SELECT id FROM schedule_groups WHERE name = ?", (block_title,))
        group = c.fetchone()

        if not group:
            flash(f"No matching schedule group found for '{block_title}'.", "danger")
            return redirect(url_for("schedule_review.review_matches"))

        group_id = group["id"]

        c.execute(
            "INSERT OR IGNORE INTO resident_schedules (mdoc, group_id) VALUES (?, ?)",
            (selected_mdoc, group_id)
        )

        c.execute(
            """
            UPDATE schedule_match_review
            SET status = 'approved',
                suggested_mdoc = ?,
                reviewed_by = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (selected_mdoc, current_user.username, match_id)
        )

        db.commit()
        flash("✅ Match approved using selected resident.", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error approving selected candidate: {str(e)}")
        flash("Failed to approve match.", "danger")

    return redirect(url_for("schedule_review.review_matches"))

@schedule_review_bp.route('/review/<int:match_id>/manual', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'scheduling')
def review_manual(match_id):
    db = get_db()
    c = db.cursor()

    # Get match info
    c.execute('SELECT * FROM schedule_match_review WHERE id = ?', (match_id,))
    match = c.fetchone()
    if not match:
        flash("Match not found.", "danger")
        return redirect(url_for('schedule_review.review_matches'))

    # Fetch all residents for manual selection
    c.execute('SELECT mdoc, name, housing_unit FROM residents ORDER BY name')
    residents = c.fetchall()

    if request.method == 'POST':
        selected_mdoc = request.form.get('selected_mdoc')

        if not selected_mdoc:
            flash("Please select a resident before approving.", "warning")
            return redirect(url_for('schedule_review.review_manual', match_id=match_id))

        # Get group ID
        c.execute("SELECT id FROM schedule_groups WHERE name = ?", (match['block_title'],))
        group = c.fetchone()
        if not group:
            flash(f"No matching schedule group found for '{match['block_title']}'.", "danger")
            return redirect(url_for('schedule_review.review_matches'))

        group_id = group['id']

        try:
            # Insert assignment
            c.execute('INSERT OR IGNORE INTO resident_schedules (mdoc, group_id) VALUES (?, ?)', (selected_mdoc, group_id))

            # Update match review entry
            c.execute('''
                UPDATE schedule_match_review
                SET status = 'approved',
                    suggested_mdoc = ?,
                    reviewed_by = ?,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (selected_mdoc, current_user.username, match_id))

            db.commit()
            flash("✅ Match approved manually.", "success")
            return redirect(url_for('schedule_review.review_matches'))

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Manual approval error: {e}")
            flash("Failed to approve match.", "danger")

    return render_template('schedule/review_manual.html', match=match, residents=residents)

@schedule_review_bp.route('/toggle_auto_approve', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def toggle_auto_approve():
    enable = request.form.get("enable") == "1"
    session["auto_approve_enabled"] = enable
    flash(f"Auto-approve is now {'enabled' if enable else 'disabled'}.", "info")
    return redirect(url_for("schedule_review.review_matches"))
