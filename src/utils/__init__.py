"""
Utilities Package

This package provides utility modules for the Agent project.
"""

from .config import get_config, AppConfig
from .logging import get_logger, log_execution, handle_exceptions, ProgressLogger, get_timestamped_logger, rotate_logs
from .paths import (
    get_path_manager,
    safe_filename,
    ensure_unique_filename,
    load_json_file,
    save_json_file,
    load_yaml_file,
    save_yaml_file,
    copy_file,
    move_file,
    list_files,
    list_files_by_extension,
    list_image_files,
    ensure_file_exists,
    clean_directory,
    get_file_size,
    get_file_extension,
    get_file_name,
    get_file_name_with_extension
)
from .api import retry, APIRateLimiter, CacheManager, APIClientBase
from .registry import get_registry, FileRegistry
from .sharepoint import get_sharepoint_context

__all__ = [
    # From config
    'get_config',
    'AppConfig',

    # From logging
    'get_logger',
    'log_execution',
    'handle_exceptions',
    'ProgressLogger',
    'get_timestamped_logger',
    'rotate_logs',

    # From paths
    'get_path_manager',
    'safe_filename',
    'ensure_unique_filename',
    'load_json_file',
    'save_json_file',
    'load_yaml_file',
    'save_yaml_file',
    'copy_file',
    'move_file',
    'list_files',
    'list_files_by_extension',
    'list_image_files',
    'ensure_file_exists',
    'clean_directory',
    'get_file_size',
    'get_file_extension',
    'get_file_name',
    'get_file_name_with_extension',

    # From api
    'retry',
    'APIRateLimiter',
    'CacheManager',
    'APIClientBase',

    # From registry
    'get_registry',
    'FileRegistry',

    # From sharepoint
    'get_sharepoint_context'
]
