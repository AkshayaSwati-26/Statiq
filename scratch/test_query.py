import requests

s = requests.Session()
r = s.post("http://localhost:8000/v1/auth/login", json={"user_id": "researcher1", "password": "AdminPassword123!"})
print("Login:", r.status_code, r.text)

r2 = s.post("http://localhost:8000/v1/query/nl", json={"question": "What is the unemployment rate in Tamil Nadu?", "language": "en"})
print("Query:", r2.status_code, r2.text)
