# 🚀 StatIQ / MoSPI Platform

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg?logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2B%20Timescale-336791.svg?logo=postgresql)
![Airflow](https://img.shields.io/badge/Orchestrator-Airflow-017CEE.svg?logo=apache-airflow)

> **Modern, Containerized, and AI-Driven Data Platform.**

---

## ✨ Key Features & Functionalities

- 🔐 **Secure Access & Auth**: JWT-based authentication, RSA key pairs, and role-based access.
- ⚡ **High-Performance API**: Built on FastAPI for rapid response, async processing, and scalability.
- 🧠 **Local AI Engine**: Integrated Ollama for secure, local AI model execution (no external API needed).
- 📊 **Time-Series Ready DB**: PostgreSQL optimized with TimescaleDB for massive data handling.
- 📦 **S3-Compatible Data Lake**: MinIO object storage for raw files, Parquet, and processed datasets.
- 🔄 **ETL Orchestration**: Apache Airflow pipelines for automated data ingestion and scheduling.
- 🚀 **Blazing Fast Cache**: Redis 7 implementation for rate limiting and NL-SQL caching.
- 💻 **Modern Frontend UI**: React + Vite application served via Nginx for a snappy user experience.
- ✉️ **Automated Mailing**: Integrated SMTP (Brevo) for alerts and notifications.
- 🛡️ **Audit Logging**: Comprehensive action tracking and security event logging.
- 🛠️ **Visual DB Management**: pgAdmin included out-of-the-box for database administration.

---

## 🏗️ Architecture Layer Diagram

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

## 🚀 Quick Start (Docker)

- **Clone & Configure**: `cp .env.example .env` and adjust variables.
- **Start Services**: `docker-compose up -d`
- **Verify Status**: `docker-compose ps`

---

## 🌐 Endpoints & Services

| Service | Address | Default Credentials |
|:---|:---|:---|
| 🎨 **Frontend UI** | `http://localhost:3000` | - |
| 🔌 **Backend API** | `http://localhost:8000` | - |
| 🐘 **pgAdmin** | `http://localhost:5050` | `admin@statiq.com` / `admin` |
| 🪣 **MinIO Console**| `http://localhost:9001` | `statiq` / `statiq123` |
| ⏱️ **Airflow UI** | `http://localhost:8080` | `admin` / `admin` |
| 🤖 **Ollama Engine** | `http://localhost:11434`| - |

---

*Note: Run `docker-compose down -v` to fully reset the environment and wipe all database volumes.*
