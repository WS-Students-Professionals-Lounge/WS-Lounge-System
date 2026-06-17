from run import create_app
from database_fixed import Config, db, User, Room, Reservation
import admin as admin_module
from datetime import datetime, timedelta

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

app = create_app(TestConfig)
with app.app_context():
    db.drop_all()
    db.create_all()

    # create admin and room
    admin = User(name='Admin User', email='admin@test', role='admin', phone='09171111111')
    admin.set_password('admin123')
    room = Room(name='Main Room', base_rate=100.0, category='meeting')
    db.session.add_all([admin, room])
    db.session.commit()

    # Create 10 pending reservations for today with staggered start times
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    reservations = []
    for i in range(10):
        st = now + timedelta(hours=1 + i)  # start times 1h,2h,...
        et = st + timedelta(hours=1)
        res = Reservation(
            user_id=admin.id,
            customer_id=1000 + i,
            room_id=room.id,
            customer_name=f'Test{i}',
            contact_number='09170000000',
            pax_count=2,
            start_time=st,
            end_time=et,
            is_open_time=False,
            status='Pending',
            total_amount=100.0,
        )
        db.session.add(res)
        reservations.append(res)
    db.session.commit()

    # Patch render_template to capture pending_reservations
    captured = {}
    orig_render = admin_module.render_template
    def patched_render(template_name, *args, **kwargs):
        captured['template'] = template_name
        captured['kwargs'] = kwargs
        if 'pending_reservations' in kwargs:
            captured['pending_reservations'] = list(kwargs['pending_reservations'])
        return orig_render(template_name, *args, **kwargs)

    admin_module.render_template = patched_render

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    # Initial dashboard capture
    resp = client.get('/admin/dashboard')
    initial = captured.get('pending_reservations', [])
    print('INITIAL_PENDING_COUNT', len(initial))
    print('INITIAL_IDS', [r.id for r in initial])

    # Simulate one reservation becoming active: make the first reservation a Walk-in and set start_time <= now
    first = reservations[0]
    first.status = 'Walk-in'
    first.start_time = now - timedelta(minutes=30)
    first.end_time = now + timedelta(hours=1)
    db.session.add(first)
    db.session.commit()

    captured.clear()
    resp2 = client.get('/admin/dashboard')
    after = captured.get('pending_reservations', [])
    print('AFTER_ACTIVE_PENDING_COUNT', len(after))
    print('AFTER_IDS', [r.id for r in after])

    # Show which reservation was promoted into the pending list (if any)
    promoted = [r.id for r in after if r.id not in [x.id for x in initial]]
    print('PROMOTED_IDS', promoted)
