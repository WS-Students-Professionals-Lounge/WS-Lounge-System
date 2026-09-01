import os

from run import create_app
from database_fixed import User, db


class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def setup_app():
    app = create_app(TestConfig)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(name="Jane Doe", email="jane@example.com", phone="09170000000", role="member")
        user.set_password("oldpassword")
        db.session.add(user)
        db.session.commit()
        return app, user


def test_profile_update_and_password_change():
    app, user = setup_app()
    client = app.test_client()

    login_response = client.post(
        "/auth/login",
        data={"email": "jane@example.com", "password": "oldpassword", "remember_me": False},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    profile_response = client.post(
        "/profile",
        data={
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "09170001111",
            "profile_submit": "Save Profile",
        },
        follow_redirects=True,
    )
    assert profile_response.status_code == 200
    assert b"Profile updated successfully." in profile_response.data

    with app.app_context():
        updated_user = User.query.get(user.id)
        assert updated_user.name == "Jane Smith"
        assert updated_user.email == "jane.smith@example.com"
        assert updated_user.phone == "09170001111"

    password_response = client.post(
        "/profile",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
            "password_submit": "Change Password",
        },
        follow_redirects=True,
    )
    assert password_response.status_code == 200
    assert b"Password changed successfully." in password_response.data

    with app.app_context():
        updated_user = User.query.get(user.id)
        assert updated_user.check_password("newpassword123")
