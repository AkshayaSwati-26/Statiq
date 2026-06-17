from sqlalchemy import create_engine, text
engine = create_engine("postgresql://statiq:statiq123@postgres:5432/statiq")
hash_str = "$argon2id$v=19$m=65536,t=3,p=4$TduC7RXWWAkdoNLluzQtEg$aGcdfmkC6EdO5B61km37Z8WVsSlldiQKlW73uX/Sa3A"
with engine.begin() as conn:
    conn.execute(text("UPDATE users SET password_hash = :hash"), {"hash": hash_str})
print("Passwords updated correctly.")
