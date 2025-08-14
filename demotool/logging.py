"""
Logging configuration for demotool.
"""

import logging
import os
import sys
from typing import Optional


class FileLineFormatter(logging.Formatter):
    """Custom formatter that includes filename and line number."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get the caller's filename and line number
        if record.filename and record.lineno:
            location = f"{record.filename}:{record.lineno}"
        else:
            location = "unknown:0"
        
        # Format: {level}: {filename}:{lineno}: {message}
        return f"{record.levelname}: {location}: {record.getMessage()}"


def setup_logging(level: Optional[str] = None) -> None:
    """
    Set up logging configuration for demotool.
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses DEMOTOOL_LOG_LEVEL environment variable or defaults to INFO
    """
    if level is None:
        level = os.environ.get("DEMOTOOL_LOG_LEVEL", "INFO")
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    
    # Create logger
    logger = logging.getLogger("demotool")
    logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    
    # Set formatter
    formatter = FileLineFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"demotool.{name}")
