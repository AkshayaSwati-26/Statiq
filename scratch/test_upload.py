import requests

files = {'file': ('hces.csv', b'')}
r = requests.post("http://localhost:8000/upload", files=files)
print(r.status_code, r.text)
