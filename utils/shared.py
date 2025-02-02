import re
import os
import datetime
import random
import string
import streamlit as st
from markitdown import MarkItDown
from utils.snowflake_utils import SnowflakeConfig, SnowflakeConnection
from utils.logging_utils import setup_logging

logger = setup_logging()


def sanitize_filename(file_name):
    """Sanitize the filename for compatibility with Snowflake."""
    return re.sub(r"[^a-zA-Z0-9_.]", "_", file_name)


def append_folder_path(folder_path):
    files = get_file_paths(folder_path)
    st.session_state["uploaded_files"].extend(files)


def upload_to_snowflake(file_name, file_data):
    """Upload a file to a Snowflake stage and insert metadata into the database."""
    try:
        session = SnowflakeConnection.get_connection()
        sanitized_file_name = sanitize_filename(file_name)
        temp_file_path = f"temp_{sanitized_file_name}"
        with open(temp_file_path, "wb") as f:
            f.write(file_data)

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if "random_string" not in st.session_state:
            st.session_state["random_string"] = ''.join(
                random.choices(string.ascii_letters + string.digits, k=8))

        random_string = st.session_state["random_string"]
        folder_path = f"resume/{current_date}/{random_string}"

        st.session_state['folder_path'] = folder_path
        st.query_params.folder_path = folder_path

        stage_path = f"@{SnowflakeConfig.DATABASE}.{SnowflakeConfig.SCHEMA}.{SnowflakeConfig.STAGE}/{folder_path}"
        put_query = f"PUT file://{os.path.abspath(temp_file_path)} {stage_path} AUTO_COMPRESS=FALSE"
        session.sql(put_query).collect()
        st.session_state["uploaded_files"].append(
            f"{folder_path}/{sanitized_file_name}")

        refresh_query = f"ALTER STAGE {SnowflakeConfig.DATABASE}.{SnowflakeConfig.SCHEMA}.{SnowflakeConfig.STAGE} REFRESH;"
        session.sql(refresh_query).collect()

        md = MarkItDown()
        parsed_content = md.convert(temp_file_path)

        insert_query = f"""
        INSERT INTO {SnowflakeConfig.CHUNK_TABLE} (relative_path, size, file_url, scoped_file_url, chunk)
        SELECT relative_path, 
               size,
               file_url, 
               build_scoped_file_url(@{SnowflakeConfig.STAGE}, relative_path) AS scoped_file_url,
               func.chunk AS chunk
        FROM 
            directory(@{SnowflakeConfig.STAGE}),
        TABLE(text_chunker (TO_VARCHAR('{parsed_content.text_content}'))
        ) as func
        WHERE relative_path LIKE 'resume/%/{random_string}/%.pdf';
        """
        session.sql(insert_query).collect()

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@st.cache_data(ttl=4000)
def get_file_paths(folder_path):
    """Retrieve file paths from the database."""
    logger.info("Retrieving file paths from the database.")
    session = SnowflakeConnection.get_connection()
    list_query = f"""
    SELECT DISTINCT relative_path 
    FROM {SnowflakeConfig.CHUNK_TABLE} 
    WHERE relative_path LIKE '{folder_path}/%';
    """
    result = session.sql(list_query).collect()
    file_paths = [row['RELATIVE_PATH'] for row in result]
    return file_paths


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


def render_sidebar():
    """Render sidebar content"""
    with st.sidebar:
        st.markdown("""
            <style>
                [data-testid="stSidebarNav"] {
                    display: none;
                }
            </style>
        """, unsafe_allow_html=True)

        st.page_link("main.py", label="/Chat")
        st.page_link("pages/auto_insights.py", label="/Auto Insights")
        st.markdown(
            '<h3 class="sidebar-title">Uploaded Files</h3>',
            unsafe_allow_html=True
        )
        if st.session_state.get("uploaded_files"):
            for file in st.session_state["uploaded_files"]:
                file_name = file.split('/')[-1]
                st.write(f"- {file_name}")
        else:
            st.write("No files uploaded yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Reset", key="reset_button"):
            st.query_params.clear()
            st.session_state["chat_mode"] = False
            st.session_state["uploaded_files"] = []
            st.session_state["folder_path"] = None
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
