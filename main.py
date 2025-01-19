import logging
import streamlit as st
from typing import List, Dict, Optional
from dataclasses import dataclass
from snowflake.cortex import complete
from utils import upload_to_snowflake, render_sidebar
import time
from pathlib import Path
from snowflake_utils import SnowflakeConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration settings"""
    PAGE_TITLE: str = "SubZeroSearch - ATS for Recruiters"
    LAYOUT: str = "centered"
    INITIAL_SIDEBAR_STATE: str = "expanded"
    MODELS: List[str] = None

    def __post_init__(self):
        self.MODELS = [
            "mistral-large2",
        ]


class SessionStateManager:
    """Manages Streamlit session state"""

    @staticmethod
    def initialize_session_state():
        """Initialize session state variables"""
        default_states = {
            "chat_mode": True,
            "uploaded_files": [],
            "folder_path": "resume/2025-01-17/OS1VsLBk",
            "uploading": False
        }

        # Initialize basic session states
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

        # Initialize messages with a simple welcome conversation
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


class UIManager:
    """Manages UI components and styling"""

    @staticmethod
    @st.cache_resource
    def load_css(file_name: str):
        """Load and apply CSS styles"""
        try:
            css_path = Path(file_name)
            if not css_path.exists():
                raise FileNotFoundError(f"CSS file not found: {file_name}")

            with open(css_path) as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
            st.markdown(f"""<style>.user-img {{
                            width: 100%;
                            height: 100%;
                            background-image: url('{st.secrets.AVATAR_URL}');
                            background-size: cover;
                            background-position: center;
                             }}</style>""",
                        unsafe_allow_html=True)

        except Exception as e:
            logger.error(f"Failed to load CSS: {str(e)}")
            raise


class FileUploadHandler:
    """Handles file upload operations"""

    @staticmethod
    def process_uploaded_files(uploaded_files) -> None:
        """Process and upload files to Snowflake"""
        if not uploaded_files:
            return

        try:
            for file in uploaded_files:
                file_data = file.read()
                upload_to_snowflake(file.name, file_data)
                logger.info(f"Successfully uploaded {file.name}")
                st.markdown(
                    f'<div class="success-message">✨ Successfully uploaded {file.name}</div>',
                    unsafe_allow_html=True
                )
        except Exception as e:
            logger.error(f"Error uploading files: {str(e)}")
            st.markdown(
                f'<div class="error-message">❌ Error uploading files: {str(e)}</div>',
                unsafe_allow_html=True
            )
            raise


class ChatHandler:
    """Handles chat operations and interactions"""

    def __init__(self, snowflake_session, config: AppConfig, slide_window: int = 5):
        self.search_service = SnowflakeConnection.get_search_service(
            snowflake_session)
        self.slide_window = slide_window
        self.config = config

    def get_chat_history(self) -> List[Dict]:
        """Get recent chat history based on slide window"""
        messages = st.session_state.get("messages", [])
        start_index = max(0, len(messages) - self.slide_window)
        return messages[start_index:len(messages)-1]

    def summarize_with_history(self, chat_history: List[Dict], question: str) -> str:
        """Summarize question with chat history context"""
        prompt = f"""
            Based on the chat history below and the question, generate a query that extends the question
            with the chat history provided. The query should be in natural language.
            Answer with only the query. Do not add any explanation.

            <chat_history>
            {chat_history}
            </chat_history>
            <question>
            {question}
            </question>
        """

        try:
            summary = complete(
                self.config.MODELS[0],
                prompt,
                session=SnowflakeConnection.get_connection(),
                stream=False
            )
            return summary.replace("'", "")
        except Exception as e:
            logger.error(f"Error summarizing question with history: {str(e)}")
            raise

    def process_chat_message(self, prompt: str) -> None:
        """Process chat messages and generate responses"""
        try:
            # Get chat history and create context-aware query
            chat_history = self.get_chat_history()

            if chat_history:
                context_query = self.summarize_with_history(
                    chat_history, prompt)
                logger.info("Using summarized context query for search")
            else:
                context_query = prompt
                logger.info("Using direct prompt for search (no chat history)")

            search_response = self._perform_search(context_query)
            context_str = self._build_context(search_response.results)
            self._generate_response(
                prompt, context_str, search_response.to_json(), chat_history)
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            st.error(f"Error occurred: {str(e)}")

    def _perform_search(self, query: str):
        """Perform search operation"""
        try:
            return self.search_service.search(
                query=query,
                columns=["chunk"],
                limit=5
            )
        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            raise

    @staticmethod
    def _build_context(results: List[Dict]) -> str:
        """Build context string from search results"""
        return "\n".join([
            f"Context document {i+1}: {r['chunk']}"
            for i, r in enumerate(results)
        ])

    @staticmethod
    def _generate_response(prompt: str, context_str: str, source_documents: Dict, chat_history: List[Dict]):
        """Generate and display chat response"""
        full_prompt = f"""
        You are a helpful AI assistant for recruiters. Your task is to provide clear, concise, and relevant information about candidates based on their resumes.
        Use the following context to answer the question, and if you're not sure about something, please say so.
        Consider the chat history when providing your response to maintain conversation continuity.
        Do not mention the context or chat history used in your answer.
        Only answer the question if you can extract it from the context provided.

        Chat History:
        {chat_history}

        Context from resumes:
        {context_str}

        User Question: {prompt}
        """

        response_placeholder = st.empty()
        sources_placeholder = st.empty()
        response = ""

        for chunk in complete(
            'mistral-large2',
            full_prompt,
            session=SnowflakeConnection.get_connection(),
            stream=True
        ):
            response += chunk
            response_placeholder.markdown(f"""
                <div class="message-wrapper assistant">
                    <div class="avatar assistant-avatar">
                        <img src="{st.secrets['LOGO_URL']}" alt="Assistant Logo"/>
                    </div>
                    <div class="message-content">{response}</div>
                </div>
            """, unsafe_allow_html=True)

        with sources_placeholder.expander("📄 View Source Documents"):
            st.json(source_documents)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "source_documents": source_documents
        })


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
            '<div class="title">SubZeroSearch - ATS for Recruiters</div>',
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
            self._handle_file_upload(uploaded_files)

        st.markdown('</div>', unsafe_allow_html=True)

    def _handle_file_upload(self, uploaded_files):
        """Handle file upload process"""
        button_container = st.empty()

        if not st.session_state.get('uploading', False):
            if button_container.button("Upload Resumes"):
                st.session_state.uploading = True
                button_container.empty()

                spinner = st.empty()
                spinner.markdown(
                    '<div class="loading-spinner"></div>',
                    unsafe_allow_html=True
                )

                try:
                    FileUploadHandler.process_uploaded_files(uploaded_files)
                    time.sleep(1)
                    st.session_state["chat_mode"] = True
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
                        <img src="{st.secrets['LOGO_URL']}" class="logo-image" alt="SubZeroSearch Logo"/> SubZeroSearch
                    </div>
                    <h1 class="chat-title">
                        Find Your Perfect Candidate with <span class="gradient-text">AI-Powered Precision</span>
                    </h1>
                    <p class="chat-subtitle">
                        Instantly find the perfect candidates using AI-powered resume analysis
                    </p>
                    <div class="header-badges">
                        <span class="badge">Smart Matching</span>
                        <span class="badge">Instant Results</span>
                        <span class="badge">AI-Powered</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def _display_chat_history(self):
        """Display chat history"""
        for message in st.session_state.get("messages", []):
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

            if message["role"] == "assistant":
                with st.expander("📄 View Source Documents"):
                    if "source_documents" in message and message["source_documents"]:
                        st.json(message["source_documents"])
                    else:
                        st.info("No source documents available")

    def _handle_chat_input(self):
        """Handle chat input and responses"""
        if prompt := st.chat_input("Ask something about the resumes..."):
            st.markdown(f"""
                <div class="message-wrapper user">
                    <div class="avatar user-avatar">
                        <div class="user-img"></div>
                    </div>
                    <div class="message-content">{prompt}</div>
                </div>
            """, unsafe_allow_html=True)

            if "messages" not in st.session_state:
                st.session_state.messages = []
            st.session_state.messages.append(
                {"role": "user", "content": prompt})

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
