from run import app, db
from sqlalchemy import text

with app.app_context():
    inspector = db.inspect(db.engine)
    print('Tables in DB:', inspector.get_table_names())
    try:
        # Try dropping the known FK name if it exists
        db.session.execute(text('ALTER TABLE walkin_reservations DROP FOREIGN KEY walkin_reservations_ibfk_1'))
        print('Dropped foreign key walkin_reservations_ibfk_1')
    except Exception as e:
        print('Drop FK failed (may not exist):', e)
    try:
        db.session.execute(text('ALTER TABLE walkin_reservations ADD CONSTRAINT fk_walkin_reservation_id FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE'))
        print('Added FK fk_walkin_reservation_id with ON DELETE CASCADE')
    except Exception as e:
        print('Add FK failed:', e)
    db.session.commit()
    print('Done')
