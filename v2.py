import streamlit as st
from snowflake.cortex import complete
from snowflake.core import Root
from snowflake.snowpark import Session
from utils import upload_to_snowflake
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


# Replace the session connection setup
connection_parameters = {
    "account": SNOWFLAKE_ACCOUNT,
    "user": SNOWFLAKE_USER,
    "password": SNOWFLAKE_PASSWORD,
    "database": SNOWFLAKE_DATABASE,
    "schema": SNOWFLAKE_SCHEMA,
    "warehouse": SNOWFLAKE_WAREHOUSE
}
session = Session.builder.configs(connection_parameters).create()
root = Root(session)
my_service = (root
  .databases[SNOWFLAKE_DATABASE]
  .schemas[SNOWFLAKE_SCHEMA]
  .cortex_search_services["CC_SEARCH_SERVICE_CS"]
)
# Add these constants after your existing configuration
MODELS = [
    "mistral-large2",
    "llama3.1-70b",
    "llama3.1-8b",
]

def upload_ui():
    """UI for uploading resumes."""
    st.title("ATS for Recruiters")
    st.write("Upload resumes and start searching for the perfect candidate!")

    uploaded_files = st.file_uploader(
        "Drag and drop your resumes here", type="pdf", accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Upload Resumes"):
            for file in uploaded_files:
                with st.spinner(f"Uploading {file.name} to Snowflake..."):
                    file_data = file.read()
                    with st.status(f"Processing {file.name}...", expanded=True) as status:
                        st.write("Uploading file to stage...")
                        upload_to_snowflake(file.name, file_data)
                        st.write("Refreshing stage metadata...")
                        st.write("Inserting document metadata...")
                        status.update(label=f"Completed processing {file.name}", state="complete")
                
            st.success("All files uploaded successfully!")
            st.session_state["chat_mode"] = True  # Switch to chat mode
            st.rerun()  # Trigger re-render to show chat UI

    # Display uploaded files in a side panel
    with st.sidebar:
        st.subheader("Uploaded Files")
        if st.session_state["uploaded_files"]:
            for file in st.session_state["uploaded_files"]:
                st.write(f"- {file}")
        else:
            st.write("No files uploaded yet.")

def chat_ui():
    """UI for chat interaction."""
    st.title("Recruiter Chat Assistant")
    st.write("Chat with the ATS to search for candidates or get insights.")

    # Display uploaded files in sidebar
    with st.sidebar:
        st.subheader("Uploaded Files")
        if st.session_state["uploaded_files"]:
            for file in st.session_state["uploaded_files"]:
                st.write(f"- {file}")
        else:
            st.write("No files uploaded yet.")
        
        # Add Snowflake model selection
        st.selectbox("Select model:", MODELS, key="model_name")

    # Define icons once
    icons = {"assistant": "❄️", "user": "👤"}

    # Display chat history
    for idx, message in enumerate(st.session_state["messages"]):
        with st.chat_message(message["role"], avatar=icons[message["role"]]):
            st.markdown(message["content"])
            # Only show source documents expander if it exists and is not empty
            if "source_documents" in message and message["source_documents"]:
                with st.expander("View Source Documents", expanded=False):
                    st.markdown("### Raw Search Response")
                    st.json(message["source_documents"])

    if prompt := st.chat_input("Ask something about the resumes..."):
        # User's message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=icons["user"]):
            st.markdown(prompt)

        # Assistant response
        with st.chat_message("assistant", avatar=icons["assistant"]):
            try:
                # Search phase
                search_response = my_service.search(
                    query=prompt,
                    columns=["chunk"],
                    limit=5
                )
                results = search_response.results
                
                search_col = 'chunk'
                context_str = ""
                for i, r in enumerate(results):
                    context_str += f"Context document {i+1}: {r[search_col]} \n" + "\n"

                # if st.session_state.debug:
                #     st.sidebar.text_area("Context documents", context_str, height=500)
                
                # Create complete prompt
                full_prompt = f"""[INST]
You are a helpful AI assistant for recruiters. Your task is to provide clear, concise, and relevant information about candidates based on their resumes. Use the following context to answer the question, and if you're not sure about something, please say so.

Context from resumes:
{context_str}

User Question: {prompt}

[/INST]"""
                
                # Create a placeholder for the streaming response
                response_placeholder = st.empty()
                response = ""
                
                with st.spinner("Generating response..."):
                    for chunk in complete(
                        st.session_state.model_name, 
                        full_prompt, 
                        session=session,
                        stream=True
                    ):
                        response += chunk
                        # Update the placeholder with accumulated response
                        response_placeholder.markdown(response)
                
                # Store both response and source documents in message history
                st.session_state["messages"].append({
                    "role": "assistant", 
                    "content": response,
                    "source_documents": search_response.to_json()  # Save search results with the message
                })
                    
            except Exception as e:
                error_msg = f"Error occurred: {str(e)}"
                st.error(error_msg)
                print("Error:", error_msg)
                return

def main():
    if st.session_state["chat_mode"]:
        chat_ui()  # Show chat UI if resumes have been uploaded
    else:
        upload_ui()  # Show upload UI if resumes haven't been uploaded

if __name__ == "__main__":
    main()