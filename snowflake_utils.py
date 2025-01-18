import streamlit as st
import logging
from typing import Any
from snowflake.core import Root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SnowflakeConfig:
    """Configuration class for Snowflake settings"""
    DATABASE: str = st.secrets["DATABASE"]
    SCHEMA: str = st.secrets["SCHEMA"]
    STAGE: str = "docs"
    SEARCH_SERVICE: str = "CC_SEARCH_SERVICE_CS"


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


# Usage example:
if __name__ == "__main__":
    try:
        # Get session
        session = SnowflakeConnection.get_connection()

        # Get search service using session
        search_service = SnowflakeConnection.get_search_service(session)

        # Use session and search_service here

    except Exception as e:
        logger.error("Failed to initialize Snowflake services: %s", str(e))
