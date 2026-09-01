import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run import create_app
from database_fixed import Config, db, User, Room, Reservation


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def test_completed_sessions_pdf_route_returns_pdf_response():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = User(name='Admin User', email='admin@lounge.com', role='admin', phone='09171111111')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        room = Room(name='Test Room A', base_rate=100.0, category='meeting')
        db.session.add(room)
        db.session.commit()

        reservation = Reservation(
            user_id=admin.id,
            room_id=room.id,
            customer_name='Sample Guest',
            contact_number='09170000000',
            pax_count=2,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(minutes=30),
            status='Checked-Out',
            total_amount=250.0,
            paid=True,
        )
        db.session.add(reservation)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        response = client.get('/admin/generate_completed_sessions_pdf?start_date=2024-01-01&end_date=2030-12-31')

        assert response.status_code == 200
        assert response.mimetype == 'application/pdf'
        assert b'%PDF-' in response.data
