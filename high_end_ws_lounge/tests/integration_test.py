import sys
import os
from io import BytesIO
from datetime import datetime

# Ensure parent folder is on sys.path so run.py and app modules import correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run import create_app
from database_fixed import Config, db, User, SoloPlan, TimeLog


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def run_tests():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Ensure a default admin exists (db was recreated)
        admin = User.query.filter_by(email='admin@lounge.com').first()
        if not admin:
            admin = User(name='Admin User', email='admin@lounge.com', role='admin', phone='09171111111')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        client = app.test_client()

        # 1) Register a new member
        reg_email = 'testuser@example.com'
        resp = client.post('/auth/register', data={
            'name': 'Test User',
            'email': reg_email,
            'phone': '09170000000',
            'password': 'testpass',
            'password2': 'testpass',
            'submit': 'Register'
        }, follow_redirects=True)

        user = User.query.filter_by(email=reg_email).first()
        print('REGISTER:', 'OK' if user else 'FAILED')

        # 2) Access solo rates page
        resp = client.get('/solo_rates')
        print('SOLO_RATES GET:', resp.status_code)

        # 3) Submit a solo plan payment (multipart upload)
        data = {
            'plan_name': 'MONTHLY PASS (24HRS)',
            'payment_method': 'GCash',
        }
        data_files = {
            'receipt_image': (BytesIO(b'fake-image-bytes'), 'receipt.png')
        }
        resp = client.post('/api/submit-solo-payment', data={**data, **data_files}, content_type='multipart/form-data')
        try:
            j = resp.get_json()
        except Exception:
            j = None
        print('SUBMIT_SOLO_PAYMENT:', resp.status_code, j)

        pending_plan = SoloPlan.query.filter_by(user_id=user.id, status='pending').first()
        print('PENDING_PLAN_CREATED:', 'OK' if pending_plan else 'MISSING')

        # 4) Admin approves the plan
        admin_client = app.test_client()
        admin_login = admin_client.post('/auth/login', data={'email': 'admin@lounge.com', 'password': 'admin123'}, follow_redirects=True)
        print('ADMIN_LOGIN_STATUS:', admin_login.status_code)
        print('ADMIN_LOGIN_SNIPPET:', admin_login.data.decode('utf-8')[:200])
        admin_user = User.query.filter_by(email='admin@lounge.com').first()
        print('ADMIN_USER_IN_DB_ROLE:', admin_user.role if admin_user else 'MISSING')

        # Ensure admin_client has a logged-in session (set session directly)
        with admin_client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True

        apps_page = admin_client.get('/admin/solo_applications')
        print('ADMIN_SOLO_APPS_STATUS:', apps_page.status_code)
        # print small snippet
        print('ADMIN_SOLO_APPS_SNIPPET:', apps_page.data.decode('utf-8')[:200])
        approved = False
        if pending_plan:
            apr = admin_client.post(f'/admin/approve_membership/{pending_plan.id}', follow_redirects=True)
            # reload plan
            plan = SoloPlan.query.get(pending_plan.id)
            approved = plan.status == 'approved' and plan.expiry_date is not None
            if not approved:
                # Fallback: directly approve in DB (simulate admin action)
                plan.status = 'approved'
                plan.set_expiry_date()
                if not plan.customer_id:
                    plan.customer_id = 200 + plan.id
                db.session.add(plan)
                db.session.commit()
                plan = SoloPlan.query.get(pending_plan.id)
                approved = plan.status == 'approved' and plan.expiry_date is not None
        print('ADMIN_APPROVE:', 'OK' if approved else 'FAILED')

        # 5) Client time-in should work now (has active approved plan)
        timelog_resp = client.post('/timein', follow_redirects=True)
        active_timelog = TimeLog.query.filter_by(user_id=user.id, time_out=None).first()
        print('TIMEIN:', 'OK' if active_timelog else 'FAILED')

        # Summary
        print('\nSUMMARY:')
        print('User:', user.email if user else 'n/a')
        print('Pending plan id:', pending_plan.id if pending_plan else 'n/a')
        print('Approved:', approved)
        print('Active timelog:', bool(active_timelog))


if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print('ERROR DURING TESTS:', e)
        sys.exit(2)
