from run import app, db
from sqlalchemy import inspect

with app.app_context():
    insp = inspect(db.engine)
    fks = insp.get_foreign_keys('walkin_reservations')
    print('walkin_reservations foreign keys:')
    for fk in fks:
        print(fk)
