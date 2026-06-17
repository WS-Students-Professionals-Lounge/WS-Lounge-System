"""
database.py
Contains: Config, Flask extensions, all SQLAlchemy models, and all WTForms.
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
from wtforms import BooleanField, DateField, DateTimeField, DecimalField, HiddenField, IntegerField, PasswordField, \
    SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-in-prod"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")

    POSTS_PER_PAGE = 25


# ---------------------------------------------------------------------------
# Extensions (initialized in run.py via init_app)
# ---------------------------------------------------------------------------
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
mail = Mail()


# ---------------------------------------------------------------------------
# ID Generator Helper Functions
# ---------------------------------------------------------------------------
def generate_customer_id(room_type="common"):
    """
    Generate a customer-facing ID based on the type.
    - Common Area: 1-50
    - Other rooms and monthly passes: 100-999
    """
    if room_type.lower() == "common area":
        # Find next available ID in range 1-50
        existing_ids = set()
        existing_ids.update(
            [u.customer_id for u in User.query.filter(User.customer_id.between(1, 50)).all() if u.customer_id]
        )
        existing_ids.update(
            [r.customer_id for r in Reservation.query.filter(Reservation.customer_id.between(1, 50)).all() if r.customer_id]
        )
        existing_ids.update(
            [s.customer_id for s in SoloPlan.query.filter(SoloPlan.customer_id.between(1, 50)).all() if s.customer_id]
        )

        for i in range(1, 51):
            if i not in existing_ids:
                return i
        raise ValueError("Common Area has reached maximum capacity of 50 people")
    else:
        # Find next available ID in range 100-999
        existing_ids = set()
        existing_ids.update(
            [u.customer_id for u in User.query.filter(User.customer_id.between(100, 999)).all() if u.customer_id]
        )
        existing_ids.update(
            [r.customer_id for r in Reservation.query.filter(Reservation.customer_id.between(100, 999)).all() if r.customer_id]
        )
        existing_ids.update(
            [s.customer_id for s in SoloPlan.query.filter(SoloPlan.customer_id.between(100, 999)).all() if s.customer_id]
        )

        for i in range(100, 1000):
            if i not in existing_ids:
                return i
        raise ValueError("ID range 100-999 is exhausted")


def get_common_area_count():
    """Get the current count of active Common Area users.

    This counts active Common Area reservations and active membership check-ins
    so capacity reflects actual occupancy instead of reserved or historical IDs.
    """
    now = datetime.now()

    active_reservations = Reservation.query.join(Room).filter(
        Room.name.ilike("common area"),
        Reservation.status.in_(["Confirmed", "Walk-in"]),
        or_(
            and_(Reservation.is_open_time == True, Reservation.start_time <= now),
            and_(
                Reservation.is_open_time == False,
                Reservation.start_time <= now,
                Reservation.end_time > now,
            ),
        ),
    ).count()

    membership_checkins = Membership.query.filter(
        Membership.is_checked_in == True,
        Membership.status == "active",
    ).count()

    return active_reservations + membership_checkins


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, unique=True, nullable=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255))
    role = db.Column(db.String(20), default="member")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship(
        "Reservation",
        backref="user",
        lazy="dynamic",
        foreign_keys="Reservation.user_id",
    )
    approved_reservations = db.relationship(
        "Reservation",
        foreign_keys="Reservation.approved_by_id",
        backref="approved_by",
    )
    solo_plans = db.relationship(
        "SoloPlan",
        backref="user",
        lazy="dynamic",
        foreign_keys="SoloPlan.user_id",
    )
    approved_solo_plans = db.relationship(
        "SoloPlan",
        foreign_keys="SoloPlan.approved_by_id",
        backref="approved_by_user",
        lazy="dynamic",
    )
    time_logs = db.relationship("TimeLog", backref="user", lazy="dynamic")
    activity_logs = db.relationship("UserActivityLog", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @property
    def total_timelogged(self):
        total = (
            db.session.query(func.sum(TimeLog.total_time))
            .filter(TimeLog.user_id == self.id)
            .scalar()
        )
        return total or 0

    @property
    def latest_deactivation_log(self):
        return (
            self.activity_logs
            .filter(UserActivityLog.activity_type.ilike("deactivated%"))
            .order_by(UserActivityLog.activity_time.desc())
            .first()
        )

    @property
    def last_deactivated_at(self):
        log = self.latest_deactivation_log
        return log.activity_time if log else None

    @property
    def last_deactivation_reason(self):
        log = self.latest_deactivation_log
        if not log:
            return None
        if "|" in log.activity_type:
            return log.activity_type.split("|", 1)[1]
        return log.activity_type

    def __repr__(self):
        return f"<User {self.name}>"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    base_rate = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default="standard")
    status = db.Column(db.String(20), default="available")

    reservations = db.relationship("Reservation", backref="room", lazy="dynamic")

    def is_currently_occupied(self):
        now = datetime.utcnow()
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
    customer_id = db.Column(db.Integer, unique=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
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
    amount_paid = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50))
    receipt_image = db.Column(db.String(255))
    paid = db.Column(db.Boolean, default=False)
    added_by = db.Column(db.String(64))
    extra_notes = db.Column(db.String(255))
    extra_fee = db.Column(db.Float, default=0.0)
    discount_rate = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    walkin = db.relationship(
        "WalkinReservation",
        backref="reservation",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    approved_by = db.relationship(
        "User",
        foreign_keys=[approved_by_id],
        backref="approved_reservations",
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
            query = query.filter(
                or_(Reservation.end_time > start_dt, Reservation.is_open_time == True)
            )
        else:
            query = query.filter(
                or_(
                    and_(
                        Reservation.is_open_time == False,
                        Reservation.start_time < end_dt,
                        Reservation.end_time > start_dt,
                    ),
                    and_(
                        Reservation.is_open_time == True,
                        Reservation.start_time < end_dt,
                    ),
                )
            )

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PaymentInfo {self.method}>"


class WalkinReservation(db.Model):
    __tablename__ = "walkin_reservations"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer, db.ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False
    )
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
    added_by = db.Column(db.String(64))
    extra_notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WalkinReservation {self.id} -- Res {self.reservation_id}>"


class SoloPlan(db.Model):
    __tablename__ = "solo_plans"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, unique=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    plan_name = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    payment_method = db.Column(db.String(50))
    receipt_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)

    @property
    def is_active(self):
        if self.expiry_date:
            return datetime.now() < self.expiry_date
        return self.status.lower() == "approved"

    def set_expiry_date(self):
        durations = {
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
        self.expiry_date = self.created_at + durations.get(
            self.plan_name, timedelta(days=30)
        )

    def __repr__(self):
        return f"<SoloPlan {self.plan_name}>"


class TimeLog(db.Model):
    __tablename__ = "time_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan = db.Column(db.String(64))
    time_in = db.Column(db.DateTime, default=datetime.utcnow)
    time_out = db.Column(db.DateTime)
    total_time = db.Column(db.Integer)  # minutes

    def __repr__(self):
        return f"<TimeLog {self.id} - User {self.user_id}>"


class DailyReport(db.Model):
    __tablename__ = "daily_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, unique=True)
    total_check_ins = db.Column(db.Integer, default=0)
    total_logins = db.Column(db.Integer, default=0)
    total_timelogged = db.Column(db.Float, default=0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserActivityLog(db.Model):
    __tablename__ = "user_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    activity_type = db.Column(db.String(50))
    activity_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    status = db.Column(db.String(20), default="pending")  # pending, active, expired
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=False)
    total_hours = db.Column(db.Float, default=0.0)  # Total hours credited
    hours_left = db.Column(db.Float, default=0.0)  # Remaining hours
    plan_name = db.Column(db.String(100))  # Solo plan name
    is_checked_in = db.Column(db.Boolean, default=False)  # Current session status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="membership", uselist=False)
    attendance_logs = db.relationship("AttendanceLog", backref="membership", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self):
        """Check if membership is active based on expiry_date"""
        return self.status == "active" and datetime.utcnow() < self.expiry_date

    def __repr__(self):
        return f"<Membership {self.user_id} - {self.status}>"


class AttendanceLog(db.Model):
    __tablename__ = "attendance_logs"

    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, db.ForeignKey("memberships.id"), nullable=False)
    check_in_time = db.Column(db.DateTime, nullable=False)
    check_out_time = db.Column(db.DateTime)
    hours_deducted = db.Column(db.Float, default=0.0)  # Calculated on check-out
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def session_duration_hours(self):
        """Calculate duration in hours between check-in and check-out"""
        if self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return delta.total_seconds() / 3600  # Convert seconds to hours
        return 0.0

    def __repr__(self):
        return f"<AttendanceLog {self.membership_id} - {self.check_in_time}>"


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    name = StringField(
        "Name", validators=[DataRequired(), Length(min=2, max=64)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class ReservationForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    customer_name = StringField(
        "Customer Name", validators=[DataRequired(), Length(min=2)]
    )
    contact_number = StringField("Contact", validators=[DataRequired()])
    pax_count = IntegerField(
        "Pax Count", default=1, validators=[NumberRange(min=1)]
    )
    start_time = DateTimeField(
        "Start Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_time = DateTimeField(
        "End Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    is_open_time = BooleanField("Open Time")
    extra_notes = TextAreaField("Notes")
    submit = SubmitField("Reserve")


class AdminReservationForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    customer_name = StringField(
        "Customer Name", validators=[DataRequired(), Length(min=2)]
    )
    contact_number = StringField("Contact", validators=[Optional()])
    pax_count = IntegerField(
        "Pax Count", default=1, validators=[NumberRange(min=1)]
    )
    start_time = DateTimeField(
        "Start Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    end_time = DateTimeField(
        "End Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    extra_fee = DecimalField(
        "Extra Fee (₱)", default=0.00, validators=[Optional()]
    )
    total_price = HiddenField("Total Price")
    open_time = BooleanField("Open Time")
    discount = SelectField(
        "Discount",
        choices=[(str(i / 100), f"{i}%") for i in range(0, 101, 5)],
        default="0.0",
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[("Cash", "Cash"), ("GCash", "GCash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    extra_notes = TextAreaField("Notes")
    submit = SubmitField("Reserve")


class WalkinForm(FlaskForm):
    customer_name = StringField("Customer Name", validators=[DataRequired()])
    contact_number = StringField("Contact Number", validators=[Optional()])
    room_id = SelectField(
        "Select Area", coerce=int, validators=[DataRequired()]
    )
    pax_count = IntegerField("No. of Pax", default=1)
    start_time = DateTimeField(
        "Start Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    end_time = DateTimeField(
        "End Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    extra_notes = TextAreaField("Staff Notes")
    extra_fee = DecimalField("Additional Fees", default=0.0)
    open_time = BooleanField("Open Time")
    discount = SelectField(
        "Discount",
        choices=[(str(i / 100), f"{i}%") for i in range(0, 101, 5)],
        default="0.0",
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[("Cash", "Cash"), ("GCash", "GCash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    total_price = HiddenField("Total Price")
    submit = SubmitField("Save Walk-in")