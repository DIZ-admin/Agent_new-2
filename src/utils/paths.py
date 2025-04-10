#!/usr/bin/env python3
"""
Paths and File System Utilities Module

This module provides centralized path definitions and file system operations.
"""

import os
import shutil
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Union, Optional, BinaryIO, TextIO
import tempfile

from .config import get_config
from .logging import get_logger

logger = get_logger(__name__)


class PathManager:
    """Manages all paths for the application."""
    
    def __init__(self):
        """Initialize path manager with configuration."""
        config = get_config()
        self.base_dir = config.base_dir
        self.config_dir = config.config_dir
        self.data_dir = config.data_dir
        self.logs_dir = config.logs_dir
        
        # Create data subdirectories
        self.downloads_dir = self.data_dir / "downloads"
        self.metadata_dir = self.data_dir / "metadata"
        self.analysis_dir = self.data_dir / "analysis"
        self.upload_dir = self.data_dir / "upload"
        self.upload_metadata_dir = self.upload_dir / "metadata"
        self.uploaded_dir = self.data_dir / "uploaded"
        self.reports_dir = self.data_dir / "reports"
        
        # Ensure all directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.downloads_dir,
            self.metadata_dir,
            self.analysis_dir,
            self.upload_dir,
            self.upload_metadata_dir,
            self.uploaded_dir,
            self.reports_dir
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def get_schema_path(self) -> Path:
        """Get path to the metadata schema file."""
        config = get_config()
        return self.config_dir / config.file.metadata_schema_file
    
    def get_download_path(self, filename: str) -> Path:
        """Get path for downloading a file."""
        return self.downloads_dir / filename
    
    def get_metadata_path(self, filename: str, extension: str = ".json") -> Path:
        """Get path for metadata file."""
        base_name = Path(filename).stem
        return self.metadata_dir / f"{base_name}{extension}"
    
    def get_analysis_path(self, filename: str) -> Path:
        """Get path for analysis result file."""
        base_name = Path(filename).stem
        return self.analysis_dir / f"{base_name}_analysis.json"
    
    def get_upload_path(self, filename: str) -> Path:
        """Get path for file to be uploaded."""
        return self.upload_dir / filename
    
    def get_upload_metadata_path(self, filename: str, extension: str = ".json") -> Path:
        """Get path for metadata file to be uploaded."""
        base_name = Path(filename).stem
        return self.upload_metadata_dir / f"{base_name}{extension}"
    
    def get_uploaded_path(self, filename: str) -> Path:
        """Get path for uploaded file."""
        return self.uploaded_dir / filename
    
    def get_report_path(self, report_name: str) -> Path:
        """Get path for report file."""
        return self.reports_dir / report_name


# Global path manager instance
_path_manager = None


def get_path_manager() -> PathManager:
    """Get the path manager instance."""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename.
    
    Args:
        filename (str): Filename to sanitize
        
    Returns:
        str: Safe filename
    """
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "")
    
    return filename


def ensure_unique_filename(path: Path) -> Path:
    """
    Ensure the filename is unique by adding a number if needed.
    
    Args:
        path (Path): Path to check
        
    Returns:
        Path: Unique path
    """
    if not path.exists():
        return path
    
    directory = path.parent
    stem = path.stem
    suffix = path.suffix
    
    counter = 1
    while True:
        new_path = directory / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def load_json_file(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a JSON file.
    
    Args:
        path (Union[str, Path]): Path to JSON file
        
    Returns:
        Dict[str, Any]: Loaded JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    path = Path(path)
    logger.debug(f"Loading JSON file: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], path: Union[str, Path]) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data (Dict[str, Any]): Data to save
        path (Union[str, Path]): Path to save to
        
    Raises:
        OSError: If the file cannot be written
    """
    path = Path(path)
    logger.debug(f"Saving JSON file: {path}")
    
    # Ensure directory exists
    path.parent.mkdir(exist_ok=True, parents=True)
    
    try:
        # Use atomic write to prevent corruption
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=str(path.parent)) as temp:
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp_path = temp.name
        
        # Rename temp file to target file
        shutil.move(temp_path, path)
    except UnicodeEncodeError:
        # Fall back to binary mode with explicit UTF-8 encoding if Unicode error occurs
        logger.warning(f"Unicode encode error occurred, falling back to binary mode for {path}")
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, dir=str(path.parent)) as temp:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            temp.write(json_str.encode('utf-8'))
            temp_path = temp.name
        
        # Rename temp file to target file
        shutil.move(temp_path, path)


def load_yaml_file(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a YAML file.
    
    Args:
        path (Union[str, Path]): Path to YAML file
        
    Returns:
        Dict[str, Any]: Loaded YAML data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the file is not valid YAML
    """
    path = Path(path)
    logger.debug(f"Loading YAML file: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml_file(data: Dict[str, Any], path: Union[str, Path]) -> None:
    """
    Save data to a YAML file.
    
    Args:
        data (Dict[str, Any]): Data to save
        path (Union[str, Path]): Path to save to
        
    Raises:
        OSError: If the file cannot be written
    """
    path = Path(path)
    logger.debug(f"Saving YAML file: {path}")
    
    # Ensure directory exists
    path.parent.mkdir(exist_ok=True, parents=True)
    
    # Use atomic write to prevent corruption
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=str(path.parent)) as temp:
        yaml.dump(data, temp, default_flow_style=False, allow_unicode=True)
        temp_path = temp.name
    
    # Rename temp file to target file
    shutil.move(temp_path, path)


def copy_file(source: Union[str, Path], target: Union[str, Path]) -> Path:
    """
    Copy a file with error handling.
    
    Args:
        source (Union[str, Path]): Source path
        target (Union[str, Path]): Target path
        
    Returns:
        Path: Path to the copied file
        
    Raises:
        FileNotFoundError: If the source file doesn't exist
        OSError: If the file cannot be copied
    """
    source = Path(source)
    target = Path(target)
    logger.debug(f"Copying file from {source} to {target}")
    
    # Ensure target directory exists
    target.parent.mkdir(exist_ok=True, parents=True)
    
    # Copy file
    return Path(shutil.copy2(source, target))


def move_file(source: Union[str, Path], target: Union[str, Path]) -> Path:
    """
    Move a file with error handling.
    
    Args:
        source (Union[str, Path]): Source path
        target (Union[str, Path]): Target path
        
    Returns:
        Path: Path to the moved file
        
    Raises:
        FileNotFoundError: If the source file doesn't exist
        OSError: If the file cannot be moved
    """
    source = Path(source)
    target = Path(target)
    logger.debug(f"Moving file from {source} to {target}")
    
    # Ensure target directory exists
    target.parent.mkdir(exist_ok=True, parents=True)
    
    # Move file
    return Path(shutil.move(source, target))


def list_files(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
    """
    List files in a directory matching a pattern.
    
    Args:
        directory (Union[str, Path]): Directory to list
        pattern (str): Glob pattern to match
        
    Returns:
        List[Path]: List of matching file paths
    """
    directory = Path(directory)
    logger.debug(f"Listing files in {directory} with pattern {pattern}")
    
    return sorted(directory.glob(pattern))


def list_files_by_extension(directory: Union[str, Path], extensions: List[str]) -> List[Path]:
    """
    List files in a directory with specific extensions.
    
    Args:
        directory (Union[str, Path]): Directory to list
        extensions (List[str]): List of extensions to match (e.g., ['.jpg', '.png'])
        
    Returns:
        List[Path]: List of matching file paths
    """
    directory = Path(directory)
    logger.debug(f"Listing files in {directory} with extensions {extensions}")
    
    # Normalize extensions to lowercase and ensure they start with a dot
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    # Find matching files
    result = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in extensions:
            result.append(path)
    
    return sorted(result)


def list_image_files(directory: Union[str, Path]) -> List[Path]:
    """
    List image files in a directory.
    
    Args:
        directory (Union[str, Path]): Directory to list
        
    Returns:
        List[Path]: List of image file paths
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    return list_files_by_extension(directory, image_extensions)


def ensure_file_exists(path: Union[str, Path]) -> bool:
    """
    Check if a file exists and raise a FileNotFoundError if not.
    
    Args:
        path (Union[str, Path]): Path to check
        
    Returns:
        bool: True if the file exists
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return True


def clean_directory(directory: Union[str, Path]) -> None:
    """
    Remove all files in a directory.
    
    Args:
        directory (Union[str, Path]): Directory to clean
    """
    directory = Path(directory)
    logger.debug(f"Cleaning directory: {directory}")
    
    if directory.exists():
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
                logger.debug(f"Removed file: {item}")


def get_file_size(path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        path (Union[str, Path]): Path to file
        
    Returns:
        int: File size in bytes
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(path)
    ensure_file_exists(path)
    return path.stat().st_size


def get_file_extension(path: Union[str, Path]) -> str:
    """
    Get the extension of a file.
    
    Args:
        path (Union[str, Path]): Path to file
        
    Returns:
        str: File extension (with dot)
    """
    return Path(path).suffix


def get_file_name(path: Union[str, Path]) -> str:
    """
    Get the name of a file without extension.
    
    Args:
        path (Union[str, Path]): Path to file
        
    Returns:
        str: File name without extension
    """
    return Path(path).stem


def get_file_name_with_extension(path: Union[str, Path]) -> str:
    """
    Get the name of a file with extension.
    
    Args:
        path (Union[str, Path]): Path to file
        
    Returns:
        str: File name with extension
    """
    return Path(path).name


# For direct testing
if __name__ == "__main__":
    # Test path manager
    path_manager = get_path_manager()
    print(f"Base directory: {path_manager.base_dir}")
    print(f"Downloads directory: {path_manager.downloads_dir}")
    
    # Test file operations
    test_dir = path_manager.data_dir / "test"
    test_dir.mkdir(exist_ok=True)
    
    # Create a test file
    test_file = test_dir / "test.json"
    test_data = {"test": "data", "num": 123}
    save_json_file(test_data, test_file)
    
    # Load the test file
    loaded_data = load_json_file(test_file)
    print(f"Loaded data: {loaded_data}")
    
    # List files
    print(f"Files in test directory: {list_files(test_dir)}")
    
    # Clean up
    clean_directory(test_dir)
    print(f"Files after cleaning: {list_files(test_dir)}")
    test_dir.rmdir()
