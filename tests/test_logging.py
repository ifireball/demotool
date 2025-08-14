"""
Tests for the logging module.
"""

import logging
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from demotool.logging import FileLineFormatter, setup_logging, get_logger


class TestFileLineFormatter:
    """Test the FileLineFormatter class."""
    
    def test_format_with_filename_lineno(self):
        """Test formatting with filename and line number."""
        formatter = FileLineFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        assert result == "INFO: test.py:42: Test message"
    
    def test_format_without_filename_lineno(self):
        """Test formatting without filename and line number."""
        formatter = FileLineFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        assert result == "ERROR: unknown:0: Test message"


class TestSetupLogging:
    """Test the setup_logging function."""
    
    def test_setup_logging_default_level(self):
        """Test setting up logging with default level."""
        with patch.dict(os.environ, {}, clear=True):
            setup_logging()
            
            logger = logging.getLogger("demotool")
            assert logger.level == logging.INFO
            assert len(logger.handlers) == 1
            
            handler = logger.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            # Check that it's writing to stderr (the exact name may vary)
            assert handler.stream == sys.stderr
    
    def test_setup_logging_custom_level(self):
        """Test setting up logging with custom level."""
        setup_logging("DEBUG")
        
        logger = logging.getLogger("demotool")
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_from_environment(self):
        """Test setting up logging from environment variable."""
        with patch.dict(os.environ, {"DEMOTOOL_LOG_LEVEL": "WARNING"}):
            setup_logging()
            
            logger = logging.getLogger("demotool")
            assert logger.level == logging.WARNING
    
    def test_setup_logging_invalid_level(self):
        """Test setting up logging with invalid level."""
        with pytest.raises(ValueError, match="Invalid log level: INVALID"):
            setup_logging("INVALID")
    
    def test_setup_logging_multiple_calls(self):
        """Test that multiple calls don't create duplicate handlers."""
        setup_logging()
        setup_logging()
        
        logger = logging.getLogger("demotool")
        assert len(logger.handlers) == 1


class TestGetLogger:
    """Test the get_logger function."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        setup_logging()
        
        logger = get_logger("test.module")
        assert logger.name == "demotool.test.module"
        # The logger level should inherit from parent, not be explicitly set
        assert logger.level == 0  # NOTSET, which means inherit from parent
        
        # Should inherit handlers from parent logger
        parent_logger = logging.getLogger("demotool")
        assert len(parent_logger.handlers) == 1
