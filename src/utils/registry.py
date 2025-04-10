#!/usr/bin/env python3
"""
File Registry Module

This module handles tracking of processed files to avoid duplicate processing.
"""

import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Union

from .config import get_config
from .logging import get_logger
from .paths import get_path_manager
from .paths import load_json_file, save_json_file

logger = get_logger(__name__)


class FileRegistry:
    """
    Registry for tracking processed and uploaded files.

    This maintains a persistent record of files that have been processed
    and uploaded to avoid duplicate processing.
    """

    def __init__(self):
        """Initialize the file registry."""
        self.path_manager = get_path_manager()
        self.registry_dir = self.path_manager.data_dir / "registry"
        self.registry_dir.mkdir(exist_ok=True)

        # Registry files
        self.processed_file = self.registry_dir / "processed_files.json"
        self.uploaded_file = self.registry_dir / "uploaded_files.json"
        self.file_hashes_file = self.registry_dir / "file_hashes.json"

        # Load registries
        self.processed = self._load_registry(self.processed_file)
        self.uploaded = self._load_registry(self.uploaded_file)
        self.file_hashes = self._load_registry(self.file_hashes_file)

        # Initialize file_hashes if needed
        if "hashes" not in self.file_hashes:
            self.file_hashes["hashes"] = {}

        logger.info(f"File registry initialized with {len(self.processed['files'])} processed and {len(self.uploaded['files'])} uploaded files")

    def _load_registry(self, file_path: Path) -> Dict[str, Any]:
        """
        Load registry from file or create a new one.

        Args:
            file_path (Path): Path to registry file

        Returns:
            Dict[str, Any]: Registry dictionary
        """
        if file_path.exists():
            try:
                return load_json_file(file_path)
            except Exception as e:
                logger.error(f"Error loading registry from {file_path}: {str(e)}")
                return {"files": {}, "last_updated": datetime.now().isoformat()}
        else:
            return {"files": {}, "last_updated": datetime.now().isoformat()}

    def _save_registry(self, registry: Dict[str, Any], file_path: Path) -> None:
        """
        Save registry to file.

        Args:
            registry (Dict[str, Any]): Registry dictionary
            file_path (Path): Path to registry file
        """
        registry["last_updated"] = datetime.now().isoformat()
        try:
            save_json_file(registry, file_path)
            logger.debug(f"Registry saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving registry to {file_path}: {str(e)}")

    def is_processed(self, filename: str) -> bool:
        """
        Check if a file has been processed.

        Args:
            filename (str): Filename to check

        Returns:
            bool: True if file has been processed, False otherwise
        """
        return filename in self.processed["files"]

    def is_uploaded(self, filename: str) -> bool:
        """
        Check if a file has been uploaded.

        Args:
            filename (str): Filename to check

        Returns:
            bool: True if file has been uploaded, False otherwise
        """
        return filename in self.uploaded["files"]

    def mark_as_processed(self, filename: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark a file as processed.

        Args:
            filename (str): Filename to mark
            metadata (Optional[Dict[str, Any]]): Additional metadata to store
        """
        self.processed["files"][filename] = {
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._save_registry(self.processed, self.processed_file)
        logger.debug(f"Marked {filename} as processed")

    def mark_as_uploaded(self, filename: str, target_url: Optional[str] = None) -> None:
        """
        Mark a file as uploaded.

        Args:
            filename (str): Filename to mark
            target_url (Optional[str]): URL of the uploaded file in SharePoint
        """
        self.uploaded["files"][filename] = {
            "timestamp": datetime.now().isoformat(),
            "target_url": target_url
        }
        self._save_registry(self.uploaded, self.uploaded_file)
        logger.debug(f"Marked {filename} as uploaded")

    def get_processed_files(self) -> List[str]:
        """
        Get list of processed files.

        Returns:
            List[str]: List of processed filenames
        """
        return list(self.processed["files"].keys())

    def get_uploaded_files(self) -> List[str]:
        """
        Get list of uploaded files.

        Returns:
            List[str]: List of uploaded filenames
        """
        return list(self.uploaded["files"].keys())

    def get_processing_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get processing metadata for a file.

        Args:
            filename (str): Filename to get metadata for

        Returns:
            Optional[Dict[str, Any]]: Processing metadata or None if not found
        """
        if filename in self.processed["files"]:
            return self.processed["files"][filename].get("metadata", {})
        return None

    def get_upload_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get upload information for a file.

        Args:
            filename (str): Filename to get upload info for

        Returns:
            Optional[Dict[str, Any]]: Upload information or None if not found
        """
        if filename in self.uploaded["files"]:
            return self.uploaded["files"][filename]
        return None

    def remove_from_processed(self, filename: str) -> bool:
        """
        Remove a file from the processed registry.

        Args:
            filename (str): Filename to remove

        Returns:
            bool: True if file was removed, False otherwise
        """
        if filename in self.processed["files"]:
            del self.processed["files"][filename]
            self._save_registry(self.processed, self.processed_file)
            logger.debug(f"Removed {filename} from processed registry")
            return True
        return False

    def remove_from_uploaded(self, filename: str) -> bool:
        """
        Remove a file from the uploaded registry.

        Args:
            filename (str): Filename to remove

        Returns:
            bool: True if file was removed, False otherwise
        """
        if filename in self.uploaded["files"]:
            del self.uploaded["files"][filename]
            self._save_registry(self.uploaded, self.uploaded_file)
            logger.debug(f"Removed {filename} from uploaded registry")
            return True
        return False

    def clear_registries(self) -> None:
        """
        Clear both registries.
        """
        self.processed = {"files": {}, "last_updated": datetime.now().isoformat()}
        self.uploaded = {"files": {}, "last_updated": datetime.now().isoformat()}
        self._save_registry(self.processed, self.processed_file)
        self._save_registry(self.uploaded, self.uploaded_file)
        logger.info("Registries cleared")

    def map_filename(self, original_filename: str, target_filename: str) -> None:
        """
        Map an original filename to a target filename.

        This is used to track the relationship between original filenames and their
        renamed versions in the target system.

        Args:
            original_filename (str): Original filename
            target_filename (str): Target filename
        """
        # Create a filename mapping if it doesn't exist
        if "filename_mapping" not in self.processed:
            self.processed["filename_mapping"] = {}

        # Add mapping
        self.processed["filename_mapping"][original_filename] = target_filename
        self._save_registry(self.processed, self.processed_file)
        logger.debug(f"Mapped {original_filename} to {target_filename}")

    def get_mapped_filename(self, original_filename: str) -> Optional[str]:
        """
        Get the mapped target filename for an original filename.

        Args:
            original_filename (str): Original filename

        Returns:
            Optional[str]: Target filename or None if not mapped
        """
        if "filename_mapping" not in self.processed:
            return None

        return self.processed["filename_mapping"].get(original_filename)

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file.

        Args:
            file_path (str): Path to the file

        Returns:
            str: MD5 hash of the file
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            # Return a unique string based on filename and size as fallback
            try:
                file_size = os.path.getsize(file_path)
                return f"fallback_{os.path.basename(file_path)}_{file_size}"
            except:
                return f"fallback_{os.path.basename(file_path)}"

    def is_file_processed_by_hash(self, file_path: str) -> bool:
        """
        Check if a file has been processed by its hash.

        Args:
            file_path (str): Path to the file

        Returns:
            bool: True if a file with the same hash has been processed
        """
        file_hash = self.calculate_file_hash(file_path)
        return file_hash in self.file_hashes["hashes"]

    def register_file_hash(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a file hash in the registry.

        Args:
            file_path (str): Path to the file
            metadata (Optional[Dict[str, Any]]): Additional metadata to store

        Returns:
            str: Hash of the file
        """
        file_hash = self.calculate_file_hash(file_path)
        filename = os.path.basename(file_path)

        self.file_hashes["hashes"][file_hash] = {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._save_registry(self.file_hashes, self.file_hashes_file)
        logger.debug(f"Registered hash for {filename}: {file_hash}")

        return file_hash

    def get_file_info_by_hash(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information by its hash.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[Dict[str, Any]]: File information or None if not found
        """
        file_hash = self.calculate_file_hash(file_path)
        return self.file_hashes["hashes"].get(file_hash)

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about processed and uploaded files.

        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        processed_count = len(self.processed["files"])
        uploaded_count = len(self.uploaded["files"])
        pending_upload = processed_count - uploaded_count

        # Count files by date
        processed_by_date = {}
        uploaded_by_date = {}

        for filename, info in self.processed["files"].items():
            date = info["timestamp"].split("T")[0]
            processed_by_date[date] = processed_by_date.get(date, 0) + 1

        for filename, info in self.uploaded["files"].items():
            date = info["timestamp"].split("T")[0]
            uploaded_by_date[date] = uploaded_by_date.get(date, 0) + 1

        return {
            "processed_count": processed_count,
            "uploaded_count": uploaded_count,
            "pending_upload": pending_upload,
            "processed_by_date": processed_by_date,
            "uploaded_by_date": uploaded_by_date,
            "last_updated": datetime.now().isoformat()
        }


# Global registry instance
_registry = None


def get_registry() -> FileRegistry:
    """
    Get the file registry instance.

    Returns:
        FileRegistry: File registry instance
    """
    global _registry
    if _registry is None:
        _registry = FileRegistry()
    return _registry


# For direct testing
if __name__ == "__main__":
    registry = get_registry()

    # Test basic functionality
    registry.mark_as_processed("test.jpg", {"size": 1024})
    registry.mark_as_uploaded("test.jpg", "https://example.com/test.jpg")

    print(f"Is test.jpg processed? {registry.is_processed('test.jpg')}")
    print(f"Is test.jpg uploaded? {registry.is_uploaded('test.jpg')}")

    # Print statistics
    stats = registry.get_processing_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2)}")

    # Clean up test file
    registry.remove_from_processed("test.jpg")
    registry.remove_from_uploaded("test.jpg")
