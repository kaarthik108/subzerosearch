import streamlit as st
import os
import re
import snowflake.connector
from openai import OpenAI

# Initialize session state variables
if "chat_mode" not in st.session_state:
    st.session_state["chat_mode"] = False
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Snowflake connection details
SNOWFLAKE_ACCOUNT = st.secrets["ACCOUNT"]
SNOWFLAKE_USER = st.secrets["USER_NAME"]
SNOWFLAKE_PASSWORD = st.secrets["PASSWORD"]
SNOWFLAKE_DATABASE = st.secrets["DATABASE"]
SNOWFLAKE_SCHEMA = st.secrets["SCHEMA"]
SNOWFLAKE_WAREHOUSE = st.secrets["WAREHOUSE"]
SNOWFLAKE_STAGE = "docs"  # Replace with your Snowflake stage name

# OpenAI API key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def sanitize_filename(file_name):
    """Sanitize the filename for compatibility with Snowflake."""
    return re.sub(r"[^a-zA-Z0-9_.]", "_", file_name)

def upload_to_snowflake(file_name, file_data):
    """Upload a file to a Snowflake stage."""
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        warehouse=SNOWFLAKE_WAREHOUSE
    )
    cursor = conn.cursor()
    try:
        sanitized_file_name = sanitize_filename(file_name)
        temp_file_path = f"temp_{sanitized_file_name}"
        with open(temp_file_path, "wb") as f:
            f.write(file_data)

        # Specify the target folder in the stage
        stage_path = f"@{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STAGE}/{sanitized_file_name}"
        put_query = f"PUT file://{os.path.abspath(temp_file_path)} {stage_path} AUTO_COMPRESS=FALSE"
        cursor.execute(put_query)
        st.session_state["uploaded_files"].append(sanitized_file_name)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        cursor.close()
        conn.close()

def upload_ui():
    """UI for uploading resumes."""
    st.title("ATS for Recruiters")
    st.write("Upload resumes and start searching for the perfect candidate!")

    uploaded_files = st.file_uploader(
        "Drag and drop your resumes here", type="pdf", accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Upload Resumes"):
            with st.spinner("Uploading resumes to Snowflake..."):
                for file in uploaded_files:
                    file_data = file.read()
                    upload_to_snowflake(file.name, file_data)
                st.session_state["chat_mode"] = True  # Switch to chat mode
                st.rerun()  # Trigger re-render to show chat UI

def chat_ui():
    """UI for chat interaction."""
    st.title("Recruiter Chat Assistant")
    st.write("Chat with the ATS to search for candidates or get insights.")

    # Display chat history
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input for chat message
    if prompt := st.chat_input("Ask something about the resumes..."):
        # User's message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # OpenAI Assistant's response
        with st.chat_message("assistant"):
            st.spinner("Thinking...")
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True
            )
            # Extract the text content from the response
            response = st.write_stream(stream)

        # Append assistant's response to the chat history
        st.session_state["messages"].append({"role": "assistant", "content": response})

def main():
    if st.session_state["chat_mode"]:
        chat_ui()  # Show chat UI if resumes have been uploaded
    else:
        upload_ui()  # Show upload UI if resumes haven't been uploaded

if __name__ == "__main__":
    main()

