import sys
import os
sys.path.append(os.getcwd())

try:
    from db.loader import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        users = conn.execute(text("SELECT user_id, password_hash, scope FROM users")).fetchall()
        for u in users:
            print(u)
except Exception as e:
    print(f"Error: {e}")
