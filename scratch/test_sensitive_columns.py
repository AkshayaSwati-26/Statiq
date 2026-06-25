import requests
from security.auth import create_access_token

def test_sensitive_columns():
    token = create_access_token("admin", "admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get("http://localhost:8000/v1/admin/sensitive-columns", headers=headers)
    print("Status:", r.status_code)
    try:
        data = r.json()
        print(f"Number of columns returned: {len(data)}")
        if len(data) > 0:
            print("First few columns:")
            for item in data[:5]:
                print(f"  - Table: {item['table_name']}, Column: {item['column_name']}, DataType: {item['data_type']}, Sensitive: {item['is_sensitive']}")
    except Exception as e:
        print("Response text:", r.text)
        print("Error parsing JSON:", e)

if __name__ == "__main__":
    test_sensitive_columns()
