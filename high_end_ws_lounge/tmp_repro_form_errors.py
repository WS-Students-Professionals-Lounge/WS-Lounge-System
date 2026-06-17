from run import create_app
from database_fixed import Config, db, User, Room, AdminReservationForm
from datetime import datetime, timedelta

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

app = create_app(TestConfig)
with app.app_context():
    db.drop_all()
    db.create_all()
    admin = User(name='Admin User', email='admin@test', role='admin', phone='09171111111')
    admin.set_password('admin123')
    room = Room(name='Test Room A', base_rate=100.0, category='meeting')
    db.session.add_all([admin, room])
    db.session.commit()

    with app.test_request_context('/admin/reservations', method='POST', data={
        'room_id': str(room.id),
        'customer_name': 'Test Customer',
        'contact_number': '09170000000',
        'pax_count': '2',
        'start_time': (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        'end_time': (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M'),
        'open_time': '',
        'extra_fee': '0',
        'discount': '0.0',
        'total_price': '100.00',
    }):
        form = AdminReservationForm()
        valid = form.validate()
        print('VALID', valid)
        print('ERRORS', form.errors)
        print('START_TIME_DATA', form.start_time.data, type(form.start_time.data))
        print('END_TIME_DATA', form.end_time.data, type(form.end_time.data))
        print('START_DATE_DATA', form.start_date.data, type(form.start_date.data) if hasattr(form, 'start_date') else None)
