from argon2 import PasswordHasher
ph = PasswordHasher()
hash_str = ph.hash("AdminPassword123!")
print("NEW HASH:", hash_str)
