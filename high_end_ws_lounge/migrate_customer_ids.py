"""
Database Migration Script
Adds customer_id columns to existing tables and backfills data.
"""

import os
import sys

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Reservation, SoloPlan, User, db
from run import app
from sqlalchemy import inspect, text


def migrate_customer_ids():
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Add customer_id to users table if not exists
        if inspector.has_table("users"):
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "customer_id" not in columns:
                print("Adding customer_id to users table...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN customer_id INTEGER UNIQUE"))
                db.session.commit()
                print("✓ Added customer_id to users table")
            else:
                print("✓ customer_id already exists in users table")
        
        # Add customer_id to reservations table if not exists
        if inspector.has_table("reservations"):
            columns = [col["name"] for col in inspector.get_columns("reservations")]
            if "customer_id" not in columns:
                print("Adding customer_id to reservations table...")
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN customer_id INTEGER UNIQUE"))
                db.session.commit()
                print("✓ Added customer_id to reservations table")
            else:
                print("✓ customer_id already exists in reservations table")
        
        # Add customer_id to solo_plans table if not exists
        if inspector.has_table("solo_plans"):
            columns = [col["name"] for col in inspector.get_columns("solo_plans")]
            if "customer_id" not in columns:
                print("Adding customer_id to solo_plans table...")
                db.session.execute(text("ALTER TABLE solo_plans ADD COLUMN customer_id INTEGER UNIQUE"))
                db.session.commit()
                print("✓ Added customer_id to solo_plans table")
            else:
                print("✓ customer_id already exists in solo_plans table")
        
        # Backfill existing reservations with customer_ids
        print("\nBackfilling customer_ids for existing records...")
        
        # Import the generator here to avoid circular import
        from database import generate_customer_id

        # Backfill reservations
        reservations_without_id = Reservation.query.filter(Reservation.customer_id.is_(None)).all()
        for res in reservations_without_id:
            try:
                room_type = "common area" if res.room and res.room.name.strip().lower() == "common area" else "other"
                res.customer_id = generate_customer_id(room_type)
                db.session.add(res)
                print(f"  Assigned ID {res.customer_id} to Reservation {res.id}")
            except ValueError as e:
                print(f"  Warning: Could not assign ID to Reservation {res.id}: {e}")
        
        db.session.commit()
        
        # Backfill solo plans
        plans_without_id = SoloPlan.query.filter(SoloPlan.customer_id.is_(None)).all()
        for plan in plans_without_id:
            try:
                plan.customer_id = generate_customer_id("monthly")
                db.session.add(plan)
                print(f"  Assigned ID {plan.customer_id} to SoloPlan {plan.id}")
            except ValueError as e:
                print(f"  Warning: Could not assign ID to SoloPlan {plan.id}: {e}")
        
        db.session.commit()
        
        # Backfill users
        users_without_id = User.query.filter(User.customer_id.is_(None)).all()
        for user in users_without_id:
            try:
                user.customer_id = generate_customer_id("other")
                db.session.add(user)
                print(f"  Assigned ID {user.customer_id} to User {user.id}")
            except ValueError as e:
                print(f"  Warning: Could not assign ID to User {user.id}: {e}")
        
        db.session.commit()
        
        print("\n✓ Migration complete!")
        print(f"  - Updated {len(reservations_without_id)} reservations")
        print(f"  - Updated {len(plans_without_id)} solo plans")
        print(f"  - Updated {len(users_without_id)} users")


if __name__ == "__main__":
    migrate_customer_ids()
