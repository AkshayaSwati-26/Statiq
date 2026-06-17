from argon2 import PasswordHasher
ph = PasswordHasher()
hash_str = "$argon2id$v=19$m=65536,t=3,p=4$EVd0yt4N1F1yV2gcG5GvHw$46mXnV854w+ys+mv/VehCWUFLWuzXoc6MQHkGePx/dU"
try:
    ph.verify(hash_str, "AdminPassword123!")
    print("Match!")
except Exception as e:
    print("No match:", e)
