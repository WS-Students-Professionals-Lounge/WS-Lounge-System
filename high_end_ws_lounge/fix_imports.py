"""
Restore database_fixed.py with correct imports from a fresh backup.
This script will rewrite the imports section completely.
"""

# Read the entire file
with open('database_fixed.py', 'r') as f:
    full_content = f.read()

# Find the end of imports (after load_dotenv() line and before # --- comment)
import_end_marker = 'load_dotenv()\n\n# -----'
if import_end_marker not in full_content:
    print("Could not find import end marker, trying alternate...")
    import_end_marker = 'load_dotenv()'

# Build new clean imports section
new_imports = '''"""
Fixed database.py - clean imports for membership features
"""

import os
from datetime import datetime, timedelta

from flask import Flask
from flask_mail import Mail
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from sqlalchemy import and_, create_engine, func, inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import (
    DateField,
    TimeField,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    IntegerField,
    BooleanField,
    TextAreaField,
    DateTimeField,
    DecimalField,
    PasswordField,
)
from wtforms.validators import (
    ValidationError,
    Email,
    EqualTo,
    Length,
    Optional,
    NumberRange,
    DataRequired,
)

load_dotenv()

# -----'''

# Extract everything after the import section
after_imports = full_content[full_content.find(import_end_marker) + len(import_end_marker):]

# Reconstruct
reconstructed = new_imports + after_imports

# Write back
with open('database_fixed.py', 'w') as f:
    f.write(reconstructed)

print("✓ Fixed database_fixed.py imports")
