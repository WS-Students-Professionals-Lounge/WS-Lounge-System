from database_fixed import Reservation, db
from run import app

with app.app_context():
    res = Reservation.query.filter_by(customer_name='Auto Walkin').all()
    print('Found', len(res))
    for r in res:
        print(r.id, r.room_id, r.start_time, r.end_time, r.status, r.total_amount)
