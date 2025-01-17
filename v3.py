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
# Complete styling with fixes
st.markdown("""
<style>
    /* Reset Streamlit container padding */
    .main .block-container {
        padding-top: 0;
        padding-bottom: 0;
        max-width: 100%;
    }

    /* Hide Streamlit's default spinner */
    .stSpinner {
        display: none !important;
    }

    /* Center container styles */
    .upload-container {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100%;
        max-width: 600px;
        text-align: center;
        padding: 2rem;
    }
    
    /* Title styles with gradient */
    .title {
        background: linear-gradient(45deg, #2196F3, #00BCD4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    /* Subtitle styles */
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* File uploader styles */
    .uploadedFile {
        display: none;
    }
    
    .stFileUploader {
        padding: 3rem !important;
        border: 2px dashed #ccc !important;
        border-radius: 15px !important;
        background: linear-gradient(145deg, #ffffff, #f6f6f6) !important;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stFileUploader:hover {
        border-color: #2196F3 !important;
        background: linear-gradient(145deg, #f0f8ff, #e3f2fd) !important;
        transform: translateY(-2px);
    }
    
    /* Gradient button */
    .stButton > button {
        background: linear-gradient(45deg, #2196F3, #00BCD4) !important;
        color: white !important;
        padding: 0.75rem 1.5rem !important;
        border: none !important;
        border-radius: 8px !important;
        margin-top: 1rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3);
        width: 100%;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #1976D2, #0097A7) !important;
        box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4);
        transform: translateY(-1px);
    }

    /* Loading spinner animation */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-spinner {
        width: 40px;
        height: 40px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #2196F3;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }

    /* Status messages */
    .success-message {
        padding: 1rem;
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        border-radius: 8px;
        margin-top: 1rem;
        animation: slideIn 0.5s ease-out;
    }
    
    .error-message {
        padding: 1rem;
        background: linear-gradient(45deg, #f44336, #e53935);
        color: white;
        border-radius: 8px;
        margin-top: 1rem;
        animation: slideIn 0.5s ease-out;
    }

    @keyframes slideIn {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    /* Hide default elements */
    .css-1dp5vir {
        display: none;
    }

    .user-img {
        width: 100%;
        height: 100%;
        background-image: url('https://mk7iyaq7oqz5ihbw.public.blob.vercel-storage.com/pngegg-FyQPBN1QqOBSGwaFpRQmhQKs0MhCD1.png');
        background-size: cover;
        background-position: center;
    }
</style>
""", unsafe_allow_html=True)

def upload_ui():
    st.markdown('<div class="upload-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="title">ATS for Recruiters</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload resumes and start searching for the perfect candidate!</div>', unsafe_allow_html=True)
    
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
                spinner.markdown('<div class="loading-spinner"></div>', unsafe_allow_html=True)
                
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
        st.markdown('<h3 class="sidebar-title">Uploaded Files</h3>', unsafe_allow_html=True)
        if st.session_state["uploaded_files"]:
            for file in st.session_state["uploaded_files"]:
                st.write(f"- {file}")
        else:
            st.write("No files uploaded yet.")
        
        st.selectbox("Select model:", MODELS, key="model_name")

    st.markdown("""
    <style>
        /* Minimalist Modern Header Styling */
        .header-section {
            padding: 2rem 2rem;
            text-align: center;
        }

        .chat-header-content {
            max-width: 780px;
            margin: 0 auto;
        }

        .chat-title {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 56px;
            font-weight: 500;
            line-height: 1.1;
            color: #1a1a1a;
            margin-bottom: 24px;
            letter-spacing: -0.02em;
        }

        .gradient-text {
            background: linear-gradient(to right, #f59e0b, #ec4899);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 400;
            letter-spacing: normal;
        }

        .chat-subtitle {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 18px;
            line-height: 1.6;
            color: #666666;
            margin: 0 auto;
            max-width: 540px;
            font-weight: 400;
            letter-spacing: -0.01em;
        }

        @media (max-width: 640px) {
            .header-section {
                padding: 1.5rem 1.5rem;
            }
            
            .chat-title {
                font-size: 40px;
            }
            
            .chat-subtitle {
                font-size: 16px;
            }
        }

        /* Sidebar Styling */
        .sidebar-title {
            color: #1565C0;
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #E3F2FD;
        }

        /* Message Styles */
        .message-wrapper {
            display: flex;
            margin: 1.2rem 0;
            align-items: flex-start;
            gap: 12px;
        }

        .message-wrapper.user {
            flex-direction: row-reverse;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            flex-shrink: 0;
            overflow: hidden;
            border: 2px solid #E3F2FD;
        }

        .avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .assistant-avatar {
            color: #1565C0;
        }

        .message-content {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 15px;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .assistant .message-content {
            background: rgba(255, 255, 255, 0.8);
            color: #000000;
            border-top-left-radius: 5px;
        }

        .user .message-content {
            background: #1a1a1a;
            color: white;
            border-top-right-radius: 5px;
        }

        /* Source Document Styling */
        div[data-testid="stExpander"] {
            border: none;
            box-shadow: none;
            background-color: transparent;
            margin-left: 48px;
            margin-bottom: 24px;
            max-width: 80%;
        }

        div[data-testid="stExpander"] > div:first-child {
            border: 1px solid #E3F2FD;
            border-radius: 8px;
            background-color: #F8F9FA;
            padding: 8px 16px;
            color: #1565C0;
            transition: all 0.2s ease;
        }

        div[data-testid="stExpander"] > div:first-child:hover {
            background-color: #E3F2FD;
        }

        div[data-testid="stExpander"] > div:last-child {
            border: 1px solid #E3F2FD;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 16px;
            background-color: white;
        }

        div[data-testid="stExpander"] pre {
            background-color: #F8F9FA;
            border-radius: 4px;
            padding: 12px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 13px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
        }

        button[kind="secondary"] {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }

        /* Chat input styling */
        .stTextInput > div > div {
            padding: 8px 16px;
            border-radius: 24px;
            border: 1px solid #E3F2FD;
            background-color: white;
            transition: all 0.2s ease;
        }

        .stTextInput > div > div:focus-within {
            border-color: #1565C0;
            box-shadow: 0 0 0 2px rgba(21, 101, 192, 0.1);
        }

        /* Update the user avatar styling */
        .user-avatar img {
            background-image: url('https://mk7iyaq7oqz5ihbw.public.blob.vercel-storage.com/pngegg-FyQPBN1QqOBSGwaFpRQmhQKs0MhCD1.png');
            background-size: cover;
            background-position: center;
            width: 100%;
            height: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

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
            
            full_prompt = f"""[INST]
You are a helpful AI assistant for recruiters. Your task is to provide clear, concise, and relevant information about candidates based on their resumes. Use the following context to answer the question, and if you're not sure about something, please say so.

Context from resumes:
{context_str}

User Question: {prompt}
[/INST]"""
            
            # Create placeholders for assistant response and sources
            response_placeholder = st.empty()
            sources_placeholder = st.empty()
            response = ""
            
            for chunk in complete(
                st.session_state.model_name, 
                full_prompt, 
                session=session,
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
    # if st.session_state["chat_mode"]:
    if True:
        chat_ui()  # Show chat UI if resumes have been uploaded
    else:
        upload_ui()  # Show upload UI if resumes haven't been uploaded

if __name__ == "__main__":
    main()