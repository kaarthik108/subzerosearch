import streamlit as st
from snowflake.cortex import complete
from utils.snowflake_utils import SnowflakeConnection
from typing import Dict, List
import logging
from dataclasses import dataclass
from utils.shared import get_file_paths
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration settings"""
    PAGE_TITLE: str = "SubZeroSearch - ATS for Recruiters"
    LAYOUT: str = "centered"
    INITIAL_SIDEBAR_STATE: str = "collapsed"
    SEARCH_MODEL: str = "mistral-large2"
    RESPONSE_MODEL: str = "mistral-large2"


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
                self.config.RESPONSE_MODEL,
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
            folder_path = st.query_params.get(
                'folder_path', None) or st.session_state.get("folder_path", "")
            if not folder_path:
                raise ValueError(
                    "Please upload the resumes")

            # Ensure folder_path is a string and properly formatted
            folder_path = str(folder_path).strip().strip('"').strip("'")
            logger.info(f"Using folder path: {folder_path}")

            file_paths = get_file_paths(folder_path)
            logger.info(f"File paths: {file_paths}")

            filter_conditions = [
                {"@eq": {"RELATIVE_PATH": path}} for path in file_paths
            ]

            # Ensure filter is always an array
            if len(filter_conditions) == 1:
                filter_conditions = [filter_conditions[0]]

            return self.search_service.search(
                query=query,
                columns=["chunk"],
                limit=10,
                filter={"@or": filter_conditions}
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
        print("\n\nsession state messages\n\n", st.session_state.messages)
        response_placeholder = st.empty()
        response = ""

        # Stream the response
        for chunk in complete(
            'mistral-large2',
            full_prompt,
            session=SnowflakeConnection.get_connection(),
            stream=True
        ):
            # Clear the loading placeholder on first chunk
            if not response:
                st.session_state.get('loading_placeholder', st.empty()).empty()

            response += chunk
            response_placeholder.markdown(f"""
                <div class="message-wrapper assistant">
                    <div class="avatar assistant-avatar">
                        <img src="{st.secrets['LOGO_URL']}" alt="Assistant Logo"/>
                    </div>
                    <div class="message-content">{response if chunk else "Loading..."}</div>
                </div>
            """, unsafe_allow_html=True)

        # Update the last message in session state with the full response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "source_documents": source_documents
        })

        # Show source documents for the current message
        with st.expander("📄 View Source Documents"):
            st.json(source_documents)
