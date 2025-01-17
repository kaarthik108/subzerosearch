import streamlit as st
from snowflake.core import Root
from snowflake.cortex import complete
from snowflake_utils import SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
from utils import upload_to_snowflake

st.set_page_config(
    page_title="ATS for Recruiters",
    layout="centered",  # This ensures main page stays narrow
    initial_sidebar_state="expanded"
)


def set_bg_from_url(bg_url):
    st.markdown(
        f"""
        <style>
        # html, body, [data-testid="stAppViewContainer"] {{
        #     background-image: url({bg_url});
        #     background-position: center;
        #     background-repeat: no-repeat;
        #     background-size: cover;
        #     background-attachment: fixed;
        #     min-height: 100vh;
        #     margin: 0;
        #     padding: 0;
        # }}

        # [data-testid="stHeader"] {{
        #     background-color: rgba(0,0,0,0);
        # }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Initialize session state variables
if "chat_mode" not in st.session_state:
    st.session_state["chat_mode"] = False
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "folder_path" not in st.session_state:
    st.session_state["folder_path"] = None


@st.cache_resource
def get_snowflake_connection():
    try:
        conn = st.connection("snowflake")
        return conn.session()
    except Exception as e:
        st.error(f"Error connecting to Snowflake: {str(e)}")
        return None


root = Root(get_snowflake_connection())
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

# Load the CSS file
load_css("styles.css")


def upload_ui():
    st.markdown('<div class="upload-container">', unsafe_allow_html=True)

    st.markdown('<div class="title">ATS for Recruiters</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload resumes and start searching for the perfect candidate!</div>',
                unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drag and drop your resumes here",
        type="pdf",
        accept_multiple_files=True,
        key="resume_uploader"
    )

    if uploaded_files:
        button_container = st.empty()

        if not st.session_state.get('uploading', False):
            if button_container.button("Upload Resumes"):
                st.session_state.uploading = True
                button_container.empty()

                spinner = st.empty()
                spinner.markdown(
                    '<div class="loading-spinner"></div>', unsafe_allow_html=True)

                try:
                    for file in uploaded_files:
                        file_data = file.read()
                        upload_to_snowflake(file.name, file_data)
                        st.markdown(
                            f'<div class="success-message">✨ Successfully uploaded {file.name}</div>',
                            unsafe_allow_html=True
                        )
                except Exception as e:
                    st.markdown(
                        f'<div class="error-message">❌ Error uploading files: {str(e)}</div>',
                        unsafe_allow_html=True
                    )
                finally:
                    spinner.empty()
                    st.session_state.uploading = False

                import time
                time.sleep(1)
                st.session_state["chat_mode"] = True
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def chat_ui():
    # Modern minimalist header with gradient text
    st.markdown("""
        <div class="header-section">
            <div class="chat-header-content">
                <h1 class="chat-title">
                    Transform your <span class="gradient-text">hiring</span> process
                </h1>
                <p class="chat-subtitle">
                    AI-powered talent matching that understands the nuances of every resume
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar content
    with st.sidebar:
        st.markdown('<h3 class="sidebar-title">Uploaded Files</h3>',
                    unsafe_allow_html=True)
        if st.session_state["uploaded_files"]:
            for file in st.session_state["uploaded_files"]:
                st.write(f"- {file}")
        else:
            st.write("No files uploaded yet.")

        st.selectbox("Select model:", MODELS, key="model_name")

    # Display chat history
    for message in st.session_state.get("messages", []):
        role_class = "user" if message["role"] == "user" else "assistant"
        avatar_content = '<div class="user-img"></div>' if message["role"] == "user" else "❄️"
        avatar_class = "user-avatar" if message["role"] == "user" else "assistant-avatar"

        st.markdown(f"""
            <div class="message-wrapper {role_class}">
                <div class="avatar {avatar_class}">{avatar_content}</div>
                <div class="message-content">{message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)

        if message["role"] == "assistant":
            with st.expander("📄 View Source Documents"):
                if "source_documents" in message and message["source_documents"]:
                    st.json(message["source_documents"])
                else:
                    st.info("No source documents available")

    # Chat input
    if prompt := st.chat_input("Ask something about the resumes..."):
        st.markdown(f"""
            <div class="message-wrapper user">
                <div class="avatar user-avatar">
                    <img src="https://mk7iyaq7oqz5ihbw.public.blob.vercel-storage.com/pngegg-FyQPBN1QqOBSGwaFpRQmhQKs0MhCD1.png" alt="User">
                </div>
                <div class="message-content">{prompt}</div>
            </div>
        """, unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Get search results
            search_response = my_service.search(
                query=prompt,
                columns=["chunk"],
                limit=5
            )
            results = search_response.results
            source_documents = search_response.to_json()

            context_str = "\n".join([f"Context document {i+1}: {r['chunk']}"
                                     for i, r in enumerate(results)])

            full_prompt = f"""
You are a helpful AI assistant for recruiters. Your task is to provide clear, concise, and relevant information about candidates based on their resumes. Use the following context to answer the question, and if you're not sure about something, please say so.

Context from resumes:
{context_str}

User Question: {prompt}
"""

            # Create placeholders for assistant response and sources
            response_placeholder = st.empty()
            sources_placeholder = st.empty()
            response = ""

            for chunk in complete(
                st.session_state.model_name,
                full_prompt,
                session=get_snowflake_connection(),
                stream=True
            ):
                response += chunk
                response_placeholder.markdown(f"""
                    <div class="message-wrapper assistant">
                        <div class="avatar assistant-avatar">❄️</div>
                        <div class="message-content">{response}</div>
                    </div>
                """, unsafe_allow_html=True)

            # Display source documents
            with sources_placeholder.expander("📄 View Source Documents"):
                st.json(source_documents)

            # Add to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "source_documents": source_documents
            })

        except Exception as e:
            st.error(f"Error occurred: {str(e)}")


def main():
    if st.session_state["chat_mode"]:
    # if True:
        chat_ui()  # Show chat UI if resumes have been uploaded
    else:
        st.session_state['folder_path'] = None
        upload_ui()  # Show upload UI if resumes haven't been uploaded


if __name__ == "__main__":
    main()
