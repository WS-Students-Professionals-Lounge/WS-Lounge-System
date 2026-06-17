"""Utility to create a test staff user via the app context."""
from run import app
from database_fixed import db, User

def main():
    with app.app_context():
        email = "ci_test_staff@example.com"
        user = User.query.filter_by(email=email).first()
        if user:
            print("already exists", user.id)
            return
        user = User(name="CI Test Staff", email=email, phone="09170000000", role="staff", is_active=True)
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
        print("created", user.id)

if __name__ == "__main__":
    main()
