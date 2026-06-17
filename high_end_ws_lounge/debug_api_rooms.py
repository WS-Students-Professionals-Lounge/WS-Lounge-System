import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from run import create_app
from database_fixed import Config, db, Room, User

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

app = create_app(TestConfig)
with app.app_context():
    db.create_all()
    admin = User(name='Admin User', email='admin@lounge.com', role='admin', phone='09171111111')
    admin.set_password('admin123')
    room = Room(name='Room A', base_rate=100.0, category='meeting')
    db.session.add_all([admin, room])
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    resp = client.get('/admin/api/rooms')
    print('STATUS', resp.status_code)
    print(resp.get_json())
