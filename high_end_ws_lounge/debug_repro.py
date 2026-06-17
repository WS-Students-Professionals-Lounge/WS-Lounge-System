from run import create_app
from database_fixed import Config, db, User, Room, Reservation
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

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    start = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
    end = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
    res = client.post(
        '/admin/reservations',
        data={
            'room_id': str(room.id),
            'customer_name': 'Test Customer',
            'contact_number': '09170000000',
            'pax_count': '2',
            'start_time': start,
            'end_time': end,
            'open_time': '',
            'extra_fee': '0',
            'discount': '0.0',
            'total_price': '100.00',
        },
        follow_redirects=True,
    )
    print('STATUS', res.status_code)
    print('RES COUNT', Reservation.query.count())
    if Reservation.query.count():
        r = Reservation.query.first()
        print('RES', r.customer_name, r.status, r.start_time, r.end_time, r.room_id)
    else:
        print('NO RES CREATED')
    print('BODY START:')
    print(res.data.decode()[:1000])
