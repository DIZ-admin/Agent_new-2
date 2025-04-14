#!/usr/bin/env python3
"""
SharePoint Uploader

This module uploads processed photos and their metadata to the target SharePoint library.
After successful upload, files are moved from upload directory to uploaded directory and metadata files are deleted.
"""

import os
import shutil
from datetime import datetime
from src.sharepoint_auth import get_sharepoint_context, get_library

# Import utilities
from src.utils.paths import get_path_manager, load_json_file, standardize_path, move_file
from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.registry import get_registry

# Get logger
logger = get_logger('sharepoint_uploader')

# Get configuration
config = get_config()

# SharePoint settings
TARGET_LIBRARY_TITLE = config.sharepoint.target_library_title

# Get path manager for directories
path_manager = get_path_manager()
UPLOAD_DIR = path_manager.upload_dir
UPLOAD_METADATA_DIR = path_manager.upload_metadata_dir
UPLOADED_DIR = path_manager.uploaded_dir


def get_files_for_upload():
    """
    Get files ready for upload.

    Returns:
        list: List of file information dictionaries
    """
    try:
        upload_files = []

        # Get registry to check if files have already been uploaded
        registry = get_registry()

        # Check for files in upload directory
        for filename in os.listdir(UPLOAD_DIR):
            file_path = UPLOAD_DIR / filename
            if file_path.is_file():
                # Skip metadata files
                if filename.endswith('.json') or filename.endswith('.yml'):
                    continue

                # Check if file has already been uploaded
                if registry.is_uploaded(filename):
                    logger.info(f"Skipping already uploaded file: {filename}")
                    continue

                # Check if metadata exists
                base_name = os.path.splitext(filename)[0]
                metadata_path = UPLOAD_METADATA_DIR / f"{base_name}.json"
                original_metadata_path = UPLOAD_METADATA_DIR / f"{base_name}.yml"

                if metadata_path.exists():
                    # Load metadata
                    metadata = load_json_file(metadata_path)

                    # Check if original filename is different and has been uploaded
                    if 'OriginalName' in metadata and metadata['OriginalName']:
                        original_name = metadata['OriginalName']
                        if original_name != filename and registry.is_uploaded(original_name):
                            logger.info(f"Skipping already uploaded file (by original name): {filename} (original: {original_name})")
                            continue

                    # Check if original metadata exists
                    original_metadata_path_to_use = None
                    if original_metadata_path.exists():
                        original_metadata_path_to_use = original_metadata_path

                    # Add to upload files
                    upload_files.append({
                        'name': filename,
                        'path': file_path,
                        'metadata_path': metadata_path,
                        'metadata': metadata,
                        'original_metadata_path': original_metadata_path_to_use
                    })
                else:
                    logger.warning(f"Metadata not found for {filename}, skipping")

        logger.info(f"Found {len(upload_files)} files ready for upload")
        return upload_files
    except Exception as e:
        logger.error(f"Error getting files for upload: {str(e)}")
        raise


def upload_file_to_sharepoint(ctx, library, file_info):
    """
    Upload a file to SharePoint with metadata.

    Args:
        ctx (ClientContext): SharePoint client context
        library: SharePoint library object
        file_info (dict): File information dictionary

    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        filename = file_info['name']
        file_path = file_info['path']
        metadata = file_info['metadata']

        logger.info(f"Uploading file: {filename}")

        # Read file content
        with open(file_path, 'rb') as content_file:
            file_content = content_file.read()

        # Get target folder
        folder = library.root_folder
        ctx.load(folder)
        ctx.execute_query()

        # Upload file
        target_file = folder.upload_file(filename, file_content)
        ctx.execute_query()
        logger.info(f"File uploaded: {filename}")

        # Update metadata
        item = target_file.listItemAllFields

        # Set metadata fields
        for field_name, field_value in metadata.items():
            # Skip filename field as it's already set
            if field_name == 'FileLeafRef':
                continue

            # Handle multi-choice fields (arrays)
            if isinstance(field_value, list):
                # Convert array to SharePoint format
                # For multi-choice fields, SharePoint expects a dictionary with a 'results' key
                field_value = {'results': field_value}

            item.set_property(field_name, field_value)

        # Update item
        item.update()
        ctx.execute_query()
        logger.info(f"Metadata updated for: {filename}")

        # Move file to uploaded directory
        uploaded_path = UPLOADED_DIR / filename
        move_file(file_path, uploaded_path)
        logger.info(f"File moved to uploaded directory: {uploaded_path}")

        # Upload JSON metadata file to SharePoint
        metadata_filename = file_info['metadata_path'].name

        # Read file content
        with open(file_info['metadata_path'], 'rb') as content_file:
            metadata_content = content_file.read()

        # Upload file to the same folder
        folder = library.root_folder
        folder.upload_file(metadata_filename, metadata_content)
        ctx.execute_query()
        logger.info(f"JSON metadata file uploaded: {metadata_filename}")

        # Move JSON metadata file to uploaded directory (instead of copying)
        uploaded_metadata_path = UPLOADED_DIR / metadata_filename
        move_file(standardize_path(file_info['metadata_path']), uploaded_metadata_path)
        logger.info(f"JSON metadata file moved to uploaded directory: {uploaded_metadata_path}")

        # Upload and move original YAML metadata file if it exists
        if 'original_metadata_path' in file_info and file_info['original_metadata_path']:
            # Upload original metadata file to SharePoint
            original_metadata_filename = file_info['original_metadata_path'].name

            # Read file content
            with open(file_info['original_metadata_path'], 'rb') as content_file:
                file_content = content_file.read()

            # Upload file to the same folder
            folder = library.root_folder
            folder.upload_file(original_metadata_filename, file_content)
            ctx.execute_query()
            logger.info(f"Original metadata file uploaded: {original_metadata_filename}")

            # Move original metadata file to uploaded directory (instead of copying)
            uploaded_original_metadata_path = UPLOADED_DIR / original_metadata_filename
            move_file(standardize_path(file_info['original_metadata_path']), uploaded_original_metadata_path)
            logger.info(f"Original metadata file moved to uploaded directory: {uploaded_original_metadata_path}")

        # Update registry to mark file as uploaded
        registry = get_registry()

        # Get original filename from OriginalName field if available
        original_filename = filename
        if 'OriginalName' in metadata and metadata['OriginalName']:
            original_filename = metadata['OriginalName']

        # Mark both the original and target filenames as uploaded
        registry.mark_as_uploaded(filename, {
            'target_url': str(target_file.serverRelativeUrl),
            'uploaded_timestamp': datetime.now().isoformat(),
            'metadata_filename': metadata_filename,
            'original_metadata_filename': original_metadata_filename if 'original_metadata_path' in file_info and file_info['original_metadata_path'] else None,
            'original_filename': original_filename
        })

        # If original filename is different from target filename, mark it as uploaded too
        if original_filename != filename:
            registry.mark_as_uploaded(original_filename, {
                'target_url': str(target_file.serverRelativeUrl),
                'uploaded_timestamp': datetime.now().isoformat(),
                'target_filename': filename,
                'metadata_filename': metadata_filename,
                'original_metadata_filename': original_metadata_filename if 'original_metadata_path' in file_info and file_info['original_metadata_path'] else None
            })

            # Map the original filename to the target filename
            registry.map_filename(original_filename, filename)

        logger.info(f"Registry updated for {filename} and {original_filename}")

        return True
    except Exception as e:
        logger.error(f"Error uploading file {filename}: {str(e)}")
        return False


def upload_files_to_sharepoint(files, batch_size=10):
    """
    Upload multiple files to SharePoint.

    Args:
        files (list): List of file information dictionaries
        batch_size (int): Number of files to upload in each batch

    Returns:
        tuple: (successful_uploads, failed_uploads)
    """
    try:
        # Get SharePoint context
        ctx = get_sharepoint_context()

        # Get target library
        target_library = get_library(ctx, TARGET_LIBRARY_TITLE)
        if not target_library:
            logger.error(f"Target library not found: {TARGET_LIBRARY_TITLE}")
            return [], files

        successful_uploads = []
        failed_uploads = []

        # Process files in batches
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} files)")

            for file_info in batch:
                success = upload_file_to_sharepoint(ctx, target_library, file_info)

                if success:
                    successful_uploads.append(file_info)
                else:
                    failed_uploads.append(file_info)

        return successful_uploads, failed_uploads
    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}")
        return [], files


if __name__ == "__main__":
    try:
        # Get files for upload
        files = get_files_for_upload()

        if files:
            logger.info(f"Found {len(files)} files ready for upload")
            print(f"\nFound {len(files)} files ready for upload")

            # Upload files to SharePoint
            successful, failed = upload_files_to_sharepoint(files)

            logger.info(f"Upload results: {len(successful)} successful, {len(failed)} failed")
            print(f"\nUpload results:")
            print(f"- Successfully uploaded: {len(successful)} files")
            print(f"- Failed to upload: {len(failed)} files")

            if successful:
                print("\nSuccessfully uploaded files:")
                for file_info in successful:
                    print(f"- {file_info['name']}")

            if failed:
                print("\nFailed to upload files:")
                for file_info in failed:
                    print(f"- {file_info['name']}")

            print(f"\nUploaded files moved to: {UPLOADED_DIR}")
            print(f"Metadata files moved from {UPLOAD_METADATA_DIR} to {UPLOADED_DIR}")
        else:
            logger.warning("No files found for upload. Please run metadata_generator.py first.")
            print("No files found for upload. Please run metadata_generator.py first.")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        print(f"Error: {str(e)}")
