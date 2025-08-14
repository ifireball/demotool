"""
Tests for the custom exception classes.
"""

import pytest

from demotool.exceptions import (
    DemotoolError,
    VMError,
    ImageError,
    SessionError,
    ResourceError,
    VNCError
)


class TestExceptions:
    """Test all custom exception classes."""
    
    def test_demotool_error_inheritance(self):
        """Test that DemotoolError inherits from Exception."""
        error = DemotoolError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    def test_vm_error_inheritance(self):
        """Test that VMError inherits from DemotoolError."""
        error = VMError("VM error")
        assert isinstance(error, DemotoolError)
        assert isinstance(error, Exception)
        assert str(error) == "VM error"
    
    def test_image_error_inheritance(self):
        """Test that ImageError inherits from DemotoolError."""
        error = ImageError("Image error")
        assert isinstance(error, DemotoolError)
        assert isinstance(error, Exception)
        assert str(error) == "Image error"
    
    def test_session_error_inheritance(self):
        """Test that SessionError inherits from DemotoolError."""
        error = SessionError("Session error")
        assert isinstance(error, DemotoolError)
        assert isinstance(error, Exception)
        assert str(error) == "Session error"
    
    def test_resource_error_inheritance(self):
        """Test that ResourceError inherits from DemotoolError."""
        error = ResourceError("Resource error")
        assert isinstance(error, DemotoolError)
        assert isinstance(error, Exception)
        assert str(error) == "Resource error"
    
    def test_vnc_error_inheritance(self):
        """Test that VNCError inherits from DemotoolError."""
        error = VNCError("VNC error")
        assert isinstance(error, DemotoolError)
        assert isinstance(error, Exception)
        assert str(error) == "VNC error"
    
    def test_exception_hierarchy(self):
        """Test the complete exception hierarchy."""
        # All should be instances of the base class
        vm_error = VMError("test")
        image_error = ImageError("test")
        session_error = SessionError("test")
        resource_error = ResourceError("test")
        vnc_error = VNCError("test")
        
        assert isinstance(vm_error, DemotoolError)
        assert isinstance(image_error, DemotoolError)
        assert isinstance(session_error, DemotoolError)
        assert isinstance(resource_error, DemotoolError)
        assert isinstance(vnc_error, DemotoolError)
        
        # All should be instances of Exception
        assert isinstance(vm_error, Exception)
        assert isinstance(image_error, Exception)
        assert isinstance(session_error, Exception)
        assert isinstance(resource_error, Exception)
        assert isinstance(vnc_error, Exception)
    
    def test_exception_with_context(self):
        """Test exceptions with additional context."""
        error = VMError("Failed to start VM", "vm-name", "timeout")
        assert "Failed to start VM" in str(error)
    
    def test_exception_attributes(self):
        """Test that exceptions can store additional attributes."""
        error = ImageError("Image creation failed")
        error.image_path = "/path/to/image.qcow2"
        error.distro = "fedora"
        error.version = "42"
        
        assert error.image_path == "/path/to/image.qcow2"
        assert error.distro == "fedora"
        assert error.version == "42"
