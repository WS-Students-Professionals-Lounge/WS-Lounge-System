"""Create test user with active membership for testing the dashboard."""
from run import app
from database_fixed import db, User, Membership, AttendanceLog
from datetime import datetime, timedelta

def main():
    with app.app_context():
        # Create or update test user
        email = "member@example.com"
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(name="Test Member", email=email, phone="09171234567", role="member", is_active=True)
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
        
        # Remove existing membership if any
        existing_membership = Membership.query.filter_by(user_id=user.id).first()
        if existing_membership:
            # Remove attendance logs first
            AttendanceLog.query.filter_by(membership_id=existing_membership.id).delete()
            db.session.delete(existing_membership)
        
        # Create membership (approved, active)
        now = datetime.utcnow()
        start_date = now - timedelta(hours=2)  # Started 2 hours ago for testing
        expiry_date = now + timedelta(days=30)  # Expires in 30 days
        
        membership = Membership(
            user_id=user.id,
            status='active',
            start_date=start_date,
            expiry_date=expiry_date,
            total_hours=100.0,
            hours_left=95.5,
            plan_name='Premium Plan - 100 Hours',
            is_checked_in=False,
        )
        db.session.add(membership)
        db.session.flush()
        
        # Create sample attendance logs (completed sessions)
        # Session 1: 2 hours used
        log1 = AttendanceLog(
            membership_id=membership.id,
            check_in_time=now - timedelta(hours=5),
            check_out_time=now - timedelta(hours=3),
            hours_deducted=2.0,
        )
        db.session.add(log1)
        
        # Session 2: 1.5 hours used
        log2 = AttendanceLog(
            membership_id=membership.id,
            check_in_time=now - timedelta(hours=2.5),
            check_out_time=now - timedelta(hours=1),
            hours_deducted=1.5,
        )
        db.session.add(log2)
        
        # Session 3: Active session (currently checked in)
        log3 = AttendanceLog(
            membership_id=membership.id,
            check_in_time=now - timedelta(minutes=30),
            check_out_time=None,  # Still checked in
            hours_deducted=0.0,
        )
        db.session.add(log3)
        membership.is_checked_in = True
        
        db.session.commit()
        print(f"✅ Test user created/updated:")
        print(f"   Email: {email}")
        print(f"   Password: password123")
        print(f"   Membership Status: {membership.status}")
        print(f"   Started: {membership.start_date}")
        print(f"   Expires: {membership.expiry_date}")
        print(f"   Total Hours: {membership.total_hours}")
        print(f"   Hours Left: {membership.hours_left}")
        print(f"   Accumulated Hours: {membership.accumulated_hours}")
        print(f"   Currently Checked In: {membership.is_checked_in}")

if __name__ == "__main__":
    main()
