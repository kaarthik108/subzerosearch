import streamlit as st


class SessionStateManager:
    """Manages Streamlit session state"""

    @staticmethod
    def initialize_session_state():
        """Initialize session state variables"""
        default_states = {
            "chat_mode": False,
            "uploaded_files": [],
            "default_folder_path": "resume/2025-01-24/ISwfEXWb",
            "folder_path": None,
            "uploading": False
        }

        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {
                    "role": "user",
                    "content": "Hi there! 👋",
                },
                {
                    "role": "assistant",
                    "content": "✨ Great! Your resumes are ready to explore. Ask me anything about them, or check out the Auto Insights page for AI-powered analysis of all your resumes! ✨",
                    "source_documents": {}
                }
            ]

        if 'folder_path' in st.session_state:
            st.query_params.folder_path = st.session_state['folder_path']
