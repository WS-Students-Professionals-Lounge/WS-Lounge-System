"""
run.py
App factory, CLI commands, and entry point.
"""

import os
from datetime import datetime, timedelta

from database_fixed import (
    Config,
    DailyReport,
    PaymentInfo,
    Reservation,
    Room,
    SoloPlan,
    TimeLog,
    User,
    db,
    login_manager,
    mail,
    socketio,
)
from flask import Flask
from sqlalchemy import inspect, text
from time_utils import format_checkin_time, format_checkout_time, format_date, decimal_hours_to_readable


def create_app(config_class=Config):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, "app", "templates"),
        static_folder=os.path.join(root_dir, "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Login required"
    socketio.init_app(app)
    mail.init_app(app)

    # Register Jinja2 filters for time formatting
    app.jinja_env.filters['format_checkin'] = format_checkin_time
    app.jinja_env.filters['format_checkout'] = format_checkout_time
    app.jinja_env.filters['format_date_time'] = format_date
    app.jinja_env.filters['format_hours'] = decimal_hours_to_readable

    with app.app_context():
        db.create_all()

    def ensure_default_rooms():
        with app.app_context():
            default_rooms = [
                {"name": "Small Meeting Room", "base_rate": 50.0, "category": "meeting"},
                {"name": "Lecture Room", "base_rate": 150.0, "category": "lecture"},
                {"name": "Conference Room", "base_rate": 250.0, "category": "conference"},
                {"name": "Comfy Room", "base_rate": 150.0, "category": "comfy"},
                {"name": "Event Room 1", "base_rate": 300.0, "category": "event"},
                {"name": "Event Room 2", "base_rate": 300.0, "category": "event"},
                {"name": "Common Area", "base_rate": 35.0, "category": "solo"},
            ]
            for room_data in default_rooms:
                if not Room.query.filter_by(name=room_data["name"]).first():
                    db.session.add(
                        Room(
                            name=room_data["name"],
                            base_rate=room_data["base_rate"],
                            category=room_data["category"],
                        )
                    )
            db.session.commit()

    def cleanup_test_rooms():
        with app.app_context():
            test_rooms = Room.query.filter(Room.name.ilike('test room%')).all()
            for room in test_rooms:
                has_reservation = Reservation.query.filter_by(room_id=room.id).first()
                if not has_reservation:
                    db.session.delete(room)
            db.session.commit()

    def ensure_payment_columns():
        with app.app_context():
            inspector = inspect(db.engine)
            if not inspector.has_table("reservations"):
                return
            columns = {column["name"] for column in inspector.get_columns("reservations")}
            if "payment_method" not in columns:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN payment_method VARCHAR(50)"))
            if "payment_type" not in columns:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN payment_type VARCHAR(20) DEFAULT 'Downpayment'"))
            if "amount_paid" not in columns:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN amount_paid FLOAT DEFAULT 0.0"))
            if "receipt_image" not in columns:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN receipt_image VARCHAR(255)"))
            if "approved_by_id" not in columns:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN approved_by_id INTEGER"))

            if inspector.has_table("solo_plans"):
                solo_columns = {column["name"] for column in inspector.get_columns("solo_plans")}
                if "approved_by_id" not in solo_columns:
                    db.session.execute(text("ALTER TABLE solo_plans ADD COLUMN approved_by_id INTEGER"))
                if "payment_method" not in solo_columns:
                    db.session.execute(text("ALTER TABLE solo_plans ADD COLUMN payment_method VARCHAR(50)"))
                if "receipt_image" not in solo_columns:
                    db.session.execute(text("ALTER TABLE solo_plans ADD COLUMN receipt_image VARCHAR(255)"))

            if inspector.has_table("users"):
                user_columns = {column["name"] for column in inspector.get_columns("users")}
                if "is_active" not in user_columns:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            db.session.commit()

    def ensure_membership_tables():
        """Ensure memberships and attendance_logs tables have all required columns"""
        with app.app_context():
            inspector = inspect(db.engine)
            
            # Ensure memberships table columns
            if inspector.has_table("memberships"):
                membership_columns = {column["name"] for column in inspector.get_columns("memberships")}
                if "is_checked_in" not in membership_columns:
                    db.session.execute(text("ALTER TABLE memberships ADD COLUMN is_checked_in BOOLEAN DEFAULT 0"))
                if "updated_at" not in membership_columns:
                    db.session.execute(text("ALTER TABLE memberships ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            
            db.session.commit()

    def ensure_default_admin():
        with app.app_context():
            if not User.query.filter_by(email="wslounge@lounge.com").first():
                admin = User(
                    name="wslounge",
                    email="wslounge@lounge.com",
                    role="admin",
                    phone="09171111111",
                )
                admin.set_password("ws12345")
                db.session.add(admin)
                db.session.commit()

    ensure_payment_columns()
    ensure_membership_tables()
    ensure_default_rooms()
    cleanup_test_rooms()
    ensure_default_admin()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from admin import admin_bp
    from client_fixed import api_bp, auth_bp, main_bp
    from membership_routes import membership_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(membership_bp)

    return app


app = create_app()


@app.cli.command()
def init_db():
    """Create database tables."""
    db.create_all()
    print("Tables created, including solo_plans")


@app.cli.command()
def seed_db():
    """Seed database with sample data."""

    # Rooms
    if not Room.query.first():
        rooms = [
            Room(name="Conference Room", base_rate=50.0, category="conference"),
            Room(name="Room 101", base_rate=35.0, category="standard"),
            Room(name="Room 102", base_rate=50.0, category="premium"),
            Room(name="Sleeping Pod", base_rate=100.0, category="pod"),
            Room("Common Area", base_rate=35.0, category="solo"),
        ]
        for room in rooms:
            db.session.add(room)
        db.session.commit()

    # Admin
    if not User.query.filter_by(email="wslounge@lounge.com").first():
        admin = User(
            name="wslounge",
            email="wslounge@lounge.com",
            role="admin",
            phone="09171111111",
        )
        admin.set_password("ws12345")
        db.session.add(admin)
        db.session.commit()

    # Members
    members = User.query.filter_by(role="member").all()
    if len(members) == 0:
        cedrick = User(
            name="cedrick",
            email="cedrick@lounge.com",
            role="member",
            phone="09171222222",
        )
        cedrick.set_password("member123")
        db.session.add(cedrick)
        db.session.commit()
        member1 = cedrick
    else:
        member1 = members[0]

    # Sample payment settings
    if not PaymentInfo.query.first():
        payment_settings = [
            PaymentInfo(
                method="GCash",
                account_name="High End WS Lounge",
                account_number="09171234567",
                instructions="Send 50% downpayment and upload the receipt.",
            ),
            PaymentInfo(
                method="Maya",
                account_name="High End WS Lounge",
                account_number="09179876543",
                instructions="Please upload the receipt after payment.",
            ),
        ]
        for setting in payment_settings:
            db.session.add(setting)
        db.session.commit()

    # Sample reservations
    if Reservation.query.count() == 0:
        res1 = Reservation(
            user_id=member1.id,
            room_id=1,
            customer_name="cedrick",
            contact_number=member1.phone,
            pax_count=6,
            start_time=datetime.now() + timedelta(hours=2),
            end_time=datetime.now() + timedelta(hours=4),
            status="Pending",
            total_amount=100.0,
            added_by="seed",
        )
        db.session.add(res1)
        db.session.commit()


@app.cli.command()
def migrate_payment_columns():
    """Add missing payment-related columns (safe, idempotent).

    Use this CLI command when you prefer an explicit migration step
    instead of relying on the runtime ensure function.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("reservations"):
            print("No reservations table found; nothing to migrate.")
            return
        columns = {col["name"] for col in inspector.get_columns("reservations")}
        added = False
        if "payment_type" not in columns:
            try:
                db.session.execute(text("ALTER TABLE reservations ADD COLUMN payment_type VARCHAR(20) DEFAULT 'Downpayment'"))
                db.session.commit()
                print("Added column: payment_type")
                added = True
            except Exception as e:
                db.session.rollback()
                print("Failed to add payment_type:", e)
        else:
            print("Column payment_type already exists")

        if not added:
            print("Migration finished; no changes applied or already up-to-date.")
        else:
            print("Migration finished; database updated.")

    # Backfill expiry for approved plans
    plan_durations = {
        "INDIVIDUAL RATE": timedelta(hours=1),
        "INDIVIDUAL RATE (4HRS)": timedelta(hours=4),
        "DAY/NIGHT PASS": timedelta(days=1),
        "WEEKLY PASS (DAY/NIGHT)": timedelta(days=7),
        "WEEKLY PASS (24HRS)": timedelta(days=7),
        "MONTHLY PASS (DAY/NIGHT)": timedelta(days=30),
        "MONTHLY PASS (24HRS)": timedelta(days=30),
        "WORKSTATION (24HRS)": timedelta(days=30),
        "Active Plan": timedelta(days=30),
    }
    approved_plans = SoloPlan.query.filter_by(status="approved").all()
    for plan in approved_plans:
        if plan.expiry_date is None:
            duration = plan_durations.get(plan.plan_name, timedelta(days=30))
            plan.expiry_date = plan.created_at + duration
            db.session.add(plan)
    db.session.commit()
    print(f"Backfilled expiry for {len(approved_plans)} approved plans")

    # Solo plans seed if none
    if SoloPlan.query.count() == 0:
        solo1 = SoloPlan(
            user_id=member1.id, plan_name="Active Plan", status="approved"
        )
        solo1.expiry_date = solo1.created_at + timedelta(days=30)
        db.session.add(solo1)
        db.session.commit()

    print(
        "Enhanced database seeded: Conference Room, cedrick, Active Plan with expiry, reservations!"
    )


if __name__ == "__main__":
    socketio.run(app, debug=True)
