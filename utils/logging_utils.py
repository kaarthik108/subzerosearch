import logging


def setup_logging(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """Setup logging configuration."""
    logging.basicConfig(level=level, format=format)
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger('snowflake.connector').setLevel(logging.WARNING)
    logging.getLogger('snowflake.snowpark').setLevel(logging.WARNING)
    logging.getLogger(
        'snowflake.core.session._generated.api.session_api').setLevel(logging.WARNING)
    return logging.getLogger(__name__)
