"""
Database Migration Script
Adds receipt_image column to solo_plans table if it doesn't exist.
"""

import os
import sys

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db
from run import app
from sqlalchemy import inspect, text


def migrate_receipt_image():
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Add receipt_image to solo_plans table if not exists
        if inspector.has_table("solo_plans"):
            columns = [col["name"] for col in inspector.get_columns("solo_plans")]
            if "receipt_image" not in columns:
                print("Adding receipt_image to solo_plans table...")
                db.session.execute(text("ALTER TABLE solo_plans ADD COLUMN receipt_image VARCHAR(255)"))
                db.session.commit()
                print("✓ Added receipt_image to solo_plans table")
            else:
                print("✓ receipt_image already exists in solo_plans table")
        else:
            print("✗ solo_plans table does not exist")


if __name__ == "__main__":
    migrate_receipt_image()
