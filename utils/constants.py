# Housing Information
UNIT_OPTIONS = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]

HOUSING_OPTIONS = [
    "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
    "Women's Center", "A Pod", "B North", "B South",
    "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
]

# Resident Behavioral Levels
LEVEL_OPTIONS = ["1", "2", "3", "4"]

# User Roles
VALID_ROLES = ['admin', 'officer', 'scheduling', 'viewer']

# Location Types
LOCATION_TYPES = ["Housing", "Education", "Recreation", "Visits", "Work"]

# Location Categories
SCHEDULE_CATEGORIES = ["Education", "Work", "Recreation"]

TIME_BLOCKS = ["Morning", "Afternoon", "Evening"]
PROGRAMS = ["Education", "Work", "Gym", "Other"]

# Dictates password length for sign-on
MIN_PASSWORD_LENGTH = 8

# Table Headers for Import History
IMPORT_HISTORY_TABLE_HEADERS = [
    '#', 'Timestamp', 'User', 'Added', 'Updated', 'Deleted', 'Failed', 'Total', 'Actions'
]

# CSV Import Headers
CSV_REQUIRED_HEADERS = ['mdoc', 'name', 'unit', 'housing_unit', 'level']
CSV_OPTIONAL_HEADERS = ['photo']