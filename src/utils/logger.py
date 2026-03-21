import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Configure once in app factory via logging.basicConfig."""
    return logging.getLogger(name)
