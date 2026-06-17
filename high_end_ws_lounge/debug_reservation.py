from io import BytesIO
import uuid
from run import create_app
from database import db, User, Room, PaymentInfo

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    db.create_all()
    member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"

    member = User(name='member', email=member_email, role='member')
    member.set_password('memberpass')
    admin = User(name='admin', email=admin_email, role='admin')
    admin.set_password('adminpass')
    db.session.add(member)
    db.session.add(admin)

    payment_info = PaymentInfo.query.filter_by(method='GCash').first()
    if not payment_info:
        payment_info = PaymentInfo(method='GCash', account_name='Admin', account_number='09170000000', instructions='Pay and upload receipt')
        db.session.add(payment_info)
    room = Room(name='Test Room', base_rate=50.0, status='available')
    db.session.add(room)
    db.session.commit()

    client = app.test_client()
    # login
    login_res = client.post('/auth/login', data={'email': member_email, 'password': 'memberpass'})
    print('login status', login_res.status_code)

    reservation_data = {
        'room_id': str(room.id),
        'customer_name': 'Test Member',
        'contact_number': '09171234567',
        'pax_count': '2',
        'start_time': '2026-05-17T10:00',
        'end_time': '2026-05-17T12:00',
        'payment_method': 'GCash',
        'extra_notes': 'Feature test booking',
    }
    reservation_data['receipt_image'] = (BytesIO(b'testreceipt'), 'receipt.png')
    res = client.post('/rooms', data=reservation_data, content_type='multipart/form-data', follow_redirects=True)
    print('post status', res.status_code)
    print(res.data.decode('utf-8'))
