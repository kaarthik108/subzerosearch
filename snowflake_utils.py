import streamlit as st
from snowflake.snowpark import Session

# Snowflake connection details
SNOWFLAKE_ACCOUNT = st.secrets["ACCOUNT"]
SNOWFLAKE_USER = st.secrets["USER_NAME"]
SNOWFLAKE_PASSWORD = st.secrets["PASSWORD"]
SNOWFLAKE_DATABASE = st.secrets["DATABASE"]
SNOWFLAKE_SCHEMA = st.secrets["SCHEMA"]
SNOWFLAKE_WAREHOUSE = st.secrets["WAREHOUSE"]
SNOWFLAKE_STAGE = "docs"  # Replace with your Snowflake stage name

@st.cache_resource
def get_snowflake_session():
    """Establish and cache a Snowflake session."""
    try:
        connection_parameters = {
            "account": SNOWFLAKE_ACCOUNT,
            "user": SNOWFLAKE_USER,
            "password": SNOWFLAKE_PASSWORD,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA,
            "warehouse": SNOWFLAKE_WAREHOUSE
        }
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"Failed to create Snowflake session: {str(e)}")
        raise 