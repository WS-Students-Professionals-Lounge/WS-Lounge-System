import os
import sys
import uuid
from io import BytesIO, BytesIOm, import, io

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_fixed import PaymentInfo, Room, User, dbcreate_app

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
        room = Room(name='Conference Room', base_rate=50.0, status='available')
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

