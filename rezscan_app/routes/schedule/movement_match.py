# #movement_match.py
# from flask import Blueprint, render_template, session, request, flash
# from flask_login import login_required
# from rezscan_app.routes.common.auth import role_required
# from rezscan_app.models.database import get_db
# from rezscan_app.utils.schedule_parser import parse_source_line
# import re
# import difflib
# import logging
# from rezscan_app.utils.logging_config import setup_logging

# setup_logging()
# logger = logging.getLogger(__name__)

# movement_match_bp = Blueprint('movement_match', __name__)

# WC_ROOMS = {"rm 109", "rm 110", "rm 118", "wc art room"}
# UNIT_I_II_ROOMS = {"rm 101", "rm 102", "rm 103", "rm 104", "rm 105", "rm 113", "rm 117"}

# def infer_block_unit(title):
#     lower = title.lower()
#     for room in WC_ROOMS:
#         if room in lower:
#             return 'wc'
#     for room in UNIT_I_II_ROOMS:
#         if room in lower:
#             return 'unit12'
#     return None

# @movement_match_bp.route('/schedule/match_preview', methods=['GET', 'POST'])
# @login_required
# @role_required('admin', 'scheduling')
# def match_preview():
#     raw_text = request.form.get('movement_text', '') if request.method == 'POST' else session.get('movement_text', '')
#     if len(raw_text) > 3000:
#         flash("Input was too large. Truncated for preview.", "warning")
#         raw_text = raw_text[:3000]
#     session['movement_text'] = raw_text

#     if not raw_text:
#         return render_template('schedule/match_preview.html', blocks=[], raw_text="", summary={'matched': 0, 'unmatched': 0, 'conflicted': 0, 'fuzzy': 0})

#     db = get_db()
#     c = db.cursor()
#     c.execute("SELECT mdoc, name, housing_unit FROM residents")
#     residents = c.fetchall()

#     residents_by_name = {}
#     residents_by_lastname = {}
#     all_names = []
#     residents_by_mdoc = {}

#     for r in residents:
#         name_key = r['name'].strip().lower()
#         last_name = r['name'].split(",")[0].strip().lower()
#         residents_by_name.setdefault(name_key, []).append(r)
#         residents_by_lastname.setdefault(last_name, []).append(r)
#         all_names.append(name_key)
#         if r['mdoc']:
#             residents_by_mdoc[str(r['mdoc'])] = r

#     def resolve_resident(name, mdoc=None, housing_unit=None, context_title=None):
#         unit_hint = infer_block_unit(context_title or '')

#         if mdoc and mdoc in residents_by_mdoc:
#             return residents_by_mdoc[mdoc]

#         name_key = name.strip().lower()
#         matches = residents_by_name.get(name_key, [])
#         if len(matches) == 1:
#             return matches[0]
#         elif len(matches) > 1:
#             return 'conflict'

#         last = name_key.split(",")[0].strip()
#         candidates = residents_by_lastname.get(last.lower(), [])

#         if unit_hint == 'wc':
#             candidates = [r for r in candidates if r['housing_unit'] and ("women" in r['housing_unit'].lower() or r['housing_unit'].lower().startswith("b"))]
#         elif unit_hint == 'unit12':
#             candidates = [r for r in candidates if r['housing_unit'] and not ("women" in r['housing_unit'].lower() or r['housing_unit'].lower().startswith("b"))]

#         if len(candidates) == 1:
#             return candidates[0]
#         elif len(candidates) > 1:
#             return 'conflict'

#         return None

#     def fuzzy_suggestion(name, all_names):
#         name_key = name.strip().lower()
#         close = difflib.get_close_matches(name_key, all_names, n=1, cutoff=0.85)
#         if close:
#             return close[0]
#         return None

#     def secondary_resolver(name: str, residents: list) -> dict | None:
#         if '-' not in name:
#             return None
#         last_name_candidate = name.split(',')[0].strip().upper()
#         matches = [res for res in residents if '-' in res['name'] and last_name_candidate in res['name']]
#         if len(matches) == 1:
#             return matches[0]
#         elif len(matches) > 1:
#             return 'conflict'
#         return None

#     def normalize(line):
#         line = line.replace('–', '-').replace('—', '-').replace('#', '-').replace(',', ', ')
#         line = re.sub(r'-+', '-', line)
#         line = re.sub(r'([A-Za-z]),([A-Za-z])', r'\1, \2', line)
#         return re.sub(r'\s+', ' ', line.strip())

#     def ignore_line(line):
#         line = line.strip()
#         if not line:
#             return True
#         if any(phrase in line for phrase in [
#             "Report Times", "Computer Lab", "Activities Building", "HiSET", "Room",
#             "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "OSHA", "Extra Duty",
#             "MCC", "No Evenings", "Study", "Continued", "AM", "PM", "access to technology"
#         ]):
#             return True
#         return False

#     lines = raw_text.strip().splitlines()
#     blocks = []
#     current_block = {'start': None, 'title': '', 'lines': []}

#     for line in lines:
#         line = normalize(line)
#         if re.match(r"^(All Day|\d{1,2}:\d{2})", line):
#             if current_block['lines']:
#                 blocks.append(current_block)
#                 current_block = {'start': None, 'title': '', 'lines': []}
#             parts = re.split(r' - ', line, maxsplit=1)
#             current_block['start'] = parts[0].strip()
#             if len(parts) > 1:
#                 current_block['title'] = parts[1].strip()
#         else:
#             current_block['lines'].append(line)

#     if current_block['lines']:
#         blocks.append(current_block)

#     parsed_blocks = []
#     for block in blocks:
#         matched = []
#         unmatched = []
#         conflicts = []
#         fuzzy = []

#         for line in block['lines']:
#             line = normalize(line)
#             if ignore_line(line):
#                 continue

#             parts = [p.strip() for p in re.split(r'-', line) if p.strip()]
#             name = mdoc = housing = None

#             for part in parts:
#                 if ',' in part:
#                     name = part
#                 elif part.isdigit() and len(part) >= 5:
#                     mdoc = part
#                 elif not housing:
#                     housing = part

#             result = resolve_resident(name or line, mdoc, housing, context_title=block['title'])

#             if result is None:
#                 result = secondary_resolver(name or line, residents)

#             if result is None:
#                 fuzzy_match = fuzzy_suggestion(name or line, all_names)
#                 if fuzzy_match:
#                     suggested = residents_by_name.get(fuzzy_match)
#                     if suggested and len(suggested) == 1:
#                         fuzzy.append({
#                             'suggested_name': fuzzy_match,
#                             'original': line,
#                             'name': suggested[0]['name'],
#                             'mdoc': suggested[0]['mdoc'],
#                             'housing_unit': suggested[0]['housing_unit']
#                         })
#                     elif suggested and len(suggested) > 1:
#                         conflicts.append(line.strip())
#                 else:
#                     unmatched.append(line.strip())
#             elif result == 'conflict':
#                 conflicts.append(line.strip())
#             else:
#                 # ✅ Auto-approve logic here
#                 auto_approve = session.get('auto_approve_enabled', True)
#                 if auto_approve:
#                     c.execute("SELECT id FROM schedule_groups WHERE name = ?", (block['title'],))
#                     group = c.fetchone()
#                     if group:
#                         group_id = group['id']
#                         c.execute('INSERT OR IGNORE INTO resident_schedules (mdoc, group_id) VALUES (?, ?)', (result['mdoc'], group_id))
#                         c.execute('''
#                             INSERT INTO schedule_match_review (
#                                 block_title, block_time, source_line,
#                                 suggested_name, suggested_mdoc, suggested_housing,
#                                 match_type, status, reviewed_by, reviewed_at
#                             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                         ''', (block['title'], block['start'], line, result['name'], result['mdoc'], result['housing_unit'], 'fuzzy', 'approved', 'Auto', datetime.now()))
#                         continue

#                 matched.append({
#                     'name': result['name'],
#                     'mdoc': result['mdoc'],
#                     'housing_unit': result['housing_unit']
#                 })

#         parsed_blocks.append({
#             'start': block['start'],
#             'title': block['title'],
#             'matched': matched,
#             'unmatched': unmatched,
#             'conflicts': conflicts,
#             'fuzzy': fuzzy
#         })

#     summary = {
#         'matched': sum(len(b['matched']) for b in parsed_blocks),
#         'unmatched': sum(len(b['unmatched']) for b in parsed_blocks),
#         'conflicted': sum(len(b['conflicts']) for b in parsed_blocks),
#         'fuzzy': sum(len(b['fuzzy']) for b in parsed_blocks)
#     }

#     db.commit()
#     c.execute("SELECT COUNT(*) FROM schedule_match_review")
#     count = c.fetchone()[0]
#     logger.debug(f"✅ Review table now contains entries for {count} blocks")

#     return render_template('schedule/match_preview.html', blocks=parsed_blocks, raw_text=raw_text, summary=summary)

