"""
File Manager Module

This module provides utilities for managing files in the web interface.
"""

import os
import glob
import json
import time
from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename
from src.utils.logging import get_logger
from src.web.utils import safe_path_join, log_with_context, Timer
from src.web.file_cache import get_file_cache
from src.web.exceptions import FileValidationError, PathSecurityError

# Get logger
logger = get_logger('web.file_manager')

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}


def allowed_file(filename):
    """
    Check if a file has an allowed extension.
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if file has an allowed extension
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class FileManager:
    """
    File Manager class for handling file operations with caching and optimization.
    """
    
    def __init__(self, path_manager):
        """
        Initialize the file manager.
        
        Args:
            path_manager: Path manager instance
        """
        self.path_manager = path_manager
        self.cache = get_file_cache()
        
    def get_files_in_directory(self, directory, page=1, per_page=12, filter_func=None, sort_by='modified', reverse=True):
        """
        Get files in a directory with pagination, filtering and sorting.
        
        Args:
            directory (str): Directory path
            page (int): Page number (1-based)
            per_page (int): Items per page
            filter_func (callable): Function to filter files
            sort_by (str): Field to sort by ('name', 'modified', 'size')
            reverse (bool): Sort in reverse order
            
        Returns:
            tuple: (files, pagination)
        """
        # Use a cache key including all parameters
        cache_key = f"dir_listing:{directory}:{page}:{per_page}:{sort_by}:{reverse}"
        if filter_func:
            cache_key += f":{filter_func.__name__}"
            
        # Try to get from cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for directory listing: {directory}")
            return cached_result
            
        with Timer() as timer:
            all_entries = []
            
            try:
                # Use scandir for better performance
                with os.scandir(directory) as entries:
                    for entry in entries:
                        # Skip directories if not explicitly needed
                        if not entry.is_file():
                            continue
                            
                        # Apply filter if provided
                        if filter_func and not filter_func(entry.name):
                            continue
                            
                        # Get file stats more efficiently
                        stat = entry.stat()
                        
                        all_entries.append({
                            'name': entry.name,
                            'path': entry.path,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime)
                        })
            except Exception as e:
                logger.error(f"Error listing directory {directory}: {str(e)}")
                return [], {'page': page, 'per_page': per_page, 'total': 0, 'total_pages': 0}
                
            # Sort entries
            if sort_by == 'name':
                all_entries.sort(key=lambda x: x['name'], reverse=reverse)
            elif sort_by == 'size':
                all_entries.sort(key=lambda x: x['size'], reverse=reverse)
            else:  # Default to modified date
                all_entries.sort(key=lambda x: x['modified'], reverse=reverse)
                
            # Calculate pagination
            total = len(all_entries)
            total_pages = (total + per_page - 1) // per_page
            
            # Adjust page if out of range
            if page < 1:
                page = 1
            elif page > total_pages and total_pages > 0:
                page = total_pages
                
            # Get page slice
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total)
            page_entries = all_entries[start_idx:end_idx]
            
            # Create pagination info
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'pages': list(range(max(1, page - 2), min(total_pages + 1, page + 3)))
            }
            
        # Log performance for large directories
        if total > 100:
            log_with_context(
                logger.debug,
                f"Listed large directory",
                {
                    'directory': directory,
                    'file_count': total,
                    'time_ms': int(timer.elapsed * 1000)
                }
            )
            
        # Cache the result
        result = (page_entries, pagination)
        self.cache.set(cache_key, result)
        
        return result
        
    def get_downloads(self, page=1, per_page=12):
        """
        Get downloaded files with pagination.
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (files, pagination)
        """
        return self.get_files_in_directory(
            self.path_manager.downloads_dir,
            page, 
            per_page,
            filter_func=allowed_file
        )
        
    def get_analyzed_files(self, page=1, per_page=12):
        """
        Get analyzed files with pagination.
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (files, pagination)
        """
        return self.get_files_in_directory(
            self.path_manager.analysis_dir,
            page,
            per_page,
            filter_func=lambda f: f.endswith('.json')
        )
        
    def get_uploadable_files(self, page=1, per_page=12):
        """
        Get files ready for upload with pagination.
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (files, pagination)
        """
        return self.get_files_in_directory(
            self.path_manager.upload_dir,
            page,
            per_page,
            filter_func=allowed_file
        )
        
    def get_uploaded_files(self, page=1, per_page=12):
        """
        Get uploaded files with pagination.
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (files, pagination)
        """
        return self.get_files_in_directory(
            self.path_manager.uploaded_dir,
            page,
            per_page,
            filter_func=allowed_file
        )
        
    def find_original_photo(self, photo_name):
        """
        Find the original photo in any of the photo directories.
        
        Args:
            photo_name (str): Base name of the photo without extension
            
        Returns:
            tuple: (original_path, original_filename) or (None, None)
        """
        # Try to get from cache first
        cache_key = f"original_photo:{photo_name}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
            
        # Look in each directory with different extensions
        directories = [
            self.path_manager.processed_dir,
            self.path_manager.downloads_dir,
            self.path_manager.uploaded_dir
        ]
        
        extensions = [''] + [f'.{ext}' for ext in ALLOWED_EXTENSIONS]
        
        for directory in directories:
            for ext in extensions:
                try:
                    test_path = safe_path_join(directory, photo_name + ext)
                    if os.path.exists(test_path):
                        result = (str(test_path), photo_name + ext)
                        # Cache the result
                        self.cache.set(cache_key, result)
                        return result
                except PathSecurityError:
                    continue
                    
        # Not found
        return (None, None)
        
    def get_metadata_for_file(self, filename, directory):
        """
        Get metadata for a file from a JSON sidecar file.
        
        Args:
            filename (str): Name of the file
            directory (str): Directory containing the metadata
            
        Returns:
            dict: Metadata or None if not found or error
        """
        try:
            # Create the metadata path
            base_name = os.path.splitext(filename)[0]
            metadata_path = safe_path_join(directory, base_name + '.json')
            
            # Check if metadata exists
            if not os.path.exists(metadata_path):
                return None
                
            # Cache key
            cache_key = f"metadata:{metadata_path}"
            
            # Try to get from cache
            cached_metadata = self.cache.get(cache_key)
            if cached_metadata:
                return cached_metadata
                
            # Read and parse JSON
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            # Cache the result
            self.cache.set(cache_key, metadata)
            
            return metadata
        except Exception as e:
            logger.error(f"Error loading metadata for {filename}: {str(e)}")
            return None
            
    def save_uploaded_file(self, file, validate=True):
        """
        Save an uploaded file to the downloads directory.
        
        Args:
            file: File object to save
            validate (bool): Whether to validate the file
            
        Returns:
            str: Path to the saved file
            
        Raises:
            FileValidationError: If validation fails
        """
        if not file or file.filename == '':
            raise FileValidationError("No file selected")
            
        if not allowed_file(file.filename):
            raise FileValidationError(f"Invalid file extension: {file.filename}")
            
        if validate:
            # Validate file content
            current_position = file.tell()
            is_valid = self._validate_image_content(file)
            file.seek(current_position)  # Reset file position
            
            if not is_valid:
                raise FileValidationError(f"File does not appear to be a valid image: {file.filename}")
                
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Create the destination path
        file_path = safe_path_join(self.path_manager.downloads_dir, filename)
        
        # Save the file
        file.save(file_path)
        
        logger.info(f"Saved uploaded file: {filename}")
        
        return str(file_path)
        
    def _validate_image_content(self, file):
        """
        Validate that a file is an image by checking its content.
        
        Args:
            file: File object to validate
            
        Returns:
            bool: True if valid image, False otherwise
        """
        try:
            # Save the current position
            current_position = file.tell()
            
            # Read enough bytes for validation
            header = file.read(32)
            file.seek(current_position)  # Reset file position
            
            # JPEG validation
            if header.startswith(b'\xFF\xD8\xFF'):
                return True
                
            # PNG validation
            if header.startswith(b'\x89PNG\r\n\x1a\n') and b'IHDR' in header[8:]:
                return True
                
            # GIF validation
            if (header.startswith(b'GIF87a') or header.startswith(b'GIF89a')):
                return True
                
            # BMP validation
            if header.startswith(b'BM') and len(header) >= 14:
                return True
                
            # TIFF validation
            if (header.startswith(b'II') and header[2:4] == b'\x2A\x00') or \
               (header.startswith(b'MM') and header[2:4] == b'\x00\x2A'):
                return True
                
            # WEBP validation
            if header.startswith(b'RIFF') and b'WEBP' in header:
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error validating image content: {str(e)}")
            return False
            
    def get_file_url(self, filepath, url_generator):
        """
        Get the URL for a file.
        
        Args:
            filepath (str): Path to the file
            url_generator (callable): Function to generate URL
            
        Returns:
            str: URL for the file or None
        """
        try:
            filename = os.path.basename(filepath)
            return url_generator(filename=filename)
        except Exception as e:
            logger.error(f"Error generating URL for {filepath}: {str(e)}")
            return None
