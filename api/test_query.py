import requests
import sys

BASE_URL = "http://localhost:8000/v1/auth"
QUERY_URL = "http://localhost:8000/v1/query/nl"

def test_nl_query():
    print("=== STARTING NL-TO-SQL DYNAMIC GENERATION TEST ===")
    
    # 1. Register a new user
    import uuid
    random_id = uuid.uuid4().hex[:6]
    test_email = f"query_user_{random_id}@univ.edu.in"
    payload = {
        "email": test_email,
        "password": "StrongPassword123!",
        "scope": "public"
    }
    session = requests.Session()
    r = session.post(f"{BASE_URL}/register", json=payload)
    assert r.status_code == 200
    token = session.cookies.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upgrade user to Premium (research scope required for NL query)
    r = session.post(f"{BASE_URL}/upgrade", headers=headers)
    assert r.status_code == 200
    token = session.cookies.get("access_token") or token
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Test Question A
    q_a = "What is the average age of respondents?"
    print(f"\nQuestion A: '{q_a}'")
    r = session.post(QUERY_URL, json={"question": q_a, "language": "en"}, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response JSON: {r.text}")
    assert r.status_code == 200
    sql_a = r.json().get("sql", "")
    print(f"Generated SQL A: {sql_a}")
    
    # 4. Test Question B
    q_b = "Show the number of female respondents by state."
    print(f"\nQuestion B: '{q_b}'")
    r = session.post(QUERY_URL, json={"question": q_b, "language": "en"}, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response JSON: {r.text}")
    assert r.status_code == 200
    sql_b = r.json().get("sql", "")
    print(f"Generated SQL B: {sql_b}")
    
    # Check if they are different
    print("\n=== RESULTS COMPARISON ===")
    print(f"SQL A: {sql_a}")
    print(f"SQL B: {sql_b}")
    
    if sql_a == sql_b:
        print("FAIL: The layer is still returning the exact same query for both questions!")
        sys.exit(1)
    else:
        print("SUCCESS: The NL-to-SQL layer is fully connected and generating dynamic queries!")

if __name__ == "__main__":
    test_nl_query()
