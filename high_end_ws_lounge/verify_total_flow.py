from run import create_app
from sqlalchemy import func
from datetime import datetime, timedelta
from admin import calculate_admin_total_amount, refresh_daily_report
from database_fixed import db, Reservation, Room, User, WalkinReservation

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False

with app.test_client() as client:
    with app.app_context():
        room = Room.query.order_by(Room.id).first()
        if not room:
            raise SystemExit('No room found')
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(name='verify admin', email='verify_admin@example.com', role='admin')
            admin.set_password('pw')
            db.session.add(admin)
            db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        room_rate = float(room.base_rate or 0)
        addon_subtotal = 300.0
        extra_fee = 0.0
        discount_rate = 0.0
        preview_total = calculate_admin_total_amount(
            room_rate=room_rate,
            duration_hours=1.0,
            extra_fee=extra_fee,
            addon_subtotal=addon_subtotal,
            discount_rate=discount_rate,
            is_open_time=False,
        )

        reservation_start = datetime.now().strftime('%Y-%m-%dT%H:%M')
        reservation_end = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        walkin_start = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        walkin_end = (datetime.now() + timedelta(days=1, hours=1)).strftime('%Y-%m-%dT%H:%M')

        res_resp = client.post('/admin/reservations', data={
            'customer_name': 'Verify Reservation',
            'contact_number': '09170000000',
            'room_id': str(room.id),
            'start_time': reservation_start,
            'end_time': reservation_end,
            'extra_fee': '0.00',
            'addon_subtotal': f'{addon_subtotal:.2f}',
            'addons_json': '[{"addon_name":"Projector","quantity":2,"unit_price":150,"subtotal":300}]',
            'total_price': f'{preview_total:.2f}',
            'discount': '0.0',
            'payment_method': 'Cash',
            'extra_notes': 'verification',
            'open_time': 'n',
        }, follow_redirects=False)

        print('preview_total=', preview_total)
        print('reservation_status=', res_resp.status_code)
        print('reservation_location=', res_resp.headers.get('Location'))

        reservation = Reservation.query.filter_by(customer_name='Verify Reservation').order_by(Reservation.id.desc()).first()
        if not reservation:
            raise SystemExit('Reservation was not created')

        print('reservation_saved=', {
            'total_amount': reservation.total_amount,
            'addon_subtotal': reservation.addon_subtotal,
            'extra_fee': reservation.extra_fee,
            'discount_rate': reservation.discount_rate,
            'status': reservation.status,
            'paid': reservation.paid,
        })

        walk_resp = client.post('/admin/walkin_checkin', data={
            'customer_name': 'Verify Walkin',
            'contact_number': '09170000001',
            'room_id': str(room.id),
            'start_time': walkin_start,
            'end_time': walkin_end,
            'extra_fee': '0.00',
            'addon_subtotal': f'{addon_subtotal:.2f}',
            'addons_json': '[{"addon_name":"Projector","quantity":2,"unit_price":150,"subtotal":300}]',
            'total_price': f'{preview_total:.2f}',
            'discount': '0.0',
            'payment_method': 'Cash',
            'extra_notes': 'verification',
            'open_time': 'n',
        }, follow_redirects=False)

        print('walkin_status=', walk_resp.status_code)
        print('walkin_location=', walk_resp.headers.get('Location'))

        walkin = WalkinReservation.query.filter_by(customer_name='Verify Walkin').order_by(WalkinReservation.id.desc()).first()
        if not walkin:
            raise SystemExit('Walkin was not created')

        print('walkin_saved=', {
            'total_amount': walkin.total_amount,
            'addon_subtotal': walkin.addon_subtotal,
            'extra_fee': walkin.extra_fee,
            'status': walkin.status,
            'paid': walkin.paid,
        })

        report = refresh_daily_report(datetime.now().date())
        print('report_total_timelogged=', report.total_timelogged)

        earnings = (
            db.session.query(func.coalesce(func.sum(Reservation.total_amount), 0))
            .filter(
                Reservation.end_time >= datetime.combine(datetime.now().date(), datetime.min.time()),
                Reservation.end_time < datetime.combine(datetime.now().date(), datetime.max.time()),
                Reservation.paid == True,
                Reservation.status == 'Checked-Out',
            )
            .scalar()
            or 0
        )
        print('earnings_query_total=', earnings)

        db.session.delete(reservation)
        db.session.delete(walkin)
        db.session.commit()
