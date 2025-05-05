import re
from PyPDF2 import PdfReader

def parse_source_line(line):
    result = {
        'suggested_name': None,
        'suggested_mdoc': None,
        'suggested_housing': None
    }

    if not line:
        return result

    # Extract full name (e.g., Last, First)
    name_match = re.search(r'^([A-Z]+,\s+[A-Z\.\-\'\s]+)', line.strip(), re.IGNORECASE)
    if name_match:
        result['suggested_name'] = name_match.group(1).strip().upper()

    # Extract MDOC: 1–6 digit number (after "MDOC:" or alone)
    mdoc_match = re.search(r'MDOC[:#]?\s*(\d{1,6})', line, re.IGNORECASE)
    if mdoc_match:
        result['suggested_mdoc'] = mdoc_match.group(1)

    # Extract housing (after "Housing:", "Unit:", or keywords like "Echo", "Foxtrot")
    housing_match = re.search(r'(Housing|Unit)[:#]?\s*([A-Za-z0-9\- ]+)', line, re.IGNORECASE)
    if housing_match:
        result['suggested_housing'] = housing_match.group(2).strip().title()
    else:
        # Fallback: look for known housing terms
        keywords = ['Echo', 'Foxtrot', 'Delta', 'Dorm 5', 'Dorm 6', 'Women', 'B North', 'C Center', 'A Pod']
        for word in keywords:
            if word.lower() in line.lower():
                result['suggested_housing'] = word
                break

    return result
def parse_schedule_blocks(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return parse_ocr_text(text)

def parse_ocr_text(raw_text):
    blocks = []
    lines = raw_text.splitlines()
    current_block = None

    time_header_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect a new block header
        if time_header_pattern.search(line) or line.lower().startswith(("wc", "cr", "rm", "unit")):
            if current_block:
                blocks.append(current_block)
            current_block = {
                "title": line,
                "time": time_header_pattern.search(line).group(0) if time_header_pattern.search(line) else None,
                "residents": []
            }
        else:
            if current_block:
                current_block["residents"].append(line)

    if current_block:
        blocks.append(current_block)

    return blocks

