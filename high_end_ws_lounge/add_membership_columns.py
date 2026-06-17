#!/usr/bin/env python3
"""One-time script to add membership columns to existing DB"""

from database import User, db
from sqlalchemy import text

print('🔄 Adding membership columns...')

try:
    # Add columns if not exist (MySQL/MariaDB)
    db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_id VARCHAR(20) NULL, ADD COLUMN IF NOT EXISTS expiry_date DATETIME NULL'))

    db.session.commit()
    print('✅ Columns added')
    
    # Add unique index if needed
    db.session.execute(text('ALTER TABLE users ADD UNIQUE INDEX IF NOT EXISTS idx_membership_id (membership_id)'))
    db.session.commit()
    print('✅ Unique index added')
    
except Exception as e:
    print(f'⚠️  Migration warning: {e}')
    db.session.rollback()

# Generate membership_id for existing members
members = User.query.filter(User.role == 'member', User.membership_id.is_(None)).all()
for member in members:
    member.membership_id = f'WS-WLK-{str(member.id).zfill(4)}'
db.session.commit()
print(f'✅ Generated membership_id for {len(members)} existing members')

print('🎉 DB ready for members admin!')

