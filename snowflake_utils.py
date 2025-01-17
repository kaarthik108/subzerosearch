import streamlit as st
import logging

SNOWFLAKE_DATABASE = st.secrets["DATABASE"]
SNOWFLAKE_SCHEMA = st.secrets["SCHEMA"]
SNOWFLAKE_STAGE = "docs"

logger = logging.getLogger(__name__)

class SnowflakeConnection:
    """Manages Snowflake database connection"""
    
    @staticmethod
    @st.cache_resource
    def get_connection():
        """Establish and return Snowflake connection"""
        try:
            conn = st.connection("snowflake")
            return conn.session()
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise ConnectionError(f"Could not connect to Snowflake: {str(e)}")