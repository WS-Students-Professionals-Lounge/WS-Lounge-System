"""Utility to create an admin or staff user via the app context."""
import argparse

from run import app
from database_fixed import db, User


def main():
    parser = argparse.ArgumentParser(description="Create an admin or staff user.")
    parser.add_argument("--name", required=True, help="Full name of the new user")
    parser.add_argument("--email", required=True, help="Email address for the new user")
    parser.add_argument("--password", required=True, help="Password for the new user")
    parser.add_argument("--phone", default="", help="Phone number for the new user")
    parser.add_argument("--role", choices=["admin", "staff"], default="admin", help="Role for the new user")
    args = parser.parse_args()

    email = args.email.strip().lower()
    with app.app_context():
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists (id={existing_user.id}).")
            return

        user = User(
            name=args.name.strip(),
            email=email,
            phone=args.phone.strip(),
            role=args.role,
            is_active=True,
        )
        user.set_password(args.password)
        db.session.add(user)
        db.session.commit()

        print(f"Created {args.role} user {args.name} ({email}) with id {user.id}.")


if __name__ == "__main__":
    main()
