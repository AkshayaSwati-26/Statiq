# MoSPI Platform - Branch Integration & Unification Strategy

To successfully bring the isolated work of your team members into a single, cohesive application, you need to execute two distinct phases: **Git Branch Unification** (the version control merge process) and **Application Orchestration** (wiring the services together to run on a machine).

## 1. Git Branch Unification Strategy

Currently, the team is working in isolated branches (e.g., `dev/api`, `dev/database`, `dev/ai`, `dev/frontend`). The goal is to merge these into a `main` or `staging` branch without breaking each other's code.

### The "Trunk-Based" Merge Flow
1. **Establish the Integration Branch:** Ensure you have a central `staging` or `main` branch. This will be the single source of truth for the combined application.
2. **Merge Order (Dependency First):**
   - **Step 1: Merge `dev/database` (Member 1).** The database schema, ingestion pipelines, and the registry tables are the foundation. Merge this first.
   - **Step 2: Merge `dev/api` (Our current work).** The API layer depends on the database. Once merged, test that the API runs against the real database tables instead of the mocks.
   - **Step 3: Merge `dev/ai` (Member 3).** The AI layer depends on our AI Context Infrastructure and the Database. With both in `main`, Member 3 can merge their `nl_agent.py` logic which hooks into `context_builder.py`.
   - **Step 4: Merge `dev/frontend`.** The UI depends on all the backend APIs being stable and returning correct data.
3. **Handle Merge Conflicts:** Because you strictly followed a **Contract-Driven Design** (as we did with the AI context), merge conflicts should be minimal. If conflicts arise, they usually happen in configuration files (like `requirements.txt` or `.env`), which should be resolved manually.

---

## 2. Technical Orchestration (Docker Compose)

Once the code is merged into `main`, how does the platform actually "work together as one application"? 

You must use **Docker Compose**. It allows the Frontend, Backend, AI (Ollama), and PostgreSQL database to run simultaneously on the same network.

### The Combined Architecture

When all branches are merged, your `docker-compose.yml` should define the entire stack:

```yaml
version: '3.8'

services:
  # 1. Database Layer (Member 1)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mospi
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  # 2. AI Layer - Ollama Engine (Member 3)
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    # Ollama downloads Gemma 3 4B internally on first startup

  # 3. Backend API Layer (Our Work)
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/mospi
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - postgres
      - ollama
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000

  # 4. Frontend Visualization Layer
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api

volumes:
  pgdata:
  ollama_models:
```

### How the Data Flows Together:
1. **Frontend** makes a request: `POST http://localhost:8000/v1/query/nl` with `"What is the unemployment rate?"`
2. **Backend API (`api`)** receives the request and triggers `nl_agent.py`.
3. **AI Context Infrastructure** queries the `postgres` container to get the schema, relationships, and examples.
4. **`nl_agent.py`** sends the assembled context + user question to the `ollama` container running Gemma 3 4B.
5. **Ollama** generates the SQL and returns it to the Backend API.
6. **Backend API** executes the SQL against `postgres`, applies security masks, and sends the JSON results back to the **Frontend**.

> [!TIP]
> To launch the entire combined application locally, you simply run:
> `docker-compose up --build`
> This spins up the database, AI model, backend, and frontend simultaneously, linked on a private network.
