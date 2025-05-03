from flask import Blueprint, render_template, session, request, flash
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
from rezscan_app.models.database import get_db
import re

movement_match_bp = Blueprint('movement_match', __name__)

@movement_match_bp.route('/schedule/match_preview', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'scheduling')
def match_preview():
    raw_text = ""

    if request.method == 'POST':
        raw_text = request.form.get('movement_text', '')
        if len(raw_text) > 3000:
            flash("Input was too large. Truncated for preview.", "warning")
            raw_text = raw_text[:3000]
        session['movement_text'] = raw_text
    else:
        raw_text = session.get('movement_text', '')

    parsed_blocks = []
    if not raw_text:
        return render_template('schedule/match_preview.html', blocks=[], raw_text="")

    db = get_db()
    c = db.cursor()
    c.execute("SELECT mdoc, name, housing_unit FROM residents")
    resident_index = {row['name'].strip().lower(): {"mdoc": row['mdoc'], "housing": row['housing_unit']} for row in c.fetchall()}

    block_pattern = re.compile(r"(?P<start>All Day|\d{1,2}:\d{2}\s?[AP]M)[^\n]*\n(?P<title>[^\n]+)\n(?P<residents>(?:.+\n)+?)(?=\d{1,2}:\d{2}\s?[AP]M|All Day|\Z)", re.IGNORECASE)
    resident_pattern = re.compile(r"(?P<name>[A-Z][a-z]+(?:[\s,.'-]+[A-Z][a-z]+)+)")

    for match in block_pattern.finditer(raw_text):
        start = match.group('start').strip()
        title = match.group('title').strip()
        residents_raw = match.group('residents').strip().splitlines()

        residents = []
        for line in residents_raw:
            name_match = resident_pattern.search(line.strip())
            if name_match:
                name = name_match.group('name').strip()
                match_data = resident_index.get(name.lower())
                residents.append({
                    "name": name,
                    "mdoc": match_data["mdoc"] if match_data else None,
                    "housing": match_data["housing"] if match_data else None,
                    "matched": match_data is not None
                })

        parsed_blocks.append({
            "start": start,
            "title": title,
            "residents": residents
        })

    return render_template("schedule/match_preview.html", blocks=parsed_blocks, raw_text=raw_text)



