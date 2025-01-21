import streamlit as st
from typing import Any
from snowflake.core import Root
from utils.logging_utils import setup_logging

logger = setup_logging()


class SnowflakeConfig:
    """Configuration class for Snowflake settings"""
    DATABASE: str = st.secrets["DATABASE"]
    SCHEMA: str = st.secrets["SCHEMA"]
    STAGE: str = "docs"
    SEARCH_SERVICE: str = "sub_zero_search"
    CHUNK_TABLE: str = "chunks_table"


class SnowflakeConnection:
    """Manages Snowflake database connections and search services."""

    def __init__(self) -> None:
        """Initialize SnowflakeConnection with configuration."""
        self.config = SnowflakeConfig

    @staticmethod
    @st.cache_resource
    def get_connection():
        """Get cached Snowflake connection.

        Returns:
            session: Snowflake session object

        Raises:
            ConnectionError: If connection fails
        """
        try:
            conn = st.connection("snowflake")
            return conn.session()
        except Exception as e:
            logger.error("Failed to connect to Snowflake: %s", str(e))
            raise ConnectionError(
                f"Could not connect to Snowflake: {str(e)}") from e

    @staticmethod
    def get_search_service(session: Any) -> Any:
        """Get Snowflake search service using provided session.

        Args:
            session: Active Snowflake session

        Returns:
            search_service: Snowflake search service object

        Raises:
            Exception: If search service creation fails
        """
        try:
            root = Root(session)
            search_service = (
                root.databases[SnowflakeConfig.DATABASE]
                .schemas[SnowflakeConfig.SCHEMA]
                .cortex_search_services[SnowflakeConfig.SEARCH_SERVICE]
            )
            return search_service
        except Exception as e:
            logger.error("Failed to get search service: %s", str(e))
            raise


if __name__ == "__main__":
    try:
        session = SnowflakeConnection.get_connection()

        search_service = SnowflakeConnection.get_search_service(session)

    except Exception as e:
        logger.error("Failed to initialize Snowflake services: %s", str(e))
