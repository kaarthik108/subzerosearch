import streamlit as st
from pathlib import Path
from utils.logging_utils import setup_logging

logger = setup_logging()


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
