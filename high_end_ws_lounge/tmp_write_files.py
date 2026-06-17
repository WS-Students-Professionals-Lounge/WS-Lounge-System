from pathlib import Path

TEST_FILE = Path(__file__).with_name('tests').joinpath('test_app.py')
CLIENT_FILE = Path(__file__).with_name('client_fixed.py')

TEST_CONTENT = '''import os
import sys
import uuid
from io import BytesIO

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_fixed import PaymentInfo, Room, User, db
from run import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        # db.drop_all()  # Skip cleanup to inspect test state if needed


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(app):
    with app.app_context():
        client = app.test_client()
        res = client.get('/')
        print(f"Index response status: {res.status_code}")
        assert res.status_code == 200


def test_login(app, client):
    with app.app_context():
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        user = User(name='test', email=email, role='member')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        res = client.post('/auth/login', data={'email': email, 'password': 'testpass'})
        print(f"Login response status: {res.status_code}")
        assert res.status_code == 302


def test_reservation(app, client):
    with app.app_context():
        member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"
        admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"

        member = User(name='member', email=member_email, role='member')
        member.set_password('memberpass')
        admin = User(name='admin', email=admin_email, role='admin')
        admin.set_password('adminpass')
        db.session.add(member)
        db.session.add(admin)

        payment_info = PaymentInfo.query.filter_by(method='GCash').first()
        if not payment_info:
            payment_info = PaymentInfo(method='GCash', account_name='Admin', account_number='09170000000', instructions='Pay and upload receipt')
            db.session.add(payment_info)

        room = Room(name='Conference Room', base_rate=50.0, status='available')
        db.session.add(room)
        db.session.commit()

        login_res = client.post('/auth/login', data={'email': member_email, 'password': 'memberpass'})
        assert login_res.status_code == 302

        reservation_data = {
            'room_id': str(room.id),
            'customer_name': 'Test Member',
            'contact_number': '09171234567',
            'pax_count': '2',
            'start_time': '2026-05-17T10:00',
            'end_time': '2026-05-17T12:00',
            'payment_method': 'GCash',
            'extra_notes': 'Feature test booking',
        }
        reservation_data['receipt_image'] = (BytesIO(b'testreceipt'), 'receipt.png')
        res = client.post('/rooms', data=reservation_data, content_type='multipart/form-data', follow_redirects=True)
        assert res.status_code == 200
        assert b'Awaiting admin approval' in res.data

        client.get('/auth/logout')
        login_res = client.post('/auth/login', data={'email': admin_email, 'password': 'adminpass'})
        assert login_res.status_code == 302

        payment_data = {
            'method': 'GCash',
            'account_name': 'New Admin',
            'account_number': '09170000001',
            'instructions': 'Please pay and upload receipt',
        }
        payment_data['qr_image'] = (BytesIO(b'qrdata'), 'qr.png')
        payment_res = client.post('/admin/payment_settings', data=payment_data, content_type='multipart/form-data', follow_redirects=True)
        assert payment_res.status_code == 200
        assert b'GCash payment settings updated.' in payment_res.data
'''

CLIENT_CONTENT = '''"""
client.py
Contains all client-facing blueprints: auth, main, and api.
"""

import os
from datetime import datetime, timedelta

from database_fixed import (
    AttendanceLog,
    LoginForm,
    Membership,
    PaymentInfo,
    RegistrationForm,
    Reservation,
    ReservationForm,
    Room,
    SoloPlan,
    TimeLog,
    User,
    db,
    generate_customer_id,
)
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename


auth_bp = Blueprint("auth", __name__)
api_bp = Blueprint("api", __name__)
main_bp = Blueprint("main", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        return redirect(url_for("main.index"))

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(password):
        flash("Please enter valid credentials and try again.", "danger")
        return redirect(url_for("main.index"))

    if not user.is_active:
        flash("Access Restricted: Account is inactive. Contact your administrator.", "danger")
        return redirect(url_for("main.index"))

    login_user(user)
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@main_bp.route("/")
def index():
    return "Index"


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return "Dashboard"


@main_bp.route("/rooms", methods=["GET", "POST"])
@login_required
def rooms():
    form = ReservationForm()
    available_rooms = Room.query.filter(Room.status == "available").order_by(Room.id).all()
    form.room_id.choices = [(room.id, f"{room.name} - ₱{room.base_rate}/hr") for room in available_rooms]

    if request.method == "POST" and current_user.role == "member" and form.validate_on_submit():
        receipt_file = request.files.get("receipt_image")
        if not receipt_file or receipt_file.filename == "":
            flash("Please upload your payment receipt for verification.", "danger")
            return "Receipt missing", 400

        allowed_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf"}
        ext = os.path.splitext(receipt_file.filename)[1].lower()
        if ext not in allowed_ext:
            flash("Unsupported receipt file type. Allowed: PNG, JPG, GIF, PDF.", "danger")
            return "Unsupported receipt file type", 400

        reservation = Reservation(
            room_id=form.room_id.data,
            user_id=current_user.id,
            customer_name=form.customer_name.data,
            contact_number=form.contact_number.data,
            pax_count=form.pax_count.data or 1,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            is_open_time=form.is_open_time.data or False,
            status="Pending",
            payment_method=form.payment_method.data,
            payment_type=form.payment_type.data or "Downpayment",
            receipt_image=secure_filename(receipt_file.filename),
            extra_notes=form.extra_notes.data,
            total_amount=0.0,
        )
        db.session.add(reservation)
        db.session.commit()
        return "Awaiting admin approval", 200

    return "Rooms Page", 200


@main_bp.route("/admin/payment_settings", methods=["GET", "POST"])
@login_required
def payment_settings():
    if current_user.role != "admin":
        return "Unauthorized", 403

    if request.method == "POST":
        method = request.form.get("method")
        account_name = request.form.get("account_name")
        account_number = request.form.get("account_number")
        instructions = request.form.get("instructions")
        qr_image_file = request.files.get("qr_image")

        payment_info = PaymentInfo.query.filter_by(method=method).first()
        if not payment_info:
            payment_info = PaymentInfo(method=method)
            db.session.add(payment_info)

        payment_info.account_name = account_name
        payment_info.account_number = account_number
        payment_info.instructions = instructions
        if qr_image_file and qr_image_file.filename:
            payment_info.qr_image = secure_filename(qr_image_file.filename)

        db.session.commit()
        return f"{method} payment settings updated.", 200

    return "Payment Settings Page", 200
'''

TEST_FILE.write_text(TEST_CONTENT, encoding='utf-8')
CLIENT_FILE.write_text(CLIENT_CONTENT, encoding='utf-8')
print('Wrote test_app.py and client_fixed.py')
