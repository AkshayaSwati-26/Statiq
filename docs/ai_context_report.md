# MoSPI Platform - AI Context Infrastructure Report

## Overview
The **AI Context Infrastructure** has been successfully implemented to act as the secure, metadata-driven bridge between the Database/Ingestion Layer and the upcoming NL-to-SQL AI Layer (Gemma 3 4B via Ollama). 

This module adheres strictly to a contract-driven design, ensuring that the AI never queries the database raw tables directly, maintaining government-level security constraints (Read-only, no DDL, no schema modification).

---

## 1. Structure and Modules Implemented

### 1.1 Repository Layer
- **`ai/db_adapter.py`**: A SQLAlchemy-based repository (`AIContextRepository`) that interfaces directly with the PostgreSQL database. It looks for system registries (e.g., `metadata_registry`, `relationship_registry`). Crucially, it includes a robust fallback mechanism that serves structured mock data if the ingestion tables are not yet available, allowing parallel development.

### 1.2 Internal AI Services
These modules act as the **Single Source of Truth** for the AI layer:
- **`ai/metadata_service.py`**: Exposes the database schema, data dictionary, dataset profiles, and sensitive column maps.
- **`ai/relationship_service.py`**: Provides the join keys and relationships between tables (e.g., `plfs_household` → `plfs_person`).
- **`ai/suggestions_service.py`**: Fetches verified NL-to-SQL pairs for few-shot prompting.
- **`ai/query_classifier.py`**: Analyzes user questions to determine the query type (`aggregation`, `ranking`, `trend`, `comparison`, `distribution`).
- **`ai/context_builder.py`**: The master assembler that calls all services above and returns a unified JSON object `build_context(question)` containing everything the LLM needs to generate SQL.

### 1.3 REST API Layer
To ensure the Frontend UI stays synchronized with the AI's understanding of the data, the exact same contracts are exposed via FastAPI routers:
- **`api/routers/metadata_router.py`** (`/v1/metadata`, `/v1/data-dictionary`, `/v1/dataset-profile`, `/v1/sensitive-columns`)
- **`api/routers/relationship_router.py`** (`/v1/relationships`)
- **`api/routers/suggestions_router.py`** (`/v1/suggested-queries`)

All routers have been registered in `api/main.py`.

---

## 2. Instructions for Member 1 (Database & Ingestion Layer)

> [!IMPORTANT]
> Your responsibility is to ensure the physical tables are populated by the ingestion pipeline.

**Tasks:**
1. **Build the Registries:** You must ensure the following tables are created in the PostgreSQL database and populated dynamically as new survey datasets (PLFS, HCES, NSSO) are ingested:
   - `metadata_registry`
   - `relationship_registry`
   - `survey_registry`
   - `data_dictionary`
   - `dataset_profile`
   - `suggested_query_registry`
   - `sensitive_column_registry`
2. **Schema Matching:** Refer to `ai/db_adapter.py` to see the exact SQL queries being executed. For example, the metadata query runs: `SELECT table_name, column_name, data_type, description, sample_values FROM metadata_registry`. Your tables must match these column names exactly.
3. **No Hardcoding:** Do not hardcode PLFS or HCES logic into the tables. The tables must dynamically reflect whatever surveys have been loaded.

*Note: The AI layer currently uses the safe fallbacks in `db_adapter.py`. Once you populate the tables, the AI will automatically switch to using your live data without any code changes required in the `ai/` folder.*

---

## 3. Instructions for Member 3 (AI Layer & Gemma Integration)

> [!IMPORTANT]
> Your responsibility is to consume the context and generate valid SQL using Gemma 3 4B + Ollama.

**Tasks:**
1. **Do not connect to the DB directly:** You are strictly forbidden from writing SQLAlchemy or psycopg2 code inside `nl_agent.py` to read tables.
2. **Consume the Context:** Inside `nl_agent.py`, you must call `from ai.context_builder import build_context`.
3. **Prompt Injection:** Call `context = build_context(user_question)`. Inject the `context["schema"]`, `context["relationships"]`, and `context["examples"]` dynamically into your Gemma 3 4B system prompt.
4. **Use the Classifier:** Use `context["query_type"]` (which contains e.g., `aggregation` or `ranking`) to conditionally branch your prompt engineering strategy if needed.
5. **Output Requirement:** Your `nl_agent.py` must return the generated SQL string back to `api/routers/query.py`, which handles the actual read-only execution and cell suppression.

---

*End of Report.*
