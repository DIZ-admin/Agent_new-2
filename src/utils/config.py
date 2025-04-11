#!/usr/bin/env python3
"""
Configuration Management Module

This module centralizes configuration loading and validation for the application.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class SharePointConfig:
    """Configuration for SharePoint connection."""
    site_url: str
    username: str
    password: str
    source_library_title: str
    target_library_title: str
    max_connection_attempts: int
    connection_retry_delay: int


@dataclass
class FileConfig:
    """Configuration for file handling."""
    metadata_schema_file: str
    target_filename_mask: str
    max_file_size: int


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI integration."""
    api_key: str
    concurrency_limit: int
    max_tokens: int
    prompt_role: str
    prompt_instructions_pre: str
    prompt_instructions_post: str
    prompt_example: str


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    log_level: str
    log_file: str


@dataclass
class AppConfig:
    """Main application configuration."""
    sharepoint: SharePointConfig
    file: FileConfig
    openai: OpenAIConfig
    logging: LoggingConfig
    base_dir: Path
    data_dir: Path
    config_dir: Path
    logs_dir: Path


def get_base_dir() -> Path:
    """Get the base directory of the application."""
    # Move two levels up from this file (utils/config.py -> src -> base)
    return Path(__file__).resolve().parent.parent.parent


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.

    Returns:
        AppConfig: Application configuration

    Raises:
        ValueError: If required configuration is missing
    """
    # Get base directory
    base_dir = get_base_dir()

    # Define directories
    config_dir = base_dir / "config"
    data_dir = base_dir / "data"
    logs_dir = base_dir / "logs"

    # Ensure directories exist
    logs_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Load environment variables
    # We'll load the file manually to handle multiline values correctly
    env_path = config_dir / "config.env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle quoted values
                    if value.startswith('"""') and value.endswith('"""'):
                        # Triple-quoted multiline string
                        value = value[3:-3]
                    elif value.startswith('"') and value.endswith('"'):
                        # Regular quoted string
                        value = value[1:-1]

                    # Set environment variable
                    os.environ[key] = value

    # Validate required variables
    required_vars = [
        "SHAREPOINT_SITE_URL",
        "SHAREPOINT_USERNAME",
        "SHAREPOINT_PASSWORD",
        "SOURCE_LIBRARY_TITLE",
        "SHAREPOINT_LIBRARY",
        "METADATA_SCHEMA_FILE",
        "OPENAI_API_KEY"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Create configuration objects
    sharepoint_config = SharePointConfig(
        site_url=os.getenv("SHAREPOINT_SITE_URL", ""),
        username=os.getenv("SHAREPOINT_USERNAME", ""),
        password=os.getenv("SHAREPOINT_PASSWORD", ""),
        source_library_title=os.getenv("SOURCE_LIBRARY_TITLE", ""),
        target_library_title=os.getenv("SHAREPOINT_LIBRARY", ""),
        max_connection_attempts=int(os.getenv("MAX_CONNECTION_ATTEMPTS", "3")),
        connection_retry_delay=int(os.getenv("CONNECTION_RETRY_DELAY", "5"))
    )

    file_config = FileConfig(
        metadata_schema_file=os.getenv("METADATA_SCHEMA_FILE", ""),
        target_filename_mask=os.getenv("TARGET_FILENAME_MASK", ""),
        max_file_size=int(os.getenv("MAX_FILE_SIZE", "15728640"))  # Default 15MB
    )

    openai_config = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        concurrency_limit=int(os.getenv("OPENAI_CONCURRENCY_LIMIT", "5")),
        max_tokens=int(os.getenv("MAX_TOKENS", "1000")),
        prompt_role=os.getenv("OPENAI_PROMPT_ROLE", ""),
        prompt_instructions_pre=os.getenv("OPENAI_PROMPT_INSTRUCTIONS_PRE", ""),
        prompt_instructions_post=os.getenv("OPENAI_PROMPT_INSTRUCTIONS_POST", ""),
        prompt_example=os.getenv("OPENAI_PROMPT_EXAMPLE", "")
    )

    logging_config = LoggingConfig(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "sharepoint_connector.log")
    )

    # Create and return the main configuration
    return AppConfig(
        sharepoint=sharepoint_config,
        file=file_config,
        openai=openai_config,
        logging=logging_config,
        base_dir=base_dir,
        data_dir=data_dir,
        config_dir=config_dir,
        logs_dir=logs_dir
    )


# Global configuration instance
_config = None
_config_last_modified = 0


def get_config(force_reload=False) -> AppConfig:
    """
    Get the application configuration.

    Args:
        force_reload (bool): Force reload the configuration

    Returns:
        AppConfig: Application configuration
    """
    global _config, _config_last_modified

    # Get the config.env file path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_dir = os.path.join(base_dir, 'config')
    env_path = os.path.join(config_dir, 'config.env')

    # Check if the file has been modified
    try:
        current_mtime = os.path.getmtime(env_path)
        file_changed = current_mtime > _config_last_modified
    except Exception:
        file_changed = False

    # Reload if needed
    if _config is None or force_reload or file_changed:
        _config = load_config()
        try:
            _config_last_modified = os.path.getmtime(env_path)
        except Exception:
            _config_last_modified = 0

    return _config


def reload_config() -> AppConfig:
    """
    Force reload the application configuration.

    Returns:
        AppConfig: Reloaded application configuration
    """
    return get_config(force_reload=True)


# For direct testing
if __name__ == "__main__":
    config = get_config()
    print(f"Configuration loaded from: {config.config_dir}")
    print(f"SharePoint site URL: {config.sharepoint.site_url}")
    print(f"Source library: {config.sharepoint.source_library_title}")
    print(f"Target library: {config.sharepoint.target_library_title}")
    print(f"OpenAI concurrency limit: {config.openai.concurrency_limit}")
