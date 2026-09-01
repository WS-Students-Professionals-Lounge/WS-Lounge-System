import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run import create_app
from database_fixed import Config, db, User


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def test_registration_persists_user_to_database():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        client = app.test_client()
        response = client.post('/auth/register', data={
            'name': 'New User',
            'email': 'newuser@example.com',
            'phone': '09170000000',
            'password': 'password123',
            'password2': 'password123',
        }, follow_redirects=True)

        assert response.status_code == 200
        assert User.query.filter_by(email='newuser@example.com').count() == 1
