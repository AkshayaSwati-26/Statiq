<div align="center">
  <h1>🚀 StatIQ / MoSPI Platform</h1>
  <p><b>A Modern, Containerized, and AI-Driven Data Intelligence Platform</b></p>
  
  ![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge)
  ![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=for-the-badge&logo=docker)
  ![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg?style=for-the-badge&logo=react)
  ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=for-the-badge&logo=fastapi)
  ![PostgreSQL](https://img.shields.io/badge/Database-Postgres%2B%20Timescale-336791.svg?style=for-the-badge&logo=postgresql)
  ![Airflow](https://img.shields.io/badge/Orchestrator-Airflow-017CEE.svg?style=for-the-badge&logo=apache-airflow)
</div>

---

## 📖 Project Overview

**StatIQ** (MoSPI Platform) is a comprehensive, full-stack data platform designed for scalable data ingestion, secure processing, and intelligent analysis. By combining a high-performance backend, time-series optimized databases, and an integrated local AI engine, StatIQ offers a complete ecosystem for managing vast datasets without relying on external cloud APIs.

Whether you are performing complex ETL tasks, running AI-driven queries over local data, or managing user access securely, this platform provides a **simple, clear, and professional** infrastructure.

---

## 🏗️ System Architecture

Our platform follows a modular, microservices-oriented approach where each component operates inside its own isolated Docker container.

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

## ✨ Core Functionalities

### 🛡️ Security & Authentication
- **Role-Based Access Control (RBAC):** Granular permissions for admins and standard users.
- **JWT & RSA Encryption:** Secure token-based authentication backed by robust asymmetric key pairs.
- **Comprehensive Audit Logging:** Track every sensitive action and security event within the platform.

### 🔌 API & Application Logic
- **High-Performance Routing:** Built on Python's FastAPI, ensuring lightning-fast, asynchronous request handling.
- **NL-SQL Caching:** Natural Language to SQL conversions are intelligently cached in Redis to drastically reduce AI overhead and latency.
- **Automated Mailing Service:** SMTP integration via Brevo for reliable system alerts and user notifications.

### 🧠 Integrated Artificial Intelligence
- **Local LLM Engine:** Utilizes Ollama directly inside the cluster, meaning zero data leaves your environment for inference tasks.
- **Context-Aware Analytics:** The AI layers can natively query your Postgres databases and translate natural language directly into actionable data insights.

### 🗄️ Data Storage & Orchestration
- **Time-Series Optimization:** PostgreSQL paired with TimescaleDB easily handles millions of chronological data points.
- **Object Storage (Data Lake):** S3-compatible MinIO handles raw files, Parquet datasets, and unstructured binary assets.
- **Automated ETL Pipelines:** Apache Airflow automates the ingestion, cleaning, and staging of incoming data streams.

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

## 💻 System Requirements

**Hardware Requirements**
*   **RAM**: 8GB Minimum 🚀 *(16GB Recommended due to AI & Airflow memory usage)*
*   **CPU**: 4 Cores Minimum
*   **Storage**: 20GB+ Free Space (SSD highly recommended)

**Software Prerequisites**
*   🐳 [Docker (v20.10+)](https://docs.docker.com/get-docker/) & Docker Compose
*   🌿 [Git](https://git-scm.com/downloads)

---

## 🚀 Quick Start (Docker)

Get the entire stack up and running locally in a few simple steps:

1. **Clone the Repository**
   ```bash
   git clone <repository_url> mospi-platform
   cd mospi-platform
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   > 📝 *Open `.env` and configure any required API keys or secrets (e.g., `JWT_SECRET`, database passwords).*

3. **Launch the Platform**
   ```bash
   docker-compose up -d
   ```
   > ⏳ *Note: The initial setup may take 5-10 minutes as it downloads large Docker images (PostgreSQL, Airflow, Ollama) and builds local containers.*

4. **Verify Deployment**
   ```bash
   docker-compose ps
   ```
   > ✅ *All services should display an `Up` or `healthy` state.*

---

## 🌐 Services & Endpoints Directory

Once running, access your local services seamlessly:

| Service | Address | Default Credentials / Purpose |
|:---|:---|:---|
| 🎨 **Frontend UI** | `http://localhost:3000` | User-facing dashboard |
| 🔌 **Backend API** | `http://localhost:8000` | Core API Layer (Swagger UI: `/docs`) |
| 🐘 **pgAdmin Viewer** | `http://localhost:5050` | `admin@statiq.com` / `admin` |
| 🪣 **MinIO Console**| `http://localhost:9001` | `statiq` / `statiq123` |
| ⏱️ **Airflow UI** | `http://localhost:8080` | `admin` / `admin` |
| 🤖 **Ollama Engine** | `http://localhost:11434`| Local AI Model Engine API |
| 🗄️ **TimescaleDB** | `localhost:5434` | `statiq` / `statiq123` (Database: `statiq`) |
| ⚡ **Redis Cache** | `localhost:6379` | Cache & Rate Limiting |

---

## 🛠️ Local Development Guide (Optional)

If you prefer to run and debug the application components outside of Docker:

### Backend (Python API)
> 🐍 *Requires Python 3.10+*
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Frontend (React + Vite)
> 🟢 *Requires Node.js (v18+)*
```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ Lifecycle Management

Master your local Docker environment with these essential commands:

*   **Stop Safely**: 
    ```bash
    docker-compose down
    ```
*   **Wipe All Data** ⚠️ *(Warning: Deletes database, cache, and MinIO volumes permanently)*: 
    ```bash
    docker-compose down -v
    ```
*   **Restart Specific Service** *(e.g., apply a quick configuration change)*: 
    ```bash
    docker-compose restart frontend
    ```
*   **Rebuild Image After Code Changes**: 
    ```bash
    docker-compose up -d --build api
    ```

---
<div align="center">
  <i>Built with ❤️ for modern data engineering and AI analytics.</i>
</div>
