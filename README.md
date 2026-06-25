<div align="center">
  <h1>🚀 StatIQ / MoSPI Platform</h1>
  <p><b>A Modern, Containerized, and AI-Driven Data Intelligence Platform</b></p>
  <p><i>Built for STATATHON 2025</i></p>
  
  ![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge)
  ![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=for-the-badge&logo=docker)
  ![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg?style=for-the-badge&logo=react)
  ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=for-the-badge&logo=fastapi)
  ![PostgreSQL](https://img.shields.io/badge/Database-Postgres%2B%20Timescale-336791.svg?style=for-the-badge&logo=postgresql)
  ![Airflow](https://img.shields.io/badge/Orchestrator-Airflow-017CEE.svg?style=for-the-badge&logo=apache-airflow)
</div>

---

## 🎯 Vision
Democratize access to India's official statistics so **policymakers, researchers, developers, and students** can derive insights without technical barriers — while preserving **privacy, accuracy, and scale**.

---

## 🚧 The Core Gap & Ground Reality Today

**Core Gap:** Open data exists, but there is no unified, intelligent, no-code way to run flexible queries and retrieve insights in a user-friendly, API-ready form.

Currently, dealing with official data presents several challenges:
- Survey data is released as **massive CSV/ZIP files**.
- Deriving insights requires **SQL, statistics, and complex preprocessing**.
- Policymakers depend on **delayed static reports**.
- Developers constantly rebuild **duplicate data pipelines**.
- Non-technical users are completely **locked out**.

### Why Existing Systems Fail

| Current Approach | Limitation |
| :--- | :--- |
| Raw CSV downloads | Manual & error-prone |
| GB-scale file downloads | Slow policymaking |
| Static dashboards | No flexibility |
| SQL-only access | Excludes non-technical users |
| Fragmented APIs | No unified access |
| No governance layer | Risk & inefficiency |

---

## 💡 The StatIQ Solution

StatIQ eliminates bulky file downloads & manual filtering. It saves time, reduces errors, and makes data accessible to non-technical users while offering ready-to-use APIs for developers.

### 🇮🇳 National Impact
- ⏱️ **90% reduction** in analysis time.
- 📊 Faster, **evidence-based policymaking**.
- 👥 **Inclusive access** to public data.
- 🚀 Foundation for **National Data APIs**.

### 🛡️ Security & Governance
- **Role-based access control** ensuring data privacy.
- **Query validation & throttling** for platform stability.
- **API key management** for external integrations.
- **Full audit logs** tracking all interactions.
- **Privacy-by-design architecture**.

### ⚙️ Feasibility
- Built entirely on **proven open-source technologies**.
- **Modular & extensible architecture**.
- Designed for **easy integration** with existing MoSPI systems.
- Pilot-ready within the hackathon scope.

---

## 🏗️ System Architecture

Our platform follows a modular, microservices-oriented approach where each component operates securely inside its own isolated Docker container.

```mermaid
graph TD
    %% Styling
    classDef frontend fill:#61DAFB,stroke:#fff,stroke-width:2px,color:#000;
    classDef backend fill:#009688,stroke:#fff,stroke-width:2px,color:#fff;
    classDef database fill:#336791,stroke:#fff,stroke-width:2px,color:#fff;
    classDef dataeng fill:#017CEE,stroke:#fff,stroke-width:2px,color:#fff;
    classDef ai fill:#FF9900,stroke:#fff,stroke-width:2px,color:#fff;
    
    User([👤 User / Client])
    
    subgraph "🖥️ Presentation Layer"
        FE[⚛️ React + Vite UI]:::frontend
    end
    
    subgraph "⚙️ Application Layer"
        API[🚀 FastAPI Backend]:::backend
        Redis[⚡ Redis Cache]:::backend
    end
    
    subgraph "🧠 Intelligence Layer"
        Ollama[🤖 Ollama Engine]:::ai
    end
    
    subgraph "🗄️ Storage Layer"
        DB[(🐘 PostgreSQL + Timescale)]:::database
        MinIO[(🪣 MinIO Data Lake)]:::database
    end
    
    subgraph "🔄 Pipeline Layer"
        Airflow[⏱️ Apache Airflow]:::dataeng
    end

    %% Connections
    User -->|HTTP/HTTPS| FE
    FE -->|REST API| API
    API <-->|Rate Limit / Cache| Redis
    API <-->|Prompts / Inference| Ollama
    API <-->|SQL Queries| DB
    API <-->|S3 API| MinIO
    Airflow -->|ETL Jobs| DB
    Airflow -->|Read/Write Parquet| MinIO
```

---

## ✨ Core Platform Functionalities

- 🔌 **High-Performance Routing:** Built on Python's FastAPI, ensuring lightning-fast, asynchronous request handling.
- 🤖 **NL-SQL Caching:** Natural Language to SQL conversions are intelligently cached in Redis to drastically reduce AI overhead and latency.
- 🧠 **Local LLM Engine:** Utilizes Ollama directly inside the cluster, meaning zero data leaves your environment for inference tasks.
- 🗄️ **Time-Series Optimization:** PostgreSQL paired with TimescaleDB easily handles millions of chronological data points.
- 📦 **Object Storage (Data Lake):** S3-compatible MinIO handles raw files, Parquet datasets, and unstructured binary assets.
- 🔄 **Automated ETL Pipelines:** Apache Airflow automates the ingestion, cleaning, and staging of incoming data streams.

---

## 📁 Repository Structure

```text
mospi-platform/
├── 📁 ai/               # AI models, prompts, and Ollama integration logic
├── 📁 airflow/          # Airflow DAGs (Directed Acyclic Graphs) and pipelines
├── 📁 api/              # Core FastAPI application (Routes, Controllers, Models)
├── 📁 data/             # Local data storage mounts (Ignored in Git)
├── 📁 db/               # Database schemas, migrations, and initialization scripts
├── 📁 docker/           # Custom Dockerfiles and build scripts for services
├── 📁 frontend/         # React + Vite user interface application
├── 📁 ingestion/        # Scripts for raw data ingestion and parsing
├── 📁 keys/             # RSA Public/Private keys for JWT signing
├── 📁 security/         # Authentication logic, middleware, and audit trails
├── 📁 tests/            # Unit and Integration test suites
├── 📄 docker-compose.yml# Master orchestration file
└── 📄 requirements.txt  # Python backend dependencies
```

---

## 🚀 Comprehensive Setup & Installation Guide

### Step 1: Verify System Requirements
Before proceeding, ensure your host machine meets the following specifications:
*   **RAM**: Minimum 8GB *(16GB is highly recommended to comfortably run Airflow and the Local AI models simultaneously)*
*   **CPU**: Minimum 4 Cores
*   **Storage**: 20GB of free SSD space
*   **Software**: 
    *   Docker Engine (v20.10 or higher)
    *   Docker Compose (v2.0 or higher)
    *   Git installed on your system

### Step 2: Clone the Repository
Open your terminal and clone the repository to your local machine:
```bash
git clone <repository_url> mospi-platform
cd mospi-platform
```

### Step 3: Configure Environment Variables
The platform relies on a `.env` file to manage secrets and configurations.
1. Create a copy of the provided template:
   ```bash
   cp .env.example .env
   ```
2. Open the newly created `.env` file in your preferred code editor.
3. Review and update critical variables (e.g., `JWT_SECRET`, database credentials, SMTP details) as required for your deployment environment.

### Step 4: Initialize and Start the Platform
Once configured, use Docker Compose to download, build, and start all microservices:
```bash
docker-compose up -d
```
> ⏳ **Important Note:** The initial execution may take **5 to 15 minutes**. Docker needs to download several heavy images (including PostgreSQL, Airflow, and the Ollama AI engine) and build the local FastAPI and React containers. Grab a coffee! ☕

### Step 5: Verify Deployment Status
Check that all containers have spun up correctly:
```bash
docker-compose ps
```
You should see all containers mapped to their respective ports with a status of `Up` or `healthy`. If a container repeatedly restarts, you can inspect its logs using:
```bash
docker-compose logs -f <service_name>
```

---

## 🌐 Services & Endpoints Directory

Once the stack is successfully running, you can access the various interconnected services through your web browser:

| Service | Local Address | Default Credentials | Purpose |
|:---|:---|:---|:---|
| 🎨 **Frontend UI** | `http://localhost:3000` | - | Main user-facing application |
| 🔌 **Backend API** | `http://localhost:8000` | - | Core API routing (Swagger UI: `/docs`) |
| 🐘 **pgAdmin Viewer** | `http://localhost:5050` | `admin@statiq.com` / `admin` | Visual DB management |
| 🪣 **MinIO Console**| `http://localhost:9001` | `statiq` / `statiq123` | Manage S3 object storage |
| ⏱️ **Airflow UI** | `http://localhost:8080` | `admin` / `admin` | Monitor ETL workflows and DAGs |
| 🤖 **Ollama Engine** | `http://localhost:11434`| - | API for the local AI models |
| 🗄️ **TimescaleDB** | `localhost:5434` | `statiq` / `statiq123` | Direct SQL access (DB: `statiq`) |
| ⚡ **Redis Cache** | `localhost:6379` | - | Internal rate limiting & cache |

---

## ⚙️ Lifecycle Management Commands

Master your local Docker environment with these essential commands:

*   **Graceful Shutdown** (Stops all running services without deleting data): 
    ```bash
    docker-compose down
    ```
*   **Complete System Reset** ⚠️ *(Warning: Permanently deletes all database, cache, and MinIO volumes)*: 
    ```bash
    docker-compose down -v
    ```
*   **Restart a Single Service** *(Example: Applying a frontend code change)*: 
    ```bash
    docker-compose restart frontend
    ```
*   **Force Rebuild a Service** *(Example: Rebuilding the API after altering `requirements.txt`)*: 
    ```bash
    docker-compose up -d --build api
    ```

---
<div align="center">
  <i>Built with ❤️ for STATATHON 2025. Empowering evidence-based policymaking through accessible data.</i>
</div>
