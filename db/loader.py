"""
db/loader.py
=============
Data Loader Module for mospi-platform.
Exposes repository functions for bulk loading and index creation.
"""

from db.postgres_client import StatIQDB

def load_dataframe_to_db(df, table_name, if_exists="append", chunksize=10000):
    """Bulk loads a pandas DataFrame into the database using psycopg2 COPY or SQLAlchemy."""
    db = StatIQDB()
    return db.bulk_load(df, table_name, if_exists=if_exists, chunksize=chunksize)

def load_dataframe_with_indexes(df, table_name, index_sqls, if_exists="replace"):
    """Loads a DataFrame and then creates indexes for maximum load performance."""
    db = StatIQDB()
    return db.bulk_load_with_indexes(df, table_name, index_sqls, if_exists=if_exists)
