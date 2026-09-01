import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database_fixed import User, db

from run import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_redirects_on_success(app, client):
    with app.app_context():
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        user = User(name="test", email=email, role="member")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

        response = client.post("/auth/login", data={"email": email, "password": "testpass"})
        assert response.status_code == 302
