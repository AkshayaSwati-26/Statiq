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

## 🌟 Vision (Statathon 2025)

Democratize access to India's official statistics so **policymakers, researchers, developers, and students** can derive insights without **technical barriers** — while preserving **privacy, accuracy, and scale.**

---

## 🛑 The Problem: Ground Reality Today

**Core Gap:** *Open data exists, but there is no unified, intelligent, no-code way to run flexible queries and retrieve insights in a user-friendly, API-ready form.*

- Survey data is released as **massive CSV/ZIP files**.
- Deriving insights requires complex **SQL, statistics, and preprocessing**.
- Policymakers are forced to depend on **delayed static reports**.
- Developers waste time rebuilding **duplicate data pipelines**.
- Non-technical users are effectively **locked out**.

### Why Existing Systems Fail

| Current Approach | The Limitation |
| :--- | :--- |
| **Raw CSV downloads** | Manual & error-prone |
| **GB-scale file downloads** | Slow policymaking |
| **Static dashboards** | No flexibility |
| **SQL-only access** | Excludes non-technical users |
| **Fragmented APIs** | No unified access |
| **No governance layer** | Risk & inefficiency |

---

## 💡 The Solution: How StatIQ Addresses the Problem

StatIQ eliminates bulky file downloads & manual filtering. It saves time, reduces errors, and makes data accessible to non-technical users while offering ready-to-use APIs for developers.

### 🎯 Impact & Feasibility

| 🚀 Feasibility | 🛡️ Security & Governance | 🇮🇳 National Impact |
| :--- | :--- | :--- |
| • Built on proven open-source technologies<br>• Modular & extensible architecture<br>• Easy integration with existing MoSPI systems<br>• Pilot-ready within hackathon scope | • Role-based access control<br>• Query validation & throttling<br>• API key management<br>• Full audit logs<br>• Privacy-by-design architecture | • ⏱️ 90% reduction in analysis time<br>• 📊 Faster, evidence-based policymaking<br>• 👥 Inclusive access to public data<br>• 🚀 Foundation for National Data APIs |

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

## 🚀 Detailed Setup & Installation Guide

Follow these step-by-step instructions to deploy the entire unified stack on your local machine using Docker. 

### Step 1: Clone the Repository
Open your terminal and clone the project to your local workspace:
```bash
git clone <repository_url> mospi-platform
cd mospi-platform
```

### Step 2: Environment Configuration
The platform relies on `.env` variables for secure credentials and configurations. 
1. Copy the sample environment file:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file in your editor and configure the necessary keys (e.g., `JWT_SECRET`, Database credentials, or SMTP configurations).

### Step 3: Launch the Docker Containers
The entire stack is containerized. Start the platform by downloading the images and booting the services in detached mode:
```bash
docker-compose up -d
```
> ⏳ *Note: The initial setup may take 5-15 minutes depending on your internet connection, as it pulls heavy images (PostgreSQL, Airflow, Ollama) and builds the local API and Frontend containers.*

### Step 4: Verify the Deployment
Ensure that all services started successfully without crashing:
```bash
docker-compose ps
```
> ✅ *Check that all services display a state of `Up` or `healthy`.* If a service fails, you can inspect it with `docker-compose logs -f <service_name>`.

---

## 🌐 Services & Endpoints Directory

Once the stack is running successfully, you can access the various services at these local endpoints:

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

If you wish to modify code and debug outside of the Docker network, use the following manual setup instructions:

### Backend (Python API)
> 🐍 *Requires Python 3.10+*
```bash
# Navigate to project root and install dependencies
pip install -r requirements.txt

# Run the FastAPI server locally
uvicorn api.main:app --reload --port 8000
```

### Frontend (React + Vite)
> 🟢 *Requires Node.js (v18+)*
```bash
# Navigate to the frontend folder
cd frontend

# Install Node modules
npm install

# Start the Vite development server
npm run dev
```

---

## ⚙️ Lifecycle Management

Master your local Docker environment with these essential commands:

*   **Stop Safely**: Shut down all containers without losing data.
    ```bash
    docker-compose down
    ```
*   **Wipe All Data** ⚠️ *(Warning: Deletes database, cache, and MinIO volumes permanently!)*: 
    ```bash
    docker-compose down -v
    ```
*   **Restart Specific Service** *(e.g., apply a quick configuration change)*: 
    ```bash
    docker-compose restart frontend
    ```
*   **Rebuild Image After Code Changes**: If you update the `Dockerfile` or `requirements.txt`:
    ```bash
    docker-compose up -d --build api
    ```

---
<div align="center">
  <i>Built with ❤️ for Statathon 2025 – Modern data engineering and AI analytics.</i>
</div>
