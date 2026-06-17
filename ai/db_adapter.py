import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.loader import engine

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
        if not results:
            # Fallback mock
            return [
                {"table_name": "api_plfs_person", "column_name": "state_name", "data_type": "varchar", "description": "State name", "sample_values": '["Tamil Nadu", "Kerala"]'},
                {"table_name": "api_plfs_person", "column_name": "sector_label", "data_type": "varchar", "description": "Rural or Urban", "sample_values": '["Rural", "Urban"]'},
                {"table_name": "api_plfs_person", "column_name": "gender_label", "data_type": "varchar", "description": "Gender", "sample_values": '["Male", "Female"]'},
                {"table_name": "api_plfs_person", "column_name": "age", "data_type": "integer", "description": "Age in years", "sample_values": "[25, 45]"},
                {"table_name": "api_plfs_person", "column_name": "usual_activity", "data_type": "varchar", "description": "Usual activity status code", "sample_values": '["11", "51", "81"]'},
                {"table_name": "api_plfs_person", "column_name": "employment_status", "data_type": "varchar", "description": "Employed, Unemployed, or Out of Labour Force", "sample_values": '["Employed", "Unemployed"]'},
                {"table_name": "api_plfs_person", "column_name": "in_labour_force", "data_type": "integer", "description": "1 if in labour force, 0 otherwise", "sample_values": "[0, 1]"},
                {"table_name": "api_plfs_person", "column_name": "is_employed", "data_type": "integer", "description": "1 if employed, 0 otherwise", "sample_values": "[0, 1]"},
                {"table_name": "api_plfs_person", "column_name": "multiplier", "data_type": "numeric", "description": "Survey weight multiplier", "sample_values": "[1200.5]"},
                {"table_name": "api_plfs_person", "column_name": "survey_year", "data_type": "varchar", "description": "Survey year", "sample_values": '["2023-24"]'},
                
                {"table_name": "api_hces_members", "column_name": "state_name", "data_type": "varchar", "description": "State name", "sample_values": '["Tamil Nadu", "Kerala"]'},
                {"table_name": "api_hces_members", "column_name": "sector_label", "data_type": "varchar", "description": "Rural or Urban", "sample_values": '["Rural", "Urban"]'},
                {"table_name": "api_hces_members", "column_name": "gender_label", "data_type": "varchar", "description": "Gender", "sample_values": '["Male", "Female"]'},
                {"table_name": "api_hces_members", "column_name": "age", "data_type": "integer", "description": "Age in years", "sample_values": "[25, 45]"},
                {"table_name": "api_hces_members", "column_name": "hospitalised", "data_type": "integer", "description": "1 if hospitalised in last 365 days, 0 otherwise", "sample_values": "[0, 1]"},
                {"table_name": "api_hces_members", "column_name": "insurance_label", "data_type": "varchar", "description": "Health insurance coverage", "sample_values": '["AB-PMJAY", "Not covered"]'},
                {"table_name": "api_hces_members", "column_name": "multiplier", "data_type": "numeric", "description": "Survey weight multiplier", "sample_values": "[1200.5]"},
                {"table_name": "api_hces_members", "column_name": "survey_year", "data_type": "varchar", "description": "Survey year", "sample_values": '["2023-24"]'}
            ]
        return results

    def get_relationship_registry(self):
        query = "SELECT parent_table, child_table, join_key, relationship_type FROM relationship_registry"
        results = self._execute_query(query)
        if not results:
            # Fallback mock
            return [
                {
                    "parent_table": "api_hces_hh",
                    "child_table": "api_hces_members",
                    "join_key": "hh_serial",
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
        if not results:
            return [
                {"table_name": "api_plfs_person", "column_name": "sector", "definition": "1 for rural, 2 for urban"},
                {"table_name": "api_plfs_person", "column_name": "gender", "definition": "1 for male, 2 for female"},
                {"table_name": "api_hces_members", "column_name": "gender", "definition": "1 for male, 2 for female"}
            ]
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
