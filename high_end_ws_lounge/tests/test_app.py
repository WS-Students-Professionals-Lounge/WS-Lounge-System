import os
import sqlite3
import sys
from datetime import datetime
import pytest
import uuid
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_fixed import User, db, Room, PaymentInfo
from run import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        # db.drop_all()  # Skip cleanup to see test results


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
        # Create test user with a unique email to avoid collisions in a shared DB.
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        user = User(name='test', email=email, role='member')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        
        res = client.post('/auth/login', data={'email': email, 'password': 'testpass'})
        print(f"Login response status: {res.status_code}")
        print(f"Login response location: {res.location}")
        assert res.status_code == 302  # Redirect on success


def test_login_accepts_existing_account_without_csrf_token(app, client):
    with app.app_context():
        email = f"legacy-{uuid.uuid4().hex[:8]}@example.com"
        user = User(name='legacy', email=email, role='member')
        user.password = 'legacy-pass'
        db.session.add(user)
        db.session.commit()

        app.config['WTF_CSRF_ENABLED'] = True
        res = client.post('/auth/login', data={'email': email, 'password': 'legacy-pass'})

        assert res.status_code == 302
        assert res.headers['Location'].endswith('/dashboard')


def test_login_falls_back_to_local_sqlite_user(app, client):
    with app.app_context():
        email = f"sqlite-fallback-{uuid.uuid4().hex[:8]}@example.com"
        sqlite_path = os.path.join(os.path.dirname(__file__), '..', 'app.db')
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, phone, password, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('sqlite fallback', email, '09170000000', 'legacy-pass', 'member', 1, datetime.utcnow()),
        )
        conn.commit()
        conn.close()

        res = client.post('/auth/login', data={'email': email, 'password': 'legacy-pass'})

        assert res.status_code == 302
        assert res.headers['Location'].endswith('/dashboard')


def test_admin_dashboard_deduplicates_room_cards(app, client):
    with app.app_context():
        admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        admin = User(name='admin', email=admin_email, role='admin')
        admin.set_password('adminpass')
        db.session.add(admin)

        duplicate_room_name = f"Duplicate Room {uuid.uuid4().hex[:4]}"
        db.session.add(Room(name=duplicate_room_name, base_rate=50.0, status='available'))
        db.session.add(Room(name=duplicate_room_name, base_rate=50.0, status='available'))
        db.session.commit()

        login_res = client.post('/auth/login', data={'email': admin_email, 'password': 'adminpass'})
        assert login_res.status_code == 302

        dash = client.get('/admin/dashboard')
        assert dash.status_code == 200
        html = dash.get_data(as_text=True)
        assert html.count(f'<span class="room-name">{duplicate_room_name}</span>') == 1


def test_reservation(app, client):
    with app.app_context():
        member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"
        admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"

        # Create test users
        member = User(name='member', email=member_email, role='member')
        member.set_password('memberpass')
        admin = User(name='admin', email=admin_email, role='admin')
        admin.set_password('adminpass')
        db.session.add(member)
        db.session.add(admin)

        # Create a room and initial payment settings. Reuse existing GCash entry if present.
        payment_info = PaymentInfo.query.filter_by(method='GCash').first()
        if not payment_info:
            payment_info = PaymentInfo(method='GCash', account_name='Admin', account_number='09170000000', instructions='Pay and upload receipt')
            db.session.add(payment_info)
        room = Room(name='Test Room', base_rate=50.0, status='available')
        db.session.add(room)
        db.session.commit()

        # Member login
        login_res = client.post('/auth/login', data={'email': member_email, 'password': 'memberpass'})
        assert login_res.status_code == 302

        # Submit a reservation with receipt upload
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

        # Admin login and update payment settings
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

