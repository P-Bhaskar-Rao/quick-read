import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self._connection_pool = None
        self._init_connection_pool()

    def _init_connection_pool(self):
        try:
            if os.getenv("CLOUD_RUN_ENV"):
                from google.cloud.sql.connector import Connector
                self.connector = Connector()
            else:
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,
                    host=self.config.db_config['host'],
                    user=self.config.db_config['user'],
                    password=self.config.db_config['password'],
                    database=self.config.db_config['database']
                )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            if os.getenv("CLOUD_RUN_ENV"):
                conn = self.connector.connect(
                    self.config.db_config['instance_connection_name'],
                    "pg8000",
                    user=self.config.db_config['user'],
                    password=self.config.db_config['password'],
                    db=self.config.db_config['database']
                )
            else:
                conn = self._connection_pool.getconn()
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                if not os.getenv("CLOUD_RUN_ENV"):
                    self._connection_pool.putconn(conn)
                else:
                    conn.close()

    def execute_query(self, query: str, params: tuple = None, fetch_results: bool = False):
        """Execute database query with proper connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_results:
                    results = cursor.fetchall()
                    conn.commit()  # ✅ Ensure write ops with RETURNING are committed
                    return results
                else:
                    conn.commit()
                    return cursor.rowcount
            except Exception as e:
                conn.rollback()
                logger.error(f"Database query error: {e}")
                raise
            finally:
                cursor.close()



    def close_all_connections(self):
        if self._connection_pool:
            self._connection_pool.closeall()
        if hasattr(self, 'connector'):
            self.connector.close()