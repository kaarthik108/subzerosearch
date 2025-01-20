import logging
import streamlit as st
from utils.shared import upload_to_snowflake, render_sidebar
import time
from utils.snowflake_utils import SnowflakeConnection
from utils.ui import UIManager
from utils.chat import ChatHandler, AppConfig
from utils.state import SessionStateManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ATSApplication:
    """Main ATS application class"""

    def __init__(self):
        self.config = AppConfig()
        self.setup_app()
        SessionStateManager.initialize_session_state()
        UIManager.load_css("styles.css")
        self.chat_handler = ChatHandler(
            SnowflakeConnection.get_connection(),
            config=self.config
        )

    def setup_app(self):
        """Configure initial app settings"""
        st.set_page_config(
            page_title=self.config.PAGE_TITLE,
            layout=self.config.LAYOUT,
            initial_sidebar_state=self.config.INITIAL_SIDEBAR_STATE
        )

    def render_upload_ui(self):
        """Render file upload interface"""
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        st.markdown(
            f'''
            <div class="brand-logo">
                <img src="{st.secrets['LOGO_URL']}" class="logo-image" alt="SubZeroSearch Logo"/>
                <span class="title">SubZeroSearch</span>
            </div>
            ''',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="subtitle">Upload resumes and start searching for the perfect candidate!</div>',
            unsafe_allow_html=True
        )

        uploaded_files = st.file_uploader(
            "Drag and drop your resumes here",
            type="pdf",
            accept_multiple_files=True,
            key="resume_uploader"
        )

        if uploaded_files:
            # Adjust the column widths for centering
            # Make all columns equal width
            col1, col2, col3 = st.columns([2, 6, 2])  # Wider center column

            with col2:
                button_container = st.empty()
                success_messages = st.empty()

                if not st.session_state.get('uploading', False):
                    # Use Streamlit's button and center it using columns
                    if st.button("Upload Resumes", key="upload_button"):
                        st.session_state.uploading = True
                        button_container.empty()

                        spinner = st.empty()
                        spinner.markdown(
                            '<div class="loading-spinner"></div>',
                            unsafe_allow_html=True
                        )

                        try:
                            for file in uploaded_files:
                                file_data = file.read()
                                upload_to_snowflake(file.name, file_data)
                                logger.info(
                                    f"Successfully uploaded {file.name}")
                                success_messages.markdown(
                                    f'<div class="success-message">✨ Successfully uploaded {file.name}</div>',
                                    unsafe_allow_html=True
                                )

                            time.sleep(1)
                            success_messages.empty()  # Clear success messages before transition
                            st.session_state["chat_mode"] = True
                            st.session_state["indexing"] = True
                            st.rerun()
                        finally:
                            spinner.empty()
                            st.session_state.uploading = False

    def render_chat_ui(self):
        """Render chat interface"""
        self._render_header()
        render_sidebar()
        self._display_chat_history()
        self._handle_chat_input()

    def _render_header(self):
        """Render chat header"""
        st.markdown(f"""
            <div class="header-section">
                <div class="chat-header-content">
                    <div class="brand-logo">
                        <img src="{st.secrets['LOGO_URL']}" class="logo-image" alt="SubZeroSearch Logo"/>
                        <span class="chat-title">SubZeroSearch</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def _display_chat_history(self):
        """Display chat history"""
        messages = st.session_state.get("messages", [])

        for i, message in enumerate(messages):
            # Skip displaying source documents for the welcome message
            is_welcome_message = i <= 1  # First two messages are the welcome conversation

            role_class = "user" if message["role"] == "user" else "assistant"
            avatar_content = '<div class="user-img"></div>' if message[
                "role"] == "user" else f'<img src="{st.secrets["LOGO_URL"]}" alt="Assistant Logo"/>'
            avatar_class = "user-avatar" if message["role"] == "user" else "assistant-avatar"

            st.markdown(f"""
                <div class="message-wrapper {role_class}">
                    <div class="avatar {avatar_class}">{avatar_content}</div>
                    <div class="message-content">{message["content"]}</div>
                </div>
            """, unsafe_allow_html=True)

            if message["role"] == "assistant" and not is_welcome_message:
                with st.expander("📄 View Source Documents"):
                    if "source_documents" in message and message["source_documents"]:
                        st.json(message["source_documents"])
                    else:
                        st.info("No source documents available")

    def _handle_chat_input(self):
        """Handle chat input and responses"""
        if st.session_state.get("indexing", False):
            with st.container():
                st.markdown("""
                    <div class="indexing-container">
                        <div class="indexing-spinner"></div>
                        <div class="indexing-messages">
                            <h3>🚀 Initializing Search</h3>
                            <div class="message-content">
                                ⚡ Snowflake Cortex Search indexing will take up to 60 seconds... Hold on!
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                time.sleep(60)
                st.session_state["indexing"] = False
                st.rerun()

        if prompt := st.chat_input("Ask something about the resumes..."):
            # Display user message
            st.markdown(f"""
                <div class="message-wrapper user">
                    <div class="avatar user-avatar">
                        <div class="user-img"></div>
                    </div>
                    <div class="message-content">{prompt}</div>
                </div>
            """, unsafe_allow_html=True)

            # Append user message to session state
            if "messages" not in st.session_state:
                st.session_state.messages = []
            st.session_state.messages.append(
                {"role": "user", "content": prompt})

            placeholder_msg = st.empty()
            st.session_state['loading_placeholder'] = placeholder_msg
            placeholder_msg.markdown(
                f"""
                <div class="message-wrapper assistant">
                    <div class="avatar assistant-avatar">
                        <img src="{st.secrets['LOGO_URL']}" alt="Assistant Logo"/>
                    </div>
                    <div class="message-content">Loading...</div>
                </div>
                """, unsafe_allow_html=True)

            # Process the chat message
            self.chat_handler.process_chat_message(prompt)

    def run(self):
        """Run the application"""
        try:
            if st.session_state["chat_mode"]:
                self.render_chat_ui()
            else:
                st.session_state['folder_path'] = None
                self.render_upload_ui()
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            st.error("An unexpected error occurred. Please try again later.")


def main():
    """Main entry point"""
    try:
        app = ATSApplication()
        app.run()
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}")
        st.error("A critical error occurred. Please contact support.")


if __name__ == "__main__":
    main()
