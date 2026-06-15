"""
db/models.py
=============
Database Model Registry for MoSPI Platform.
The schema is defined in schema.sql (PostgreSQL/TimescaleDB),
and safe queries are handled in postgres_client.py.
"""

from db.postgres_client import SAFE_COLUMNS, MATERIALIZED_VIEWS
