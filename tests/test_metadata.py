import sys
import os
import pytest
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


from ingestion.metadata_generator import (
    extract_column_metadata,
    extract_dictionary_metadata,
    generate_relationship_metadata,
    generate_suggested_queries,
    generate_sample_values,
    generate_dataset_profile
)
from db.postgres_client import StatIQDB


class TestMetadataGenerator:

    @pytest.fixture
    def mock_df(self):
        return pd.DataFrame({
            "st": ["33", "28", "27"],
            "gender_label": ["Male", "Female", "Male"],
            "multiplier": [1000.0, 2000.0, 1500.0],
            "age": [25, 30, 45],
            "fsu_serial": ["10001", "10002", "10003"]
        })

    @pytest.fixture
    def mock_layout(self):
        return {
            "fields": [
                {"name": "st", "full_name": "State Code", "remarks": "State numerical code identifier"}
            ]
        }

    @pytest.fixture
    def mock_codebook(self):
        return {
            "st": {"33": "Tamil Nadu", "28": "Andhra Pradesh"}
        }

    def test_extract_column_metadata(self, mock_df, mock_layout):
        cols = extract_column_metadata("plfs", "plfs_person", mock_df, mock_layout)
        assert len(cols) == 5
        
        # Check standard layout map lookup
        st_col = next(c for c in cols if c["column_name"] == "st")
        assert "State" in st_col["description"]
        assert st_col["data_type"] == "varchar"
        assert st_col["is_sensitive"] is False

        # Check static derived map lookup
        gender_col = next(c for c in cols if c["column_name"] == "gender_label")
        assert "Gender" in gender_col["description"]
        assert gender_col["is_sensitive"] is False

        # Check multiplier float casting
        mult_col = next(c for c in cols if c["column_name"] == "multiplier")
        assert mult_col["data_type"] == "numeric"

        # Check sensitive column identifier
        fsu_col = next(c for c in cols if c["column_name"] == "fsu_serial")
        assert fsu_col["is_sensitive"] is True

    def test_extract_dictionary_metadata(self, mock_codebook):
        dictionary = extract_dictionary_metadata("plfs", mock_codebook)
        assert len(dictionary) > 0
        
        # Check codebook value
        tn_val = next(d for d in dictionary if d["variable_name"] == "st" and d["code"] == "33")
        assert tn_val["code_description"] == "Tamil Nadu"

        # Check transform value mapping (e.g. usual_activity maps)
        act_val = next(d for d in dictionary if d["variable_name"] == "usual_activity" and d["code"] == "11")
        assert "Self-employed" in act_val["code_description"]

    def test_generate_relationship_metadata(self):
        rels = generate_relationship_metadata("hces_health")
        assert len(rels) == 2
        assert rels[0]["parent_table"] == "hces_health_hh"
        assert rels[0]["child_table"] == "hces_health_members"
        assert "fsu_serial" in rels[0]["join_keys"]

    def test_generate_suggested_queries(self):
        queries = generate_suggested_queries("plfs")
        assert len(queries) == 3
        assert queries[0]["title"] == "Weighted Labour Force Participation Rate (LFPR) by State"
        assert "plfs_person" in queries[0]["sql_query"]

    def test_generate_sample_values(self, mock_df):
        samples = generate_sample_values("plfs", "plfs_person", mock_df)
        # gender_label and st have cardinality <= 60
        # fsu_serial, multiplier are skipped/numeric
        col_names = [s["column_name"] for s in samples]
        assert "gender_label" in col_names
        assert "st" in col_names
        assert "multiplier" not in col_names
        assert "fsu_serial" not in col_names

        gender_sample = next(s for s in samples if s["column_name"] == "gender_label")
        assert "Male" in gender_sample["sample_values"]
        assert "Female" in gender_sample["sample_values"]

    def test_generate_dataset_profile(self, mock_df):
        profile = generate_dataset_profile("plfs", "plfs_person", mock_df)
        assert len(profile) == 1
        prof_rec = profile[0]
        assert prof_rec["row_count"] == 3
        assert prof_rec["column_count"] == 5
        assert prof_rec["missing_values"] == 0
        
        summary = prof_rec["profile_data"]["summary"]
        assert summary["completeness_overall_pct"] == 100.0


class TestPostgresMetadataRegistry:

    @pytest.fixture(autouse=True)
    def skip_no_postgres(self):
        try:
            StatIQDB()
        except Exception:
            pytest.skip("PostgreSQL not running — start with: docker-compose up -d postgres")

    def test_load_metadata_roundtrip(self):
        db = StatIQDB()
        
        mock_rels = [{"parent_table": "p_table", "child_table": "c_table", "join_keys": ["k1"], "relationship_type": "1:N", "description": "desc"}]
        mock_dict = [{"variable_name": "v1", "code": "1", "code_description": "d1"}]
        mock_cols = [{"table_name": "t1", "column_name": "c1", "data_type": "int", "description": "desc1", "is_sensitive": False}]
        mock_samples = [{"table_name": "t1", "column_name": "c1", "sample_values": ["val1", "val2"]}]
        mock_profiles = [{"table_name": "t1", "row_count": 100, "column_count": 5, "missing_values": 2, "profile_data": {"summary": {}}}]
        mock_queries = [{"title": "q1", "description": "descq", "sql_query": "SELECT 1"}]

        db.load_survey_metadata(
            survey_id="__test_survey__",
            relationships=mock_rels,
            dictionary=mock_dict,
            columns=mock_cols,
            samples=mock_samples,
            profiles=mock_profiles,
            suggested_queries=mock_queries
        )

        # Query database to assert insertion
        from sqlalchemy import text
        with db.engine.connect() as conn:
            n_cols = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_columns WHERE survey_id = '__test_survey__'")).scalar()
            n_rels = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_relationships WHERE survey_id = '__test_survey__'")).scalar()
            n_dict = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_dictionary WHERE survey_id = '__test_survey__'")).scalar()
            n_samples = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_samples WHERE survey_id = '__test_survey__'")).scalar()
            n_profiles = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_profiles WHERE survey_id = '__test_survey__'")).scalar()
            n_queries = conn.execute(text("SELECT COUNT(*) FROM survey_metadata_suggested_queries WHERE survey_id = '__test_survey__'")).scalar()

            # Clean up
            conn.execute(text("DELETE FROM survey_metadata_relationships WHERE survey_id = '__test_survey__'"))
            conn.execute(text("DELETE FROM survey_metadata_dictionary WHERE survey_id = '__test_survey__'"))
            conn.execute(text("DELETE FROM survey_metadata_columns WHERE survey_id = '__test_survey__'"))
            conn.execute(text("DELETE FROM survey_metadata_samples WHERE survey_id = '__test_survey__'"))
            conn.execute(text("DELETE FROM survey_metadata_profiles WHERE survey_id = '__test_survey__'"))
            conn.execute(text("DELETE FROM survey_metadata_suggested_queries WHERE survey_id = '__test_survey__'"))
            conn.commit()

        assert n_cols == 1
        assert n_rels == 1
        assert n_dict == 1
        assert n_samples == 1
        assert n_profiles == 1
        assert n_queries == 1
