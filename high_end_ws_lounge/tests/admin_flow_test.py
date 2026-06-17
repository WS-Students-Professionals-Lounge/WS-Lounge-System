import os
import sys
from datetime import datetime, timedelta
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run import create_app
from database_fixed import Config, db, User, Room, Reservation, WalkinReservation, DailyReport
from admin import get_active_room_reservations


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def run_admin_tests():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        # create admin and member
        admin = User(name='Admin User', email='admin@lounge.com', role='admin', phone='09171111111')
        admin.set_password('admin123')
        member = User(name='Walkin Member', email='walkin@example.com', role='member', phone='09170000001')
        member.set_password('member123')
        db.session.add_all([admin, member])
        db.session.commit()

        # create a room
        room = Room(name='Test Room A', base_rate=100.0, category='meeting')
        common = Room(name='Common Area', base_rate=35.0, category='solo')
        db.session.add_all([room, common])
        db.session.commit()

        client = app.test_client()

        # Set admin session for client
        admin_client = app.test_client()
        with admin_client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        # Walk-in checkin to Test Room A
        form = {
            'room_id': str(room.id),
            'customer_name': 'Walkin Person',
            'contact_number': '09171234567',
            'pax_count': '3',
            'extra_notes': 'Testing walkin',
            'extra_fee': '0',
        }
        resp = admin_client.post('/admin/walkin_checkin', data=form, follow_redirects=True)
        print('WALKIN_CHECKIN_STATUS:', resp.status_code)

        # Verify reservation created
        res = Reservation.query.filter_by(customer_name='Walkin Person').first()
        print('WALKIN_RES_CREATED:', 'OK' if res and res.status == 'Walk-in' else 'FAILED')
        # Room should be unavailable if start_time <= now
        room_refreshed = Room.query.get(room.id)
        print('ROOM_STATUS_AFTER_CHECKIN:', room_refreshed.status)

        # WalkinReservation exists
        walk = WalkinReservation.query.filter_by(reservation_id=res.id).first()
        print('WALKIN_ENTRY_CREATED:', 'OK' if walk else 'MISSING')

        # Checkout: simulate payment
        checkout = admin_client.get(f'/admin/walkin_checkout/{res.id}?final_bill=200', follow_redirects=True)
        print('WALKIN_CHECKOUT_STATUS:', checkout.status_code)

        res_after = Reservation.query.get(res.id)
        walk_after = WalkinReservation.query.filter_by(reservation_id=res.id).first()
        print('RES_STATUS_AFTER_CHECKOUT:', res_after.status, 'PAID:', res_after.paid)
        print('WALK_STATUS_AFTER_CHECKOUT:', walk_after.status if walk_after else 'NO-WALK')

        # Daily report created for the date
        report_date = res_after.end_time.date()
        report = DailyReport.query.filter_by(report_date=report_date).first()
        print('DAILY_REPORT_CREATED:', 'OK' if report else 'MISSING')
        if report:
            print('DAILY_REPORT_TOTAL_CHECK_INS:', report.total_check_ins, 'TOTAL_TIMELOGGED(REVENUE):', report.total_timelogged)

        # Future confirmed reservation should not appear as an active session until its start time.
        future_res = Reservation(
            user_id=admin.id,
            customer_id=888,
            room_id=room.id,
            customer_name='Future Guest',
            contact_number='09170002222',
            pax_count=2,
            start_time=datetime.now() + timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=3),
            status='Confirmed',
            total_amount=150.0,
            paid=True,
        )
        db.session.add(future_res)
        db.session.commit()
        future_active = get_active_room_reservations([room])
        print('FUTURE_RES_ACTIVE_COUNT:', len(future_active))
        print('FUTURE_RES_SHOWN_ACTIVE:', 'YES' if future_res.id in [r.id for r in future_active.values()] else 'NO')

        # Expired session handling: create a confirmed reservation that ended in past
        past_res = Reservation(
            user_id=admin.id,
            customer_id=999,
            room_id=room.id,
            customer_name='Past User',
            contact_number='09170001111',
            pax_count=2,
            start_time=datetime.now() - timedelta(hours=3),
            end_time=datetime.now() - timedelta(hours=1),
            status='Confirmed',
            total_amount=100.0,
            paid=True,
        )
        db.session.add(past_res)
        db.session.commit()

        # Call admin dashboard which triggers expiry update
        dash = admin_client.get('/admin/dashboard')
        print('DASHBOARD_GET_STATUS:', dash.status_code)
        past_after = Reservation.query.get(past_res.id)
        print('PAST_RES_STATUS_AFTER_DASHBOARD:', past_after.status)


if __name__ == '__main__':
    run_admin_tests()
