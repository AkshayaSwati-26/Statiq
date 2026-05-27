# MoSPI API Contract

Base URL: http://localhost:8000

## Endpoints

### GET /health
Response: { "status": "ok" }

### GET /v1/indicators/unemployment-rate
Params: year (int), state (int, optional), sector (int, optional)
Auth: Bearer token
Response: { "year": 2023, "count": 28, "data": [{ "state_code": 1, "rate": 12.3 }] }

### POST /v1/query/nl
Body: { "question": "string" }
Auth: Bearer token
Response: { "sql": "...", "explanation": "...", "data": [...], "count": 5 }

### POST /v1/auth/token
Body: { "user_id": "string", "scope": "public|research|admin" }
Response: { "token": "..." }
