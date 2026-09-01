"""
Fixed database.py - clean imports for membership features
"""

import os
import sqlite3
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
from wtforms.fields import DateTimeField, DecimalField
from wtforms.validators import (
    DataRequired,
    ValidationError,
    Email,
    EqualTo,
    Length,
    Regexp,
    Optional,
    NumberRange,
    DataRequired,
)

load_dotenv()

# Config

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def resolve_database_uri():
    env_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    preferred_local_uri = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

    if not env_uri:
        return preferred_local_uri

    if env_uri.startswith("sqlite"):
        return env_uri

    if env_uri.startswith("mysql") or env_uri.startswith("postgres"):
        try:
            engine = create_engine(env_uri)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return env_uri
        except Exception as exc:
            print(
                "Warning: configured SQLALCHEMY_DATABASE_URI is not reachable; "
                "falling back to local SQLite."
            )
            print(f"Database error: {exc}")
            return preferred_local_uri

    return env_uri


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-in-prod"
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")

    POSTS_PER_PAGE = 25


# Extensions

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
mail = Mail()


# ID Generator Helper Functions

def generate_membership_id():
    """Generate WS-WLK-XXXX sequential ID for members."""
    max_seq = db.session.query(func.max(func.cast(func.replace(User.membership_id, 'WS-WLK-', ''), db.Integer)))\
        .filter(User.membership_id.like('WS-WLK-%')).scalar() or 0
    seq = max_seq + 1
    return f"WS-WLK-{str(seq).zfill(4)}"


def generate_customer_id(room_type="common"):
    """
    Generate a customer-facing ID based on the type.
    - Common Area: 1-70
    - Other rooms and monthly passes: 100-999
    """
    if room_type.lower() == "common area":
        existing_ids = set([
            u.customer_id for u in User.query.filter(User.customer_id.between(1, 70)).all() if u.customer_id
        ] + [r.customer_id for r in Reservation.query.filter(Reservation.customer_id.between(1, 70)).all() if r.customer_id] + [
            s.customer_id for s in SoloPlan.query.filter(SoloPlan.customer_id.between(1, 70)).all() if s.customer_id
        ])
        for i in range(1, 71):
            if i not in existing_ids:
                return i
        raise ValueError("Common Area capacity reached")
    else:
        existing_ids = set([
            u.customer_id for u in User.query.filter(User.customer_id.between(100, 999)).all() if u.customer_id
        ] + [r.customer_id for r in Reservation.query.filter(Reservation.customer_id.between(100, 999)).all() if r.customer_id] + [
            s.customer_id for s in SoloPlan.query.filter(SoloPlan.customer_id.between(100, 999)).all() if s.customer_id
        ])
        for i in range(100, 1000):
            if i not in existing_ids:
                return i
        raise ValueError("ID range exhausted")


def get_common_area_count():
    return Reservation.query.filter(
        Reservation.customer_id.between(1, 70),
        Reservation.status.in_(["Confirmed", "Pending", "Walk-in"])
    ).count()


def get_user_by_email(email):
    """Resolve a user by email from the active database or the local SQLite fallback."""
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return None

    user = User.query.filter(func.lower(User.email) == normalized_email).first()
    if user:
        return user

    sqlite_db_path = os.path.join(BASE_DIR, "app.db")
    if not os.path.exists(sqlite_db_path):
        return None

    try:
        active_db_name = getattr(db.engine.url, "database", None)
    except Exception:
        active_db_name = None

    if active_db_name and os.path.abspath(sqlite_db_path) == os.path.abspath(active_db_name):
        return None

    try:
        conn = sqlite3.connect(sqlite_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, email, phone, password, role, is_active FROM users WHERE lower(email)=?",
            (normalized_email,),
        )
        row = cur.fetchone()
        conn.close()
    except Exception:
        return None

    if not row:
        return None

    fallback_user = User.query.filter(func.lower(User.email) == normalized_email).first()
    if fallback_user:
        return fallback_user

    imported_user = User(
        name=row[0] or "Imported User",
        email=row[1],
        phone=row[2],
        password=row[3],
        role=row[4] or "member",
        is_active=(row[5] if row[5] is not None else True),
    )
    db.session.add(imported_user)
    db.session.commit()
    return imported_user


# Models

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, unique=True, nullable=True)
    membership_id = db.Column(db.String(20), unique=True, nullable=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255))
    role = db.Column(db.String(20), default="member")
    is_active = db.Column(db.Boolean, default=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship("Reservation", backref="user", lazy="dynamic", foreign_keys='Reservation.user_id')
    approved_reservations = db.relationship("Reservation", foreign_keys='Reservation.approved_by_id', backref='approved_by')
    solo_plans = db.relationship(
        "SoloPlan",
        backref="user",
        lazy="dynamic",
        foreign_keys='SoloPlan.user_id',
    )
    time_logs = db.relationship("TimeLog", backref="user", lazy="dynamic")
    membership = db.relationship("Membership", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not self.password:
            return False

        if not isinstance(self.password, str):
            return False

        if password is None:
            return False

        if self.password.startswith(("scrypt:", "pbkdf2:", "bcrypt:", "argon2")):
            return check_password_hash(self.password, password)

        if self.password == password:
            return True

        if self.password == password.strip():
            return True

        return False

    @property
    def total_mins(self):
        total = db.session.query(func.coalesce(func.sum(TimeLog.total_time), 0)).filter(TimeLog.user_id == self.id).scalar()
        return total or 0

    @property
    def total_hours(self):
        return self.total_mins // 60

    @property
    def total_minutes(self):
        return self.total_mins % 60

    @property
    def membership_display_id(self):
        return self.membership_id or f"WS-WLK-{str(self.id).zfill(4)}"

    @property
    def is_membership_active(self):
        if not self.expiry_date:
            return self.is_active
        return self.is_active and datetime.now() < self.expiry_date

    @property
    def total_timelogged(self):
        total = db.session.query(func.sum(TimeLog.total_time)).filter(TimeLog.user_id == self.id).scalar()
        return total or 0

    def __repr__(self):
        return f"<User {self.name}>"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    base_rate = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default="standard")
    status = db.Column(db.String(20), default="available")

    reservations = db.relationship(
        "Reservation", 
        backref="room", 
        lazy="dynamic", 
        cascade="all, delete-orphan"
    )

    def is_currently_occupied(self):
        # Adjusted to Philippine Standard Time (+8 Hours)
        now = datetime.utcnow() + timedelta(hours=8)
        
        active_res = Reservation.query.filter(
            Reservation.room_id == self.id,
            Reservation.status.in_(["Confirmed", "Pending", "Walk-in"]),
            Reservation.start_time <= now,
            or_(Reservation.end_time >= now, Reservation.is_open_time == True),
        ).first()
        return active_res is not None

    def __repr__(self):
        return f"<Room {self.name}>"


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    # FIX: Gin-dula ang unique=True kay ang isa ka customer pwede maka-obra sang madamo nga reservations
    customer_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    customer_name = db.Column(db.String(64))
    contact_number = db.Column(db.String(20))
    address = db.Column(db.String(128))
    pax_count = db.Column(db.Integer, default=1)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    is_open_time = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Pending")
    total_amount = db.Column(db.Float, default=0.0)
    
    # Payment verification fields (online reservations)
    amount_paid = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50))
    payment_type = db.Column(db.String(20), default="Downpayment")
    receipt_image = db.Column(db.String(255))
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    paid = db.Column(db.Boolean, default=False)
    added_by = db.Column(db.String(64))
    extra_notes = db.Column(db.String(255))
    extra_fee = db.Column(db.Float, default=0.0)
    addon_subtotal = db.Column(db.Float, default=0.0)
    discount_rate = db.Column(db.Float, default=0.0)
    
    # FIX: PH Timezone (+8 hours)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))

    reservation_addons = db.relationship(
        "ReservationAddOn",
        backref="reservation",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    walkin = db.relationship(
        "WalkinReservation",
        backref="reservation",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @staticmethod
    def check_conflict(room_id, start_dt, end_dt, exclude_id=None):
        query = Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.status.in_(["Confirmed", "Pending", "Walk-in"]),
        )

        if exclude_id:
            query = query.filter(Reservation.id != exclude_id)

        if end_dt is None:
            query = query.filter(or_(Reservation.end_time > start_dt, Reservation.is_open_time == True))
        else:
            query = query.filter(or_(
                and_(
                    Reservation.is_open_time == False,
                    Reservation.start_time < end_dt,
                    Reservation.end_time > start_dt,
                ),
                and_(
                    Reservation.is_open_time == True,
                    Reservation.start_time < end_dt,
                ),
            ))

        return query.first()

    def __repr__(self):
        return f"<Reservation {self.id}>"


class PaymentInfo(db.Model):
    __tablename__ = "payment_info"

    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(32), unique=True, nullable=False)
    account_name = db.Column(db.String(128))
    account_number = db.Column(db.String(64))
    qr_image = db.Column(db.String(255))
    instructions = db.Column(db.String(255))
    
    # FIX: PH Timezone (+8 hours)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8), 
        onupdate=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    def __repr__(self):
        return f"<PaymentInfo {self.method}>"


class WalkinReservation(db.Model):
    __tablename__ = "walkin_reservations"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    customer_name = db.Column(db.String(64))
    contact_number = db.Column(db.String(20))
    pax_count = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="Walk-in")
    total_amount = db.Column(db.Float, default=0.0)
    paid = db.Column(db.Boolean, default=False)
    extra_fee = db.Column(db.Float, default=0.0)
    addon_subtotal = db.Column(db.Float, default=0.0)
    added_by = db.Column(db.String(64))
    extra_notes = db.Column(db.String(255))
    
    # FIX: Philippine Standard Time (+8 hours)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))

    walkin_addons = db.relationship(
        "WalkinAddOn",
        backref="walkin_reservation",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<WalkinReservation {self.id} -- Res {self.reservation_id}>"


class SoloPlan(db.Model):
    __tablename__ = "solo_plans"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=True) 
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    plan_name = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    payment_method = db.Column(db.String(50))
    receipt_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    expiry_date = db.Column(db.DateTime)

    approved_by_user = db.relationship(
        "User",
        foreign_keys=[approved_by_id],
        backref="approved_solo_plans",
    )

    @property
    def is_active(self):
        # Kon nag-check out na o expired na ang status, HINDI na active!
        if self.status and self.status.lower() in ["checked_out", "checked-out", "completed", "expired"]:
            return False

        # Align sa Philippine Time (+8 hours)
        now_ph = datetime.utcnow() + timedelta(hours=8)
        if self.expiry_date:
            return now_ph < self.expiry_date
        return self.status.lower() in ["approved", "active"]

    def set_expiry_date(self, start_time=None):
        durations = {
            "INDIVIDUAL RATE": timedelta(hours=1),
            "INDIVIDUAL RATE (4HRS)": timedelta(hours=4),
            "DAY/NIGHT PASS": timedelta(days=1),
            "WEEKLY PASS (DAY/NIGHT)": timedelta(days=7),
            "WEEKLY PASS (24HRS)": timedelta(days=7),
            "MONTHLY PASS (DAY/NIGHT)": timedelta(days=30),
            "MONTHLY PASS (24HRS)": timedelta(days=30),
            "WORKSTATION (24HRS)": timedelta(days=30),
            "ACTIVE PLAN": timedelta(days=30),
        }
        
        # FIX 1: Kon wala ginhatag nga start_time, mag-gamit sang SUBONG nga oras sang approval (PH Time)
        now_ph = datetime.utcnow() + timedelta(hours=8)
        start = start_time if start_time is not None else now_ph
        
        # FIX 2: Case-insensitive lookup para indi mag-fallback sa 30 days kon iba ang capitalizations
        clean_plan_name = (self.plan_name or "").strip().upper()
        duration = durations.get(clean_plan_name, timedelta(days=30))
        
        self.expiry_date = start + duration

    def __repr__(self):
        return f"<SoloPlan {self.plan_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'plan_name': self.plan_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_active': self.is_active
        }

    def check_out(self):
        self.status = "checked_out"

class TimeLog(db.Model):
    __tablename__ = "time_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan = db.Column(db.String(64))
    
    # FIX: Dynamic Philippine Standard Time (+8 Hours)
    time_in = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    time_out = db.Column(db.DateTime, nullable=True)
    total_time = db.Column(db.Integer, default=0)  # Total in minutes

    def calculate_total_time(self):
        """Helper method para mag-compute sang total minutes upon check-out."""
        if self.time_in and self.time_out:
            delta = self.time_out - self.time_in
            self.total_time = int(delta.total_seconds() // 60)
            return self.total_time
        return 0

    def __repr__(self):
        return f"<TimeLog {self.id} - User {self.user_id}>"


class DailyReport(db.Model):
    __tablename__ = "daily_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, unique=True)
    total_check_ins = db.Column(db.Integer, default=0)
    total_logins = db.Column(db.Integer, default=0)
    total_timelogged = db.Column(db.Float, default=0)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))

class UserActivityLog(db.Model):
    __tablename__ = "user_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    # Foreign Key cascade o nullable handler
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activity_type = db.Column(db.String(50))
    
    activity_time = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    ip_address = db.Column(db.String(45))


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(db.Integer, primary_key=True)
    
    # ondelete="CASCADE" para indi mag-crash sa MySQL kon mag-deactivate/delete sang User
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True
    )
    
    status = db.Column(db.String(20), default="pending")  # pending, active, expired
    
    # Dynamic Philippine Standard Time (+8 Hours)
    start_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    expiry_date = db.Column(db.DateTime, nullable=False)
    total_hours = db.Column(db.Float, default=0.0)  # Total hours credited
    hours_left = db.Column(db.Float, default=0.0)  # Remaining hours
    plan_name = db.Column(db.String(100))  # Solo plan name
    is_checked_in = db.Column(db.Boolean, default=False)  # Current session status
    is_checked_out = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8), 
        onupdate=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    user = db.relationship("User", back_populates="membership", uselist=False)
    attendance_logs = db.relationship(
        "AttendanceLog", 
        backref="membership", 
        lazy="dynamic", 
        cascade="all, delete-orphan"
    )

    @property
    def is_active(self):
        """Check if membership is active based on expiry_date (PH Timezone Alignment)"""
        now_ph = datetime.utcnow() + timedelta(hours=8)
        return self.status == "active" and now_ph < self.expiry_date

    @property
    def accumulated_hours(self):
        """Calculate total hours used from all completed attendance logs"""
        logs = self.attendance_logs.filter(AttendanceLog.check_out_time.isnot(None)).all()
        total = sum(log.hours_deducted for log in logs if log.hours_deducted)
        return round(total, 2)

    def __repr__(self):
        return f"<Membership {self.user_id} - {self.status}>"

class AttendanceLog(db.Model):
    __tablename__ = "attendance_logs"

    id = db.Column(db.Integer, primary_key=True)
    
    # Gindugang ang ondelete="CASCADE" para sa safe deletions/cleanup
    membership_id = db.Column(
        db.Integer, 
        db.ForeignKey("memberships.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    check_in_time = db.Column(db.DateTime, nullable=False)
    check_out_time = db.Column(db.DateTime)
    hours_deducted = db.Column(db.Float, default=0.0)  # Calculated on check-out
    
    # Dynamic Philippine Standard Time (+8 Hours)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))

    @property
    def session_duration_hours(self):
        """Calculate duration in hours between check-in and check-out"""
        if self.check_out_time and self.check_in_time:
            delta = self.check_out_time - self.check_in_time
            return delta.total_seconds() / 3600  # Convert seconds to hours
        return 0.0

    def __repr__(self):
        return f"<AttendanceLog {self.membership_id} - {self.check_in_time}>"


class AddOn(db.Model):
    """
    Master list of available add-ons for reservations.
    Defines the name, unit price, and availability.
    """
    __tablename__ = "addons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.String(255))
    unit_price = db.Column(db.Float, nullable=False)
    requires_quantity = db.Column(db.Boolean, default=True)  # Whether quantity input is needed
    min_quantity = db.Column(db.Integer, default=1)
    max_quantity = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=True)
    
    # Philippine Standard Time (+8 hours)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8)
    )
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8), 
        onupdate=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    # Relationships (GINKAKAS ANG CASCADE/DELETE-ORPHAN PARA PROTEKTADO ANG HISTORY)
    reservation_addons = db.relationship(
        "ReservationAddOn",
        backref="addon",
        lazy="dynamic",
    )
    walkin_addons = db.relationship(
        "WalkinAddOn",
        backref="addon",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<AddOn {self.name} - ₱{self.unit_price}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'unit_price': float(self.unit_price),
            'requires_quantity': self.requires_quantity,
            'min_quantity': self.min_quantity,
            'max_quantity': self.max_quantity,
        }


class ReservationAddOn(db.Model):
    """
    Tracks selected add-ons for a specific reservation.
    Stores quantity, unit price, and subtotal for each add-on.
    """
    __tablename__ = "reservation_addons"

    id = db.Column(db.Integer, primary_key=True)
    
    # Kon i-delete ang Reservation mismo, ma-delete ang kabilugan nga reservation line item
    reservation_id = db.Column(
        db.Integer, 
        db.ForeignKey("reservations.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # PROTECTED: RESTRICT para indi ma-erase ang financial history o resibo
    addon_id = db.Column(
        db.Integer, 
        db.ForeignKey("addons.id", ondelete="RESTRICT"), 
        nullable=False
    )
    
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)  # Price at time of booking
    subtotal = db.Column(db.Float, default=0.0)  # quantity * unit_price
    
    # Philippine Standard Time (+8 Hours)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    def __repr__(self):
        return f"<ReservationAddOn {self.addon_id} qty={self.quantity}>"

    def calculate_subtotal(self):
        """Calculate subtotal: quantity * unit_price"""
        self.subtotal = self.quantity * self.unit_price
        return self.subtotal

    def to_dict(self):
        return {
            'id': self.id,
            'addon_id': self.addon_id,
            'addon_name': self.addon.name if self.addon else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'subtotal': float(self.subtotal),
        }

class WalkinAddOn(db.Model):
    """
    Tracks selected add-ons for a specific walk-in reservation.
    Stores quantity, unit price, and subtotal for each add-on.
    """
    __tablename__ = "walkin_addons"

    id = db.Column(db.Integer, primary_key=True)
    
    # Kon ma-delete ang walk-in record mismo, ma-delete ang line items sini
    walkin_reservation_id = db.Column(
        db.Integer, 
        db.ForeignKey("walkin_reservations.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # PROTECTED: RESTRICT para indi ma-delete ang Master AddOn kon may history record na
    addon_id = db.Column(
        db.Integer, 
        db.ForeignKey("addons.id", ondelete="RESTRICT"), 
        nullable=False
    )
    
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)  # Price at time of booking
    subtotal = db.Column(db.Float, default=0.0)  # quantity * unit_price
    
    # Philippine Standard Time (+8 Hours)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    def __repr__(self):
        return f"<WalkinAddOn {self.addon_id} qty={self.quantity}>"

    def calculate_subtotal(self):
        """Calculate subtotal: quantity * unit_price"""
        self.subtotal = self.quantity * self.unit_price
        return self.subtotal

    def to_dict(self):
        return {
            'id': self.id,
            'addon_id': self.addon_id,
            'addon_name': self.addon.name if self.addon else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'subtotal': float(self.subtotal),
        }


# Forms

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Length(max=20)])
    
    # ADDED: Length (min=8) & Regexp for Alphanumeric Password
    password = PasswordField(
        "Password", 
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long."),
            Regexp(
                r'^(?=.*[A-Za-z])(?=.*\d).+$',
                message="Password must contain at least one letter and one number."
            )
        ]
    )
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    submit = SubmitField("Register")


class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=64)])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    phone = StringField("Contact Number", validators=[Length(max=20)])
    profile_submit = SubmitField("Save Profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    
    # ADDED: Regexp for Alphanumeric Password
    new_password = PasswordField(
        "New Password", 
        validators=[
            DataRequired(), 
            Length(min=8, message="Password must be at least 8 characters long."),
            Regexp(
                r'^(?=.*[A-Za-z])(?=.*\d).+$',
                message="Password must contain at least one letter and one number."
            )
        ]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )
    password_submit = SubmitField("Change Password")


class ReservationForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    customer_name = StringField("Customer Name", validators=[DataRequired(), Length(min=2)])
    contact_number = StringField("Contact", validators=[DataRequired()])
    pax_count = IntegerField("Pax Count", default=1, validators=[NumberRange(min=1)])
    start_time = DateTimeField("Start Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_time = DateTimeField("End Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    # Support open-time toggle on client reservation form (template expects `is_open_time`)
    is_open_time = BooleanField("Open Time")
    extra_notes = TextAreaField("Notes")
    # Payment fields expected by client-side booking flow
    payment_method = SelectField("Payment Method", choices=[("GCash", "GCash"), ("Maya", "Maya")], validators=[Optional()])
    payment_type = SelectField("Payment Type", choices=[("Downpayment", "Downpayment"), ("Full Payment", "Full Payment")], default="Downpayment", validators=[Optional()])
    submit = SubmitField("Reserve")


class AdminReservationForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    customer_name = StringField("Customer Name", validators=[DataRequired(), Length(min=2)])
    contact_number = StringField("Contact", validators=[Optional()])
    pax_count = IntegerField("Pax Count", default=1, validators=[NumberRange(min=1)])
    start_time = DateTimeField("Start Date/Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_time = DateTimeField("End Date/Time", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    extra_fee = DecimalField("Extra Fee (₱)", default=0.00, validators=[Optional()])
    addon_subtotal = HiddenField("Add-on Subtotal", default="0.00")
    addons_json = HiddenField("Add-ons JSON")  # JSON string with selected add-ons
    total_price = HiddenField("Total Price")
    open_time = BooleanField("Open Time")
    discount = SelectField("Discount", choices=[(str(i / 100), f"{i}%") for i in range(0, 101, 5)], default="0.0")
    payment_method = SelectField("Payment Method", choices=[("Cash", "Cash"), ("GCash", "GCash"), ("Bank Transfer", "Bank Transfer")], default="Cash")
    extra_notes = TextAreaField("Notes")
    submit = SubmitField("Reserve")


class WalkinForm(FlaskForm):
    customer_name = StringField("Customer Name", validators=[DataRequired()])
    contact_number = StringField("Contact Number", validators=[Optional()])
    room_id = SelectField("Select Area", coerce=int, validators=[DataRequired()])
    pax_count = IntegerField("No. of Pax", default=1)
    start_time = DateTimeField("Start Time", format='%Y-%m-%dT%H:%M', validators=[Optional()])
    end_time = DateTimeField("End Time", format='%Y-%m-%dT%H:%M', validators=[Optional()])
    extra_notes = TextAreaField("Staff Notes")
    extra_fee = DecimalField("Additional Fees", default=0.0)
    addon_subtotal = HiddenField("Add-on Subtotal", default="0.00")
    addons_json = HiddenField("Add-ons JSON")  # JSON string with selected add-ons
    open_time = BooleanField("Open Time")
    discount = SelectField("Discount", choices=[(str(i / 100), f"{i}%") for i in range(0, 101, 5)], default="0.0")
    payment_method = SelectField("Payment Method", choices=[("Cash", "Cash"), ("GCash", "GCash"), ("Bank Transfer", "Bank Transfer")], default="Cash")
    total_price = HiddenField("Total Price")
    submit = SubmitField("Save Walk-in")

