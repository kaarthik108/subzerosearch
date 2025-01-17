import re
import os
import datetime
import random
import string
import snowflake.connector
import streamlit as st
from markitdown import MarkItDown
from snowflake_utils import SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_STAGE

# if 'folder_path' not in st.session_state:
#     st.session_state['folder_path'] = "resume/2025-01-14/nN1N2gY0" 

@st.cache_resource
def get_snowflake_connection():
    conn = st.connection("snowflake")
    return conn.session()

def sanitize_filename(file_name):
    """Sanitize the filename for compatibility with Snowflake."""
    return re.sub(r"[^a-zA-Z0-9_.]", "_", file_name)

def upload_to_snowflake(file_name, file_data):
    """Upload a file to a Snowflake stage and insert metadata into the database."""
    try:
        session = get_snowflake_connection()
        sanitized_file_name = sanitize_filename(file_name)
        temp_file_path = f"temp_{sanitized_file_name}"
        with open(temp_file_path, "wb") as f:
            f.write(file_data)

        # Generate folder path with current date and random string
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Check if random string is already generated for the session
        if "random_string" not in st.session_state:
            st.session_state["random_string"] = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        random_string = st.session_state["random_string"]
        folder_path = f"resume/{current_date}/{random_string}"

        st.session_state['folder_path'] = folder_path
        st.query_params.folder_path = folder_path
        
        # Specify the target folder in the stage
        stage_path = f"@{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STAGE}/{folder_path}"
        put_query = f"PUT file://{os.path.abspath(temp_file_path)} {stage_path} AUTO_COMPRESS=FALSE"
        session.sql(put_query).collect()
        st.session_state["uploaded_files"].append(f"{folder_path}/{sanitized_file_name}")

        # Refresh stage before inserting metadata
        refresh_query = f"ALTER STAGE {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STAGE} REFRESH;"
        session.sql(refresh_query).collect()

        # Use MarkItDown to parse the document
        md = MarkItDown()
        parsed_content = md.convert(temp_file_path)

        # Insert metadata into the database
        insert_query = f"""
        INSERT INTO docs_chunks_table (relative_path, size, file_url, scoped_file_url, chunk)
        SELECT relative_path, 
               size,
               file_url, 
               build_scoped_file_url(@docs, relative_path) AS scoped_file_url,
               func.chunk AS chunk
        FROM 
            directory(@docs),
        TABLE(text_chunker (TO_VARCHAR('{parsed_content.text_content}'))
        ) as func
        WHERE relative_path LIKE 'resume/%/{random_string}/%.pdf';
        """
        session.sql(insert_query).collect()

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        # No need to explicitly close session as Streamlit manages it


prompt = """
    Analyze all the resumes and provide structured insights in JSON format. The response must be ONLY valid JSON with no additional text or formatting. The JSON should include:
    {
        "total_candidates": <int>,
        "skills": {"<skill>": <count>, ...},
        "average_experience": <float>,
        "total_projects": <int>,
        "candidates": [
            {
                "name": "<candidate_name>",
                "experience": <int>,
                "projects": <int>,
                "key_achievements": "<key achievements>",
                "ai_take": "<your assessment of suitable roles for this candidate>"
            },
            ...
        ]
    }

    Example:
    {
        "total_candidates": 2,
        "skills": {"Python": 2, "SQL": 2, "Spark": 1},
        "average_experience": 6.5,
        "total_projects": 7,
        "candidates": [
            {
                "name": "Alan Susa",
                "experience": 7,
                "projects": 3,
                "key_achievements": "Migrated Oracle to Redshift, saving $678k annually.",
                "ai_take": "Best suited for Data Engineer or Big Data Developer roles."
            },
            {
                "name": "Kaarthik Andavar",
                "experience": 6,
                "projects": 4,
                "key_achievements": "Reduced ML costs by 99.4% via SageMaker migration.",
                "ai_take": "Great fit for Full-Stack Developer or Data Warehouse Engineer roles."
            }
        ]
    }
    """