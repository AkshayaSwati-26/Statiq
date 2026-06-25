import requests
from security.auth import create_access_token

def test_admin_auth():
    # 1. Create a valid admin token
    token = create_access_token("admin", "admin")
    print("Generated token:", token)
    
    # 2. Call registrations endpoint using Cookies
    cookies = {"access_token": token}
    r = requests.get("http://localhost:8000/v1/admin/registrations", cookies=cookies)
    print("Status:", r.status_code)
    print("Response:", r.text)

if __name__ == "__main__":
    test_admin_auth()
