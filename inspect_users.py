from database_fixed import Config
from sqlalchemy import create_engine, text
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
print('DB URI:', Config.SQLALCHEMY_DATABASE_URI)
print(engine.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")) .fetchall())
print(engine.execute(text("SELECT id, name, email, role, is_active, password FROM users ORDER BY id")) .fetchall())