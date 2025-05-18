import logging
import sys

from src.utils.config import config


def setup_logging(name: str = "openapi_server", level: int = logging.INFO, log_file: str = None):
    logger = logging.getLogger(f"[{name}]")

    # Enable DEBUG logs if running under pytest or unittest
    if "pytest" in sys.modules or "unittest" in sys.modules:
        level = logging.DEBUG
    
    if config.DEBUG:
        level = logging.DEBUG
    
    if not log_file:
        log_file = config.LOG_FILE

    logger.setLevel(level)
    # Always add a StreamHandler to ensure logs are visible, even in test environments
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # Optionally add a FileHandler if log_file is provided
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger