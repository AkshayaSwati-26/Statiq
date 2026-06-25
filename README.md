# MoSPI Platform (StatIQ) - Unified Data Stack

Welcome to the **MoSPI Platform (StatIQ)**. This is a comprehensive, AI-powered platform for data ingestion, processing, querying, and visualization, designed for robust statistical data analysis (e.g., PLFS, HCES Health datasets). The platform provides a modern unified stack that leverages advanced Natural Language processing to query databases intuitively.

---

## 🚀 Key Features & Functionalities

### 1. AI-Powered Natural Language Querying (NL2SQL)
- **Natural Language to SQL:** Ask complex questions about the data in natural language. The AI layer intelligently translates these into optimized SQL queries.
- **Multilingual Support:** The system includes multilingual capabilities, breaking down language barriers in data querying.
- **Local AI Engine:** Powered by **Ollama**, ensuring complete data privacy by running language models locally.
- **Context-Aware:** Employs dynamic context building and intelligent query classification to generate accurate, schema-aware queries.

### 2. Automated Data Ingestion & Processing
- **Airflow Orchestration:** Uses **Apache Airflow** to orchestrate complex Data Directed Acyclic Graphs (DAGs) for automated data ingestion (e.g., `dag_hces_health.py`, `dag_plfs.py`).
- **FWF & Parquet Processing:** Highly capable of parsing Fixed Width Files (FWF), running transformations, generating statistical metadata, and exporting to optimized Parquet formats.
- **Metadata Management:** Automatically extracts and structures metadata during the ingestion phase for downstream discovery.

### 3. Modern Frontend Dashboard
A sleek, responsive, and dynamic UI built with **React** and **Vite**:
- **Query Workspace:** An intuitive interface for users to type natural language queries, view generated SQL, and analyze results.
- **Dataset Explorer:** Browse available datasets, view schemas, metadata, and statistical indicators.
- **Results Dashboard & Query History:** Visualize query results seamlessly and trace back past queries.
- **Data Ingestion Portal:** Monitor the status of Airflow DAGs, raw uploads, and processed data streams directly from the UI.
- **Admin Portal:** Comprehensive administrative tools including User Management, Audit Logs, Dataset Access Control, and Data Sensitivity configurations.

### 4. High-Performance API Backend
Built on **FastAPI** (Python), delivering high-speed async performance:
- **Comprehensive Routers:** Modular architecture handling Authentication, Queries, Metadata, Indicators, and Admin functions.
- **Security & Auth:** Secure JWT-based authentication combined with RSA key encryption and SMTP email verification (via Brevo).
- **Data Security:** Implements dataset-level access control and column-level data sensitivity filtering.

### 5. Robust Storage Stack
- **PostgreSQL 16 + TimescaleDB:** Primary relational database heavily optimized for time-series and large-scale statistical data.
- **MinIO Object Storage:** S3-compatible high-performance object storage used for housing raw data and processed Parquet files.
- **Redis 7:** High-speed in-memory cache used for accelerating NL-SQL query translations and API rate limiting.

---

## 🏗️ Architecture Stack

- **Frontend:** React, Vite, Nginx
- **Backend API:** FastAPI, Python 3.10+
- **AI Engine:** Ollama (Local LLM Deployment)
- **Databases:** PostgreSQL (TimescaleDB), Redis
- **Object Storage:** MinIO
- **Orchestration:** Apache Airflow
- **Containerization:** Docker & Docker Compose

---

## 🛠️ System Requirements

### Hardware Requirements
- **RAM**: Minimum 8GB (16GB recommended due to multiple services including Ollama and Airflow)
- **CPU**: 4 cores minimum
- **Storage**: At least 20GB of free space

### Software Prerequisites
Ensure you have the following installed on your system:
- [Docker](https://docs.docker.com/get-docker/) (v20.10 or higher)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0 or higher)
- [Git](https://git-scm.com/downloads)

*(Optional for local non-Docker development)*:
- Python 3.10+
- Node.js (v18+) & npm

---

## 💻 Step-by-Step Installation

### Step 1: Clone the Repository
Open your terminal/command prompt and clone the project repository to your local machine:
```bash
git clone <repository_url> mospi-platform
cd mospi-platform
```

### Step 2: Environment Configuration
The platform requires certain environment variables to run. A sample configuration file is provided.
1. Copy the `.env.example` file to create a new `.env` file:
   ```bash
   cp .env.example .env
   ```
   *(On Windows Command Prompt, use `copy .env.example .env`)*
2. Open the `.env` file in your preferred text editor and update any required keys (e.g., `JWT_SECRET`, `SMTP_USERNAME`, `SMTP_PASSWORD`, etc.).

### Step 3: Start the Platform using Docker Compose
The entire stack is containerized. To download the necessary images and start all services in the background, run:
```bash
docker-compose up -d
```
*Note: The first run may take several minutes as it downloads large images (PostgreSQL, TimescaleDB, Airflow, Ollama, etc.) and builds the API and Frontend containers.*

### Step 4: Verify the Installation
Check the status of all running containers:
```bash
docker-compose ps
```
All services should show a status of `Up` or `healthy`. If any service is restarting or failing, you can check its logs by running:
```bash
docker-compose logs -f <service_name>
```
*(Example: `docker-compose logs -f api`)*

---

## 🌐 Accessing the Services

Once the stack is successfully running, you can access the various services at the following local endpoints:

| Service | URL | Default Credentials / Info |
|---------|-----|----------------------------|
| **Frontend Application** | `http://localhost:3000` | Main User Interface |
| **Backend API** | `http://localhost:8000` | FastAPI Layer |
| **pgAdmin (Database Viewer)**| `http://localhost:5050` | **Email**: `admin@statiq.com` <br> **Password**: `admin` |
| **PostgreSQL (TimescaleDB)** | `localhost:5434` | **User**: `statiq` <br> **Password**: `statiq123` <br> **DB**: `statiq` |
| **MinIO (Object Storage)** | `http://localhost:9001` | **User**: `statiq` <br> **Password**: `statiq123` |
| **Apache Airflow** | `http://localhost:8080` | **User**: `admin` <br> **Password**: `admin` |
| **Redis** | `localhost:6379` | Cache & Rate Limiting |
| **Ollama (AI Engine)** | `http://localhost:11434`| Local AI Model Engine |

---

## 🔧 Local Development Setup (Optional)

If you wish to run the backend or frontend outside of Docker for development purposes:

### Backend (Python API)
1. Ensure you have Python 3.10+ installed.
2. Navigate to the project root and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI server:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

### Frontend (React + Vite)
1. Ensure you have Node.js installed.
2. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```

---

## ⚙️ Managing the Platform

- **Stop all services**:
  ```bash
  docker-compose down
  ```
- **Stop services and remove data volumes** *(Warning: This will delete your database and MinIO data!)*:
  ```bash
  docker-compose down -v
  ```
- **Restart a specific service** (e.g., frontend):
  ```bash
  docker-compose restart frontend
  ```
- **Rebuild after making changes**:
  ```bash
  docker-compose up -d --build
  ```
