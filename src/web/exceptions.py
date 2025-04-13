"""
Exceptions Module

This module provides custom exceptions for the web interface.
"""

class WebInterfaceError(Exception):
    """Base class for all exceptions in the web interface."""
    pass


class FileValidationError(WebInterfaceError):
    """Exception raised when file validation fails."""
    pass


class ProcessExecutionError(WebInterfaceError):
    """Exception raised when process execution fails."""
    pass


class MetadataError(WebInterfaceError):
    """Exception raised when metadata processing fails."""
    pass


class PathSecurityError(WebInterfaceError):
    """Exception raised when a path security check fails."""
    pass


class TimeoutError(WebInterfaceError):
    """Exception raised when an operation times out."""
    pass
