#!/usr/bin/env python3
"""
Photo Metadata Extractor

This module extracts metadata from photos and saves it to JSON files.
It also handles downloading photos from the source SharePoint library and deleting them after processing.
"""

import os
import yaml
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from src.sharepoint_auth import get_sharepoint_context, get_library

# Import utilities
import shutil
from src.utils.paths import get_path_manager
from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.registry import get_registry

# Get logger
logger = get_logger('photo_metadata')

# Get configuration
config = get_config()

# SharePoint settings
SOURCE_LIBRARY_TITLE = config.sharepoint.source_library_title
MAX_FILE_SIZE = config.file.max_file_size

# Get path manager for directories
path_manager = get_path_manager()
DOWNLOADS_DIR = path_manager.downloads_dir
METADATA_DIR = path_manager.metadata_dir


def get_photo_files(ctx, library):
    """
    Get all photo files from a SharePoint library.

    Args:
        ctx (ClientContext): SharePoint client context
        library: SharePoint library object

    Returns:
        list: List of file objects
    """
    try:
        logger.info(f"Retrieving files from library: {library.properties.get('Title')}")

        # Try a different approach - get all files directly
        library_title = library.properties.get('Title')
        library_url = f"/sites/100_Testing_KI-Projekte/{library_title}"
        logger.debug(f"Library URL: {library_url}")

        # Get the folder object for the library
        folder = ctx.web.get_folder_by_server_relative_url(library_url)
        ctx.load(folder)
        ctx.execute_query()
        logger.debug(f"Folder properties: {folder.properties}")

        # Get all files in the folder
        files = folder.files
        ctx.load(files)
        ctx.execute_query()
        logger.debug(f"Found {len(files)} files in library folder")

        # Filter for image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        photo_files = []

        # Process files directly
        for file in files:
            file_name = file.properties.get('Name', '')
            file_ext = os.path.splitext(file_name)[1].lower()
            logger.debug(f"Checking file: {file_name}, extension: {file_ext}")

            if file_ext in image_extensions:
                file_url = file.properties.get('ServerRelativeUrl', '')
                logger.debug(f"Found image file: {file_name}, URL: {file_url}")

                # Check file size
                file_size = file.properties.get('Length', 0)
                # Convert to int if it's a string
                if isinstance(file_size, str):
                    try:
                        file_size = int(file_size)
                    except ValueError:
                        file_size = 0

                logger.debug(f"File size: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)")

                if file_size <= MAX_FILE_SIZE:
                    photo_files.append({
                        'name': file_name,
                        'url': file_url,
                        'size': file_size,
                        'file_obj': file
                    })
                    logger.debug(f"Added file to processing list: {file_name}")
                else:
                    logger.warning(f"Skipping file {file_name} - exceeds maximum size of {MAX_FILE_SIZE} bytes)")

        logger.info(f"Found {len(photo_files)} photo files in library")
        return photo_files
    except Exception as e:
        logger.error(f"Error retrieving photo files: {str(e)}")
        raise


def download_photo(file_info):
    """
    Download a photo from SharePoint.

    Args:
        file_info (dict): File information dictionary

    Returns:
        str: Path to downloaded file
    """
    try:
        file_name = file_info['name']
        file_obj = file_info['file_obj']

        # Create local file path
        local_path = DOWNLOADS_DIR / file_name

        # Download file
        logger.info(f"Downloading file: {file_name}")
        with open(local_path, 'wb') as local_file:
            file_obj.download(local_file).execute_query()

        logger.info(f"File downloaded to: {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error downloading file {file_info['name']}: {str(e)}")
        raise


def extract_exif_metadata(image_path):
    """
    Extract EXIF metadata from an image.

    Args:
        image_path (str): Path to image file

    Returns:
        dict: Dictionary of EXIF metadata
    """
    try:
        metadata = {}

        # Open image
        with Image.open(image_path) as img:
            # Get EXIF data
            exif_data = img._getexif()

            if exif_data:
                # Extract EXIF tags
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)

                    # Convert bytes to string if needed
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = str(value)

                    # Convert datetime objects to string
                    if isinstance(value, datetime):
                        value = value.isoformat()

                    # Convert PIL.TiffImagePlugin.IFDRational to float or string
                    if str(type(value)).find('IFDRational') > 0:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = str(value)

                    # Convert tuples, lists, and other non-serializable types to strings
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        value = str(value)

                    metadata[tag] = value

            # Add basic image info
            metadata['ImageWidth'] = img.width
            metadata['ImageHeight'] = img.height
            metadata['ImageFormat'] = img.format
            metadata['ImageMode'] = img.mode

        return metadata
    except Exception as e:
        logger.error(f"Error extracting EXIF metadata from {image_path}: {str(e)}")
        return {}


def convert_to_degrees(value):
    """
    Convert GPS coordinates to degrees.

    Args:
        value: GPS coordinate value from EXIF

    Returns:
        float: Coordinate in degrees
    """
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (ValueError, TypeError, IndexError):
        return 0.0


def extract_formatted_exif(image_path):
    """
    Extract EXIF metadata from an image and format it in a human-readable way.

    Args:
        image_path (str): Path to image file

    Returns:
        str: Formatted EXIF metadata
    """
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()

        if not exif_data:
            return "No EXIF data available."

        formatted_exif = []

        # Process basic EXIF data
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)

            # Special handling for GPS information
            if tag == 'GPSInfo':
                gps_data = {}
                for gps_tag in value:
                    sub_tag = GPSTAGS.get(gps_tag, gps_tag)
                    gps_data[sub_tag] = value[gps_tag]

                # Convert coordinates to readable format
                if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                    lat = convert_to_degrees(gps_data['GPSLatitude'])
                    lon = convert_to_degrees(gps_data['GPSLongitude'])

                    if gps_data.get('GPSLatitudeRef') == 'S':
                        lat = -lat
                    if gps_data.get('GPSLongitudeRef') == 'W':
                        lon = -lon

                    formatted_exif.append(f"GPS Coordinates: {lat:.6f}, {lon:.6f}")

                    # Add individual GPS components
                    for sub_tag, sub_value in gps_data.items():
                        if isinstance(sub_value, bytes):
                            try:
                                sub_value = sub_value.decode('utf-8')
                            except UnicodeDecodeError:
                                sub_value = str(sub_value)
                        formatted_exif.append(f"GPS {sub_tag}: {sub_value}")
            else:
                # Format value for readability
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except UnicodeDecodeError:
                        value = str(value)

                # Convert datetime objects to string
                if isinstance(value, datetime):
                    value = value.isoformat()

                # Convert other complex types to string
                if not isinstance(value, (str, int, float, bool, type(None))):
                    value = str(value)

                formatted_exif.append(f"{tag}: {value}")

        # Add basic image info
        with Image.open(image_path) as img:
            formatted_exif.append(f"Image Width: {img.width}")
            formatted_exif.append(f"Image Height: {img.height}")
            formatted_exif.append(f"Image Format: {img.format}")
            formatted_exif.append(f"Image Mode: {img.mode}")

        return "\n".join(formatted_exif)
    except Exception as e:
        logger.error(f"Error formatting EXIF data from {image_path}: {str(e)}")
        return "Error extracting EXIF data."


def save_metadata_to_yaml(metadata, image_path):
    """
    Save metadata to a YAML file.

    Args:
        metadata (dict): Metadata dictionary
        image_path (str): Path to image file

    Returns:
        str: Path to YAML file
    """
    try:
        # Create YAML file path with same name as image but .yml extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        yaml_path = METADATA_DIR / f"{base_name}.yml"

        # Save metadata to YAML file
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Metadata saved to: {yaml_path}")
        return yaml_path
    except Exception as e:
        logger.error(f"Error saving metadata to YAML: {str(e)}")
        raise


def delete_sharepoint_file(file_obj):
    """
    Delete a file from SharePoint.

    Args:
        file_obj: SharePoint file object

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        file_name = file_obj.properties.get('Name', '')
        logger.info(f"Deleting file from SharePoint: {file_name}")

        # Delete the file
        file_obj.delete_object().execute_query()

        logger.info(f"Successfully deleted file from SharePoint: {file_name}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file from SharePoint: {str(e)}")
        return False


def process_photo_batch(photo_files, batch_size=10):
    """
    Process a batch of photos and delete them from SharePoint after successful processing.
    Skips photos that have already been processed based on their hash.
    Moves processed photos to the processed directory.

    Args:
        photo_files (list): List of photo file information dictionaries
        batch_size (int): Number of photos to process in each batch

    Returns:
        list: List of processed photo information dictionaries
    """
    processed_photos = []
    deleted_files = []
    skipped_files = []
    registry = get_registry()
    path_manager = get_path_manager()

    # Create processed directory if it doesn't exist
    processed_dir = path_manager.data_dir / "processed"
    processed_dir.mkdir(exist_ok=True)

    for i in range(0, len(photo_files), batch_size):
        batch = photo_files[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} photos)")

        for file_info in batch:
            try:
                # Download photo
                local_path = download_photo(file_info)

                # Calculate file hash
                file_hash = registry.calculate_file_hash(local_path)

                # Check if file has already been processed by hash
                if registry.is_file_processed_by_hash(local_path):
                    logger.info(f"Skipping already processed photo: {file_info['name']}")
                    skipped_files.append(file_info['name'])

                    # Delete file from SharePoint since we already have it
                    if delete_sharepoint_file(file_info['file_obj']):
                        deleted_files.append(file_info['name'])

                    # Remove the downloaded file to save space
                    try:
                        os.remove(local_path)
                        logger.debug(f"Removed duplicate file: {local_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove duplicate file {local_path}: {str(e)}")

                    continue

                # Extract metadata
                metadata = extract_exif_metadata(local_path)

                # Save metadata to YAML
                yaml_path = save_metadata_to_yaml(metadata, local_path)

                # Register file hash
                registry.register_file_hash(local_path, {
                    'name': file_info['name'],
                    'metadata_path': str(yaml_path),
                    'timestamp': datetime.now().isoformat(),
                    'hash': file_hash
                })

                # Add to processed photos
                processed_photos.append({
                    'name': file_info['name'],
                    'local_path': local_path,
                    'metadata_path': yaml_path,
                    'metadata': metadata,
                    'file_obj': file_info['file_obj'],
                    'hash': file_hash
                })

                # Mark as processed in registry
                registry.mark_as_processed(file_info['name'], {
                    'local_path': str(local_path),
                    'metadata_path': str(yaml_path),
                    'timestamp': datetime.now().isoformat(),
                    'hash': file_hash
                })

                # Delete file from SharePoint after successful processing
                if delete_sharepoint_file(file_info['file_obj']):
                    deleted_files.append(file_info['name'])

                # Move processed file to processed directory
                processed_file_path = processed_dir / os.path.basename(local_path)
                processed_yaml_path = processed_dir / os.path.basename(yaml_path)

                try:
                    # Move photo file
                    shutil.move(local_path, processed_file_path)
                    logger.debug(f"Moved processed file to: {processed_file_path}")

                    # Move YAML metadata file
                    shutil.move(yaml_path, processed_yaml_path)
                    logger.debug(f"Moved metadata file to: {processed_yaml_path}")

                    # Update paths in processed photos
                    for photo in processed_photos:
                        if photo['local_path'] == local_path:
                            photo['local_path'] = str(processed_file_path)
                            photo['metadata_path'] = str(processed_yaml_path)
                            break
                except Exception as e:
                    logger.warning(f"Failed to move processed files: {str(e)}")

                logger.info(f"Successfully processed photo: {file_info['name']}")
            except Exception as e:
                logger.error(f"Error processing photo {file_info['name']}: {str(e)}")

    logger.info(f"Processed {len(processed_photos)} photos, skipped {len(skipped_files)} already processed photos")
    logger.info(f"Deleted {len(deleted_files)} files from SharePoint")
    return processed_photos


if __name__ == "__main__":
    try:
        # Get SharePoint context
        ctx = get_sharepoint_context()

        # Get source library
        source_library = get_library(ctx, SOURCE_LIBRARY_TITLE)
        if not source_library:
            logger.error(f"Source library not found: {SOURCE_LIBRARY_TITLE}")
            exit(1)

        # Get photo files
        photo_files = get_photo_files(ctx, source_library)

        # Process photos in batches
        if photo_files:
            print(f"\nFound {len(photo_files)} photos in source library")
            print(f"Downloading and extracting metadata...")

            # Process all photos in batches
            batch_size = 10  # Process 10 photos at a time
            processed_photos = process_photo_batch(photo_files, batch_size)

            logger.info(f"Successfully processed {len(processed_photos)} photos")
            print(f"\nSuccessfully processed {len(processed_photos)} photos")
            logger.info(f"Photos downloaded to: {DOWNLOADS_DIR}")
            print(f"Photos downloaded to: {DOWNLOADS_DIR}")
            logger.info(f"Metadata saved to: {METADATA_DIR}")
            print(f"Metadata saved to: {METADATA_DIR}")
            logger.info(f"Files were deleted from source SharePoint library after processing")
            print(f"Files were deleted from source SharePoint library after processing")
        else:
            print("No photos found in source library")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        print(f"Error: {str(e)}")
