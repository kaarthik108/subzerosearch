import logging


def setup_logging(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """Setup logging configuration."""
    logging.basicConfig(level=level, format=format)
    return logging.getLogger(__name__)
