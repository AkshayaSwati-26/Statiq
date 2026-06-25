from security.auth import verify_password
from db.loader import engine
from sqlalchemy import text

# Fetch hash from DB
with engine.connect() as conn:
    row = conn.execute(text("SELECT password_hash FROM users WHERE user_id = 'admin'")).fetchone()
    if row:
        pwd_hash = row[0]
        print("Hash in DB:", pwd_hash)
        # Try some passwords
        passwords = ["StrongPassword123!", "MoSPIAdmin2026", "admin", "admin123"]
        for p in passwords:
            try:
                res = verify_password(p, pwd_hash)
                print(f"Password '{p}': {res}")
            except Exception as e:
                print(f"Error for '{p}': {e}")
    else:
        print("Admin user not found in DB")
