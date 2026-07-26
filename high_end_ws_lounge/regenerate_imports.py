"""
Clean import section for database_fixed.py
"""

clean_imports = '''"""
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
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
    IntegerField,
    BooleanField,
    TextAreaField,
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

# Read the full file
with open('database_fixed.py', 'r') as f:
    content = f.read()

# Find where the imports end (where load_dotenv() ends)
split_index = content.find('# -----')

if split_index == -1:
    print("Error: Could not find import end marker")
    exit(1)

# Get the rest of the file after imports
rest_of_file = content[split_index:]

# Reconstruct file with clean imports
new_content = clean_imports + rest_of_file

# Write back
with open('database_fixed.py', 'w') as f:
    f.write(new_content)

print("✓ Imports regenerated cleanly")
