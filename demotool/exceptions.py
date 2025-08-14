"""
Custom exception classes for demotool.
"""


class DemotoolError(Exception):
    """Base exception class for all demotool errors."""
    pass


class VMError(DemotoolError):
    """Exception raised for VM-related errors."""
    pass


class ImageError(DemotoolError):
    """Exception raised for image-related errors."""
    pass


class SessionError(DemotoolError):
    """Exception raised for demo session errors."""
    pass


class ResourceError(DemotoolError):
    """Exception raised for resource allocation errors."""
    pass


class VNCError(DemotoolError):
    """Exception raised for VNC-related errors."""
    pass
