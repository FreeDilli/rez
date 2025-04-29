# constants.py

# --- Housing Information ---
UNIT_OPTIONS = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]
HOUSING_OPTIONS = [
    "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
    "Women's Center", "A Pod", "B North", "B South",
    "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
]

# --- Resident Behavior Levels ---
LEVEL_OPTIONS = ["1", "2", "3", "4"]

# --- User Roles ---
VALID_ROLES = ['admin', 'officer', 'scheduling', 'viewer']
ROLE_REDIRECTS = {
    'admin': 'admin.admin_dashboard',
    'officer': 'user_dashboard.dashboard',
    'viewer': 'user_dashboard.dashboard',
    'scheduling': 'user_dashboard.dashboard',
}

# --- Scheduling ---
LOCATION_TYPES = ['Housing', 'Education', 'Recreation', 'Visits', 'Work']
SCHEDULE_CATEGORIES = ["Education", "Work", "Recreation"]
TIME_BLOCKS = ["Morning", "Afternoon", "Evening"]
PROGRAMS = ["Education", "Work", "Gym", "Other"]

# --- Security ---
MIN_PASSWORD_LENGTH = 8

# --- Data Formats ---
DATEFORMAT = '%m-%d-%Y'  # Matches dateformat filter output
TIMEFORMAT = '%H:%M:%S'

# --- Import/Export ---
IMPORT_HISTORY_TABLE_HEADERS = [
    '#', 'Timestamp', 'User', 'Added', 'Updated', 'Deleted', 'Failed', 'Total', 'Actions'
]
CSV_REQUIRED_HEADERS = ['mdoc', 'name', 'unit', 'housing_unit', 'level']
CSV_OPTIONAL_HEADERS = ['photo']
