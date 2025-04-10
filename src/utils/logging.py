#!/usr/bin/env python3
"""
Logging Module

This module provides centralized logging setup and utilities for the application.
"""

import os
import sys
import logging
import functools
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Any, Optional, Dict, Union

from .config import get_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name and date-based log file.

    Args:
        name (str): Logger name

    Returns:
        logging.Logger: Configured logger
    """
    config = get_config()

    # Create logger
    logger = logging.getLogger(name)

    # Only set up handlers if they don't exist yet
    if not logger.handlers:
        # Set log level
        log_level = getattr(logging, config.logging.log_level)
        logger.setLevel(log_level)

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )

        # Create date-based log filename
        today = datetime.now().strftime('%Y-%m-%d')
        base_name = os.path.splitext(config.logging.log_file)[0]
        extension = os.path.splitext(config.logging.log_file)[1] or '.log'
        log_filename = f"{base_name}_{today}{extension}"
        log_file_path = config.logs_dir / log_filename

        # Create file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(detailed_formatter)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Create a symlink or copy to the default log file for backward compatibility
        default_log_path = config.logs_dir / config.logging.log_file
        try:
            # Try to create a symlink first (works on Unix-like systems)
            if os.path.exists(default_log_path):
                os.remove(default_log_path)
            os.symlink(log_file_path, default_log_path)
        except (OSError, AttributeError):
            # If symlink fails (e.g., on Windows), create a copy
            if os.path.exists(default_log_path):
                with open(default_log_path, 'w') as f:
                    f.write(f"Log redirected to {log_filename}\n")

    return logger


def get_timestamped_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name and a timestamp in the log filename.
    Useful for creating unique log files per run.

    Args:
        name (str): Logger name

    Returns:
        logging.Logger: Configured logger
    """
    config = get_config()

    # Create logger
    logger = logging.getLogger(name)

    # Only set up handlers if they don't exist yet
    if not logger.handlers:
        # Set log level
        log_level = getattr(logging, config.logging.log_level)
        logger.setLevel(log_level)

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )

        # Create timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(config.logging.log_file)[0]
        extension = os.path.splitext(config.logging.log_file)[1] or '.log'
        log_filename = f"{base_name}_{timestamp}{extension}"
        log_file_path = config.logs_dir / log_filename

        # Create file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(detailed_formatter)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def log_execution(function: Callable) -> Callable:
    """
    Decorator to log function execution with timing.

    Args:
        function (Callable): The function to decorate

    Returns:
        Callable: Decorated function
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger = get_logger(function.__module__)
        func_name = function.__name__

        logger.info(f"Starting {func_name}")
        start_time = time.time()

        try:
            result = function(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.info(f"Completed {func_name} in {elapsed_time:.2f} seconds")
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error in {func_name} after {elapsed_time:.2f} seconds: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise

    return wrapper


def handle_exceptions(function: Callable) -> Callable:
    """
    Decorator to handle exceptions and log them.

    Args:
        function (Callable): The function to decorate

    Returns:
        Callable: Decorated function
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger = get_logger(function.__module__)
        func_name = function.__name__

        try:
            return function(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func_name}: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise

    return wrapper


def rotate_logs(max_days: int = 30) -> None:
    """
    Rotate logs by removing files older than max_days.

    Args:
        max_days (int): Maximum age of log files in days
    """
    config = get_config()
    logs_dir = config.logs_dir

    # Get current time
    now = datetime.now()

    # List all log files
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]

    # Check each log file
    for log_file in log_files:
        # Skip the main log file (which is a symlink or redirect)
        if log_file == config.logging.log_file:
            continue

        log_path = os.path.join(logs_dir, log_file)

        # Get file modification time
        mtime = datetime.fromtimestamp(os.path.getmtime(log_path))

        # Calculate age in days
        age_days = (now - mtime).days

        # Remove if older than max_days
        if age_days > max_days:
            try:
                os.remove(log_path)
                print(f"Removed old log file: {log_file} (age: {age_days} days)")
            except Exception as e:
                print(f"Error removing log file {log_file}: {str(e)}")


class ProgressLogger:
    """
    Logger for tracking progress of operations.
    """

    def __init__(self, name: str, total: int, update_interval: int = 1):
        """
        Initialize the progress logger.

        Args:
            name (str): Name of the progress operation
            total (int): Total number of items to process
            update_interval (int): Interval for logging progress (in percentage)
        """
        self.logger = get_logger(f"progress.{name}")
        self.name = name
        self.total = total
        self.current = 0
        self.last_percentage = 0
        self.update_interval = update_interval
        self.start_time = time.time()

        self.logger.info(f"Starting {name} with {total} items")

    def update(self, increment: int = 1, additional_info: str = "") -> None:
        """
        Update progress and log if necessary.

        Args:
            increment (int): Number of items to increment
            additional_info (str): Additional information to log
        """
        self.current += increment

        if self.total == 0:
            percentage = 100
        else:
            percentage = min(int((self.current / self.total) * 100), 100)

        # Log if percentage has changed by at least update_interval
        if percentage >= self.last_percentage + self.update_interval or percentage == 100:
            elapsed = time.time() - self.start_time
            items_per_second = self.current / elapsed if elapsed > 0 else 0

            message = f"{self.name}: {percentage}% complete ({self.current}/{self.total}, {items_per_second:.2f} items/sec)"
            if additional_info:
                message += f" - {additional_info}"

            self.logger.info(message)
            self.last_percentage = percentage

    def complete(self, additional_info: str = "") -> None:
        """
        Mark progress as complete and log final statistics.

        Args:
            additional_info (str): Additional information to log
        """
        elapsed = time.time() - self.start_time
        items_per_second = self.current / elapsed if elapsed > 0 else 0

        message = f"Completed {self.name}: {self.current} items in {elapsed:.2f} seconds ({items_per_second:.2f} items/sec)"
        if additional_info:
            message += f" - {additional_info}"

        self.logger.info(message)


# For direct testing
if __name__ == "__main__":
    # Test basic logger
    logger = get_logger("test")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Test progress logger
    progress = ProgressLogger("test_operation", 10)
    for i in range(10):
        time.sleep(0.1)  # Simulate work
        progress.update(1, f"Processed item {i+1}")
    progress.complete("All done!")

    # Test decorators
    @log_execution
    def test_function(a, b):
        print(f"Test function: {a} + {b} = {a + b}")
        return a + b

    @handle_exceptions
    def error_function():
        raise ValueError("Test error")

    test_function(3, 4)

    try:
        error_function()
    except ValueError:
        print("Error caught as expected")
