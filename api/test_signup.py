import requests
import sys

BASE_URL = "http://localhost:8000/v1/auth"

def test_signup_and_upgrade():
    print("=== STARTING USER SIGNUP & UPGRADE VERIFICATION ===")
    
    # 1. Test invalid password policy
    print("\n1. Testing weak password registration...")
    payload = {
        "email": "test_weak@univ.edu.in",
        "password": "weak", # Too short, missing chars
        "scope": "public"
    }
    r = requests.post(f"{BASE_URL}/register", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 400 or r.status_code == 422
    
    # 2. Test invalid admin registration (no passcode)
    print("\n2. Testing admin registration without passcode...")
    payload = {
        "email": "test_admin_fail@mospi.gov.in",
        "password": "StrongPassword123!",
        "scope": "admin"
    }
    r = requests.post(f"{BASE_URL}/register", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 403 or r.status_code == 422
    
    # 3. Test valid public user registration (Student/Researcher)
    print("\n3. Testing valid public registration...")
    import uuid
    random_id = uuid.uuid4().hex[:6]
    test_email = f"student_{random_id}@univ.edu.in"
    payload = {
        "email": test_email,
        "password": "StrongPassword123!",
        "scope": "public"
    }
    session = requests.Session() # to preserve cookie
    r = session.post(f"{BASE_URL}/register", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 200
    
    # Verify auth cookie is set
    cookies = session.cookies.get_dict()
    print(f"Cookies: {cookies}")
    assert "access_token" in cookies
    token = cookies["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 4. Check /me endpoint for new user
    print("\n4. Checking /me endpoint for new user...")
    r = session.get(f"{BASE_URL}/me", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 200
    data = r.json()
    assert data["scope"] == "public"
    
    # 5. Test upgrade to Premium
    print("\n5. Testing upgrade to premium...")
    r = session.post(f"{BASE_URL}/upgrade", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 200
    data = r.json()
    assert data["scope"] == "research"
    
    # Extract updated access token from cookies
    updated_token = session.cookies.get("access_token") or token
    upgraded_headers = {"Authorization": f"Bearer {updated_token}"}
    
    # 6. Verify /me now reports 'research' scope
    print("\n6. Checking /me after upgrade...")
    r = session.get(f"{BASE_URL}/me", headers=upgraded_headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 200
    data = r.json()
    assert data["scope"] == "research"
    
    # 7. Test Admin registration with correct passcode
    print("\n7. Testing admin registration with correct passcode...")
    admin_email = f"admin_{random_id}@mospi.gov.in"
    payload = {
        "email": admin_email,
        "password": "StrongPassword123!",
        "scope": "admin",
        "admin_passcode": "MoSPIAdmin2026"
    }
    r = requests.post(f"{BASE_URL}/register", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    assert r.status_code == 200
    
    print("\n=== ALL AUTOMATED TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    try:
        test_signup_and_upgrade()
    except AssertionError as e:
        print(f"Assertion failed! {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Test crashed: {e}")
        sys.exit(1)
