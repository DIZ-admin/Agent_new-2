"""
Web Interface Utilities

This module provides utility functions for the web interface.
"""

import os
import json
import signal
import time
from pathlib import Path
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename

from src.utils.logging import get_logger
from src.web.exceptions import PathSecurityError, TimeoutError

# Get logger
logger = get_logger('web.utils')


def safe_path_join(base_dir, filename):
    """
    Safely join base directory and filename, ensuring the result stays within the base directory.
    
    Args:
        base_dir (str): Base directory path
        filename (str): Filename to append
        
    Returns:
        Path: Safely joined path
        
    Raises:
        PathSecurityError: If the resulting path would be outside the base directory
    """
    # Sanitize filename
    safe_filename = secure_filename(filename)
    
    # Create absolute paths
    base_path = Path(base_dir).resolve()
    full_path = base_path.joinpath(safe_filename).resolve()
    
    # Check if the path is within the base directory
    if not str(full_path).startswith(str(base_path)):
        logger.warning(f"Security: Attempted path traversal: {filename} -> {full_path}")
        raise PathSecurityError(f"Invalid path: {filename}")
        
    return full_path


def handle_api_error(error, default_message="An error occurred", redirect_route='main.index'):
    """
    Handle API errors with logging, flashing a message and redirecting.
    
    Args:
        error: The exception that occurred
        default_message (str): Default message to show to the user
        redirect_route (str): Route to redirect to
        
    Returns:
        Response: Redirect response
    """
    error_message = str(error)
    logger.error(f"{default_message}: {error_message}")
    flash(f"{default_message}: {error_message}", "danger")
    return redirect(url_for(redirect_route))


def log_with_context(logger_func, message, context=None):
    """
    Log a message with structured context data.
    
    Args:
        logger_func: Logging function (e.g. logger.info)
        message (str): Log message
        context (dict, optional): Additional context data
    """
    if context:
        # Convert dict to JSON string, handling non-serializable objects
        json_context = json.dumps(context, default=str)
        logger_func(f"{message} {json_context}")
    else:
        logger_func(message)


class Timeout:
    """
    Context manager for timing out operations.
    
    Usage:
        with Timeout(seconds=5):
            # code that might hang
    """
    def __init__(self, seconds, error_message='Operation timed out'):
        self.seconds = seconds
        self.error_message = error_message
        
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
        
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
        
    def __exit__(self, type, value, traceback):
        signal.alarm(0)  # Disable the alarm


def with_timeout(seconds):
    """
    Decorator to apply timeout to a function.
    
    Args:
        seconds (int): Timeout in seconds
        
    Returns:
        function: Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timeout(seconds=seconds):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Performance monitoring
class Timer:
    """
    Context manager for timing operations.
    
    Usage:
        with Timer() as t:
            # code to time
        print(f"Operation took {t.elapsed:.3f} seconds")
    """
    def __init__(self):
        self.start_time = None
        self.elapsed = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, type, value, traceback):
        self.elapsed = time.time() - self.start_time
