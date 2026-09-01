#!/usr/bin/env python3
"""
Final fix for database_fixed.py - replaces entire import section
"""

# Read the file
with open('database_fixed.py', 'rb') as f:
    binary_content = f.read()

# Convert to string
content = binary_content.decode('utf-8')

# Find where the actual working code starts (search for Config class or BASE_DIR)
split_point = content.find('BASE_DIR = os.path.abspath')
if split_point == -1:
    # Try finding the first comment line after validators
    split_point = content.find('# -----')
    if split_point == -1:
        print("ERROR: Could not find split point!")
        exit(1)

# Extract the working section
working_section = content[split_point:]

# Create completely fresh imports
fresh_imports = '''"""
Fixed database.py - clean imports for membership features
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager, UserMixin
from flask_mail import Mail
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import and_, func, inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, DateField, DateTimeField, DecimalField, HiddenField, IntegerField, PasswordField, \\
    SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

load_dotenv()

'''

# Reconstruct file
new_content = fresh_imports + working_section

# Write back using binary mode to avoid encoding issues
with open('database_fixed.py', 'wb') as f:
    f.write(new_content.encode('utf-8'))

print("SUCCESS: database_fixed.py repaired!")
