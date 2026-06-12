import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

try:
    from db.loader import engine
except ImportError:
    from api.mock_db import engine

logger = logging.getLogger(__name__)

class AIContextRepository:
    """
    Repository for accessing the database registries (metadata, relationships, suggestions).
    Uses safe fallback data if the registry tables don't exist yet in the database.
    """
    def __init__(self):
        self.engine = engine

    def _execute_query(self, query: str, params: dict = None):
        """Helper to execute SQL queries and fetch results safely."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.warning(f"Database query failed or table not found: {e}")
            return None

    def get_metadata_registry(self, survey_id: str = None):
        query = "SELECT table_name, column_name, data_type, description, sample_values FROM metadata_registry"
        params = {}
        if survey_id:
            query += " WHERE survey_id = :survey_id"
            params["survey_id"] = survey_id
        
        results = self._execute_query(query, params)
        if results is None:
            # Fallback mock
            return [
                {
                    "table_name": "plfs_person",
                    "column_name": "usual_activity_status",
                    "data_type": "integer",
                    "description": "Principal activity status code",
                    "sample_values": "[11, 21, 31, 81, 82]"
                }
            ]
        return results

    def get_relationship_registry(self):
        query = "SELECT parent_table, child_table, join_key, relationship_type FROM relationship_registry"
        results = self._execute_query(query)
        if results is None:
            # Fallback mock
            return [
                {
                    "parent_table": "plfs_household",
                    "child_table": "plfs_person",
                    "join_key": "household_id",
                    "relationship_type": "one_to_many"
                }
            ]
        return results

    def get_suggested_queries(self):
        query = "SELECT question, sql_query, category FROM suggested_query_registry"
        results = self._execute_query(query)
        if results is None:
            # Fallback mock
            return [
                {
                    "question": "What is the unemployment rate in rural areas?",
                    "sql_query": "SELECT ...",
                    "category": "aggregation"
                }
            ]
        return results

    def get_data_dictionary(self):
        query = "SELECT table_name, column_name, definition FROM data_dictionary"
        results = self._execute_query(query)
        if results is None:
            return [{"table_name": "plfs_person", "column_name": "sector", "definition": "1 for rural, 2 for urban"}]
        return results

    def get_dataset_profile(self):
        query = "SELECT profile_key, profile_value FROM dataset_profile"
        results = self._execute_query(query)
        if results is None:
            return [{"profile_key": "total_records", "profile_value": "100000"}]
        return results

    def get_sensitive_columns(self):
        query = "SELECT table_name, column_name, sensitivity_level FROM sensitive_column_registry"
        results = self._execute_query(query)
        if results is None:
            return [{"table_name": "plfs_person", "column_name": "pii_name", "sensitivity_level": "high"}]
        return results

# Singleton instance
repository = AIContextRepository()
