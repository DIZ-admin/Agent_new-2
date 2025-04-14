#!/usr/bin/env python3
"""
Metadata Generator

This module generates metadata files for SharePoint upload according to the target library schema,
combining EXIF metadata and OpenAI analysis results.
"""

import os
import re
import shutil
import yaml
import requests

# Import utilities
from src.utils.paths import get_path_manager, load_json_file, save_json_file, standardize_path, copy_file
from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.registry import get_registry

# Get logger
logger = get_logger('metadata_generator')

# Get configuration
config = get_config()

# File settings
METADATA_SCHEMA_FILE = config.file.metadata_schema_file
TARGET_FILENAME_MASK = config.file.target_filename_mask

# Get path manager for directories
path_manager = get_path_manager()
DOWNLOADS_DIR = path_manager.downloads_dir
METADATA_DIR = path_manager.metadata_dir
ANALYSIS_DIR = path_manager.analysis_dir
UPLOAD_DIR = path_manager.upload_dir
UPLOADED_DIR = path_manager.uploaded_dir
UPLOAD_METADATA_DIR = path_manager.upload_metadata_dir
PROCESSED_DIR = path_manager.data_dir / "processed"


def load_metadata_schema():
    """
    Load metadata schema from JSON file.

    Returns:
        dict: Metadata schema dictionary
    """
    try:
        schema = load_json_file(METADATA_SCHEMA_FILE)
        logger.info(f"Loaded metadata schema from {METADATA_SCHEMA_FILE}")
        return schema
    except Exception as e:
        logger.error(f"Error loading metadata schema: {str(e)}")
        raise


def get_next_file_number():
    """
    Get the next file number for the target filename mask.
    Checks both upload and uploaded directories to ensure continuity.

    Returns:
        int: Next file number
    """
    try:
        # Check existing files in upload and uploaded directories
        all_files = []

        # Check upload directory
        if os.path.exists(UPLOAD_DIR):
            all_files.extend([os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)])

        # Check uploaded directory
        if os.path.exists(UPLOADED_DIR):
            all_files.extend([os.path.join(UPLOADED_DIR, f) for f in os.listdir(UPLOADED_DIR)])

        # Extract numbers from existing filenames
        pattern = re.compile(r'Erni_Referenzfoto_(\d{4})\.')
        numbers = []

        for filepath in all_files:
            filename = os.path.basename(filepath)
            match = pattern.search(filename)
            if match:
                numbers.append(int(match.group(1)))

        # Get next number
        next_number = 1
        if numbers:
            next_number = max(numbers) + 1

        logger.info(f"Next file number: {next_number}")
        return next_number
    except Exception as e:
        logger.error(f"Error getting next file number: {str(e)}")
        return 1


def generate_target_filename(original_filename, number):
    """
    Generate target filename according to the mask.

    Args:
        original_filename (str): Original filename
        number (int): File number

    Returns:
        str: Target filename
    """
    try:
        # Get file extension
        _, ext = os.path.splitext(original_filename)

        # Generate filename
        filename = TARGET_FILENAME_MASK.format(number=f"{number:04d}") + ext

        logger.info(f"Generated target filename: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error generating target filename: {str(e)}")
        raise


def geocode_coordinates(lat, lon):
    """
    Convert GPS coordinates to a location name using a geocoding service.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        str: Location name or None if geocoding failed
    """
    try:
        # Use Nominatim API (OpenStreetMap) for geocoding
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {
            "User-Agent": "ERNI-PhotoMetadata/1.0",  # Required by Nominatim API
            "Accept-Language": "de"  # Get results in German
        }

        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()

            # Extract location information
            if 'address' in data:
                address = data['address']

                # Try to get city or town or village
                location = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet')

                # If no city/town found, try county or state
                if not location:
                    location = address.get('county') or address.get('state')

                if location:
                    return location

        # If geocoding failed or no suitable location found
        return None
    except Exception as e:
        logger.error(f"Error geocoding coordinates {lat}, {lon}: {str(e)}")
        return None


def validate_metadata_field(field_name, field_value, field_schema):
    """
    Validate metadata field value against schema.

    Args:
        field_name (str): Field name
        field_value: Field value
        field_schema (dict): Field schema

    Returns:
        tuple: (is_valid, validated_value)
    """
    try:
        field_type = field_schema.get('type')

        # Handle different field types
        if field_type == 'Text' or field_type == 'Note':
            # Ensure value is string
            if field_value is None:
                return True, ""
            return True, str(field_value)

        elif field_type == 'Choice':
            # Check if value is in choices
            choices = field_schema.get('choices', [])
            if field_value in choices:
                return True, field_value
            elif isinstance(field_value, str) and field_value:
                # Try to find closest match
                for choice in choices:
                    if field_value.lower() in choice.lower() or choice.lower() in field_value.lower():
                        logger.info(f"Mapped '{field_value}' to choice '{choice}' for field {field_name}")
                        return True, choice
            return False, None

        elif field_type == 'MultiChoice':
            # Handle both string and list inputs
            choices = field_schema.get('choices', [])
            if isinstance(field_value, str):
                field_value = [field_value]

            if not isinstance(field_value, list):
                return False, None

            # Validate each value
            valid_values = []
            for value in field_value:
                if value in choices:
                    valid_values.append(value)
                else:
                    # Try to find closest match
                    for choice in choices:
                        if value.lower() in choice.lower() or choice.lower() in value.lower():
                            logger.info(f"Mapped '{value}' to choice '{choice}' for field {field_name}")
                            valid_values.append(choice)
                            break

            return True, valid_values

        elif field_type == 'DateTime':
            # Pass through as is
            return True, field_value

        elif field_type == 'User':
            # Pass through as is
            return True, field_value

        else:
            # For other types, pass through as is
            return True, field_value

    except Exception as e:
        logger.error(f"Error validating field {field_name}: {str(e)}")
        return False, None


def generate_metadata_for_upload(photo_info, schema, target_filename):
    """
    Generate metadata for SharePoint upload with intelligent data integration.

    Args:
        photo_info (dict): Photo information dictionary
        schema (dict): Metadata schema dictionary
        target_filename (str): Target filename

    Returns:
        dict: Metadata dictionary for upload
    """
    try:
        # Get analysis results and original EXIF metadata
        analysis = photo_info.get('analysis', {})
        exif_metadata = photo_info.get('metadata', {})

        # Create metadata dictionary
        metadata = {}

        # Add filename
        metadata['FileLeafRef'] = target_filename

        # Create a mapping from title to internal_name
        title_to_internal_name = {}
        for field in schema.get('fields', []):
            title_to_internal_name[field.get('title')] = field.get('internal_name')

        # Define priorities for data sources for different fields
        # This mapping determines which data source has priority for each field
        field_priorities = {
            # Date and time fields - EXIF data is more reliable
            'DateTime': ['exif', 'analysis'],
            'Datum': ['exif', 'analysis'],
            'Aufnahmedatum': ['exif', 'analysis'],

            # Location fields - GPS data has priority, then analysis
            'OrtohnePLZ': ['exif_gps', 'analysis'],
            'Ort': ['exif_gps', 'analysis'],
            'Standort': ['exif_gps', 'analysis'],
            'Location': ['exif_gps', 'analysis'],

            # Description fields - AI analysis is usually better
            'Titel': ['analysis', 'exif'],
            'Beschreibung': ['analysis', 'exif'],
            'Beschreibung_kurz': ['analysis', 'exif'],
            'Beschreibung_lang': ['analysis', 'exif'],
            'Title': ['analysis', 'exif'],
            'Description': ['analysis', 'exif'],

            # Technical fields - EXIF data is more reliable
            'Kamera': ['exif', 'analysis'],
            'Objektiv': ['exif', 'analysis'],
            'Camera': ['exif', 'analysis'],
            'Lens': ['exif', 'analysis'],
            'ISO': ['exif', 'analysis'],
            'Aperture': ['exif', 'analysis'],
            'ShutterSpeed': ['exif', 'analysis'],
            'FocalLength': ['exif', 'analysis'],

            # Copyright fields - EXIF data is more reliable
            'Copyright': ['exif', 'analysis'],
            'Author': ['exif', 'analysis'],
            'Autor': ['exif', 'analysis'],
            'Fotograf': ['exif', 'analysis'],
            'Photographer': ['exif', 'analysis'],

            # Material and construction fields - AI analysis is better
            'Material': ['analysis'],
            'Konstruktion': ['analysis'],
            'Holzart': ['analysis'],
            'Bauweise': ['analysis'],
            'Construction': ['analysis'],
            'WoodType': ['analysis'],
            'BuildingType': ['analysis']
        }

        # Define mapping between EXIF tags and SharePoint fields
        # This mapping connects SharePoint field titles to EXIF tag names
        exif_to_sharepoint = {
            # Date and time fields
            'DateTime': 'DateTimeOriginal',
            'Datum': 'DateTimeOriginal',
            'Aufnahmedatum': 'DateTimeOriginal',

            # Author and copyright fields
            'Artist': 'Artist',
            'Author': 'Artist',
            'Autor': 'Artist',
            'Fotograf': 'Artist',
            'Photographer': 'Artist',

            'Copyright': 'Copyright',

            # Description fields
            'Titel': 'ImageDescription',
            'Title': 'ImageDescription',
            'Beschreibung': 'ImageDescription',
            'Beschreibung_kurz': 'ImageDescription',
            'Description': 'ImageDescription',

            # Camera fields
            'Kamera': 'Make',
            'Camera': 'Make',
            'Objektiv': 'LensModel',
            'Lens': 'LensModel',
            'ISO': 'ISOSpeedRatings',
            'Aperture': 'FNumber',
            'ShutterSpeed': 'ExposureTime',
            'FocalLength': 'FocalLength'
        }

        # Process each field in schema
        for field in schema.get('fields', []):
            internal_name = field.get('internal_name')
            title = field.get('title')

            # Skip system fields and fields that are set automatically
            if internal_name in ['ID', 'Created', 'Modified', 'Author', 'Editor',
                               'ContentType', 'Vorschau', 'DocIcon', 'ComplianceAssetId', 'OriginalName']:
                continue

            # Determine value based on priorities
            value = None

            # If field has defined priorities
            if title in field_priorities:
                priorities = field_priorities[title]

                for source in priorities:
                    if source == 'analysis' and title in analysis:
                        value = analysis[title]
                        logger.debug(f"Using analysis data for field {title}: {value}")
                        break
                    elif source == 'exif':
                        exif_field = exif_to_sharepoint.get(title)
                        if exif_field and exif_field in exif_metadata:
                            value = exif_metadata[exif_field]
                            logger.debug(f"Using EXIF data for field {title}: {value}")
                            break
                    elif source == 'exif_gps' and 'GPSInfo' in exif_metadata:
                        # Special handling for GPS coordinates
                        if title == 'OrtohnePLZ' and 'GPS Coordinates' in exif_metadata:
                            # Extract coordinates from formatted GPS string
                            gps_str = exif_metadata.get('GPS Coordinates', '')
                            if gps_str:
                                # Parse coordinates from string
                                try:
                                    # Format is typically "GPS Coordinates: 47.123456, 8.123456"
                                    coords = gps_str.split(': ')[1].split(', ')
                                    lat = float(coords[0])
                                    lon = float(coords[1])

                                    # Try to geocode coordinates
                                    location = geocode_coordinates(lat, lon)
                                    if location:
                                        value = location
                                        logger.info(f"Geocoded coordinates to location: {location}")
                                    else:
                                        # Fallback to raw coordinates if geocoding fails
                                        value = f"GPS: {gps_str}"
                                except (IndexError, ValueError) as e:
                                    logger.warning(f"Error parsing GPS coordinates: {str(e)}")
                                    value = f"GPS: {gps_str}"

                                logger.debug(f"Using GPS data for field {title}: {value}")
                                break
            else:
                # For fields without explicit priorities, try both sources
                # First check if there's a matching EXIF field
                exif_field = exif_to_sharepoint.get(title)
                if exif_field and exif_field in exif_metadata:
                    value = exif_metadata[exif_field]
                    logger.debug(f"Using EXIF data for field without priority {title}: {value}")
                # Then check if there's a matching analysis field
                elif title in analysis:
                    value = analysis[title]
                    logger.debug(f"Using analysis data for field without priority {title}: {value}")

            # Validate and add value if available
            if value is not None:
                is_valid, validated_value = validate_metadata_field(internal_name, value, field)

                if is_valid and validated_value is not None:
                    # Use internal_name as key for SharePoint
                    metadata[internal_name] = validated_value

        # Set Status field to "Entwurf KI" if not already set
        if 'Status' not in metadata:
            metadata['Status'] = "Entwurf KI"

        # Add original filename to OriginalName field for tracking
        original_filename = photo_info.get('name', '')
        metadata['OriginalName'] = original_filename

        logger.info(f"Generated metadata for {target_filename} with intelligent data integration")
        return metadata
    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}")
        raise


def save_metadata_for_upload(metadata, target_filename):
    """
    Save metadata for SharePoint upload.

    Args:
        metadata (dict): Metadata dictionary
        target_filename (str): Target filename

    Returns:
        str: Path to metadata file
    """
    try:
        # Create metadata filename
        base_name = os.path.splitext(target_filename)[0]
        metadata_filename = f"{base_name}.json"
        metadata_path = UPLOAD_METADATA_DIR / metadata_filename

        # Save metadata to JSON file
        save_json_file(metadata, metadata_path)

        logger.info(f"Saved metadata for upload: {metadata_path}")
        return metadata_path
    except Exception as e:
        logger.error(f"Error saving metadata for upload: {str(e)}")
        raise


def prepare_photo_for_upload(photo_info, schema, file_number):
    """
    Prepare a photo for upload to SharePoint.

    Args:
        photo_info (dict): Photo information dictionary
        schema (dict): Metadata schema dictionary
        file_number (int): File number

    Returns:
        dict: Upload information dictionary
    """
    try:
        # Generate target filename
        target_filename = generate_target_filename(photo_info['name'], file_number)

        # Generate metadata
        metadata = generate_metadata_for_upload(photo_info, schema, target_filename)

        # Save metadata for upload (JSON format for SharePoint)
        metadata_path = save_metadata_for_upload(metadata, target_filename)

        # Copy original metadata file (YAML format) to upload directory if it exists
        # Use the same base name as the target filename for consistency
        original_metadata_path = None
        if photo_info.get('metadata_path'):
            base_name = os.path.splitext(target_filename)[0]
            original_metadata_target_path = UPLOAD_METADATA_DIR / f"{base_name}.yml"
            copy_file(standardize_path(photo_info['metadata_path']), original_metadata_target_path)
            original_metadata_path = original_metadata_target_path
            logger.info(f"Copied original metadata to upload directory: {original_metadata_target_path}")

        # Copy photo to upload directory
        target_path = UPLOAD_DIR / target_filename
        copy_file(standardize_path(photo_info['local_path']), target_path)

        logger.info(f"Copied photo to upload directory: {target_path}")

        # Return upload information
        return {
            'original_name': photo_info['name'],
            'target_name': target_filename,
            'target_path': target_path,
            'metadata_path': metadata_path,  # JSON metadata for SharePoint
            'metadata': metadata,
            'original_metadata_path': original_metadata_path  # YAML metadata (original)
        }
    except Exception as e:
        logger.error(f"Error preparing photo for upload: {str(e)}")
        raise


def find_processed_photos():
    """
    Find photos that have been processed with OpenAI and not yet uploaded to SharePoint.

    Returns:
        list: List of processed photo information dictionaries
    """
    try:
        processed_photos = []
        registry = get_registry()

        # Check for analysis files
        for filename in os.listdir(ANALYSIS_DIR):
            if filename.endswith('_analysis.json'):
                # Extract original filename
                original_name = filename.replace('_analysis.json', '')

                # Check if the file has already been uploaded to SharePoint
                # Check both by original name and by mapped filename (if it exists)
                if registry.is_uploaded(original_name):
                    logger.info(f"Skipping already uploaded photo: {original_name}")
                    continue

                # Check if the file has been mapped to a target filename and that target has been uploaded
                mapped_filename = registry.get_mapped_filename(original_name)
                if mapped_filename and registry.is_uploaded(mapped_filename):
                    logger.info(f"Skipping already uploaded photo: {original_name} (mapped to {mapped_filename})")
                    continue

                # Find corresponding photo and metadata
                photo_path = None
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                    # Check in downloads directory
                    test_path = DOWNLOADS_DIR / (original_name + ext)
                    if test_path.exists():
                        photo_path = test_path
                        break

                    # Check in processed directory
                    test_path = PROCESSED_DIR / (original_name + ext)
                    if test_path.exists():
                        photo_path = test_path
                        break

                if photo_path:
                    # Check if the file has already been processed by hash
                    if registry.is_file_processed_by_hash(photo_path):
                        # Get file info by hash
                        file_info = registry.get_file_info_by_hash(photo_path)
                        if file_info and 'filename' in file_info:
                            original_hash_filename = file_info['filename']
                            # Check if the file with this hash has been uploaded
                            if registry.is_uploaded(original_hash_filename):
                                logger.info(f"Skipping already uploaded photo with same hash: {original_name} (hash matches {original_hash_filename})")
                                continue
                    # Load analysis
                    analysis_path = ANALYSIS_DIR / filename
                    analysis = load_json_file(analysis_path)

                    # Load metadata if available (check for YAML file first, then JSON as fallback)
                    # Check in metadata directory
                    yaml_path = METADATA_DIR / (original_name + '.yml')
                    json_path = METADATA_DIR / (original_name + '.json')
                    # Check in processed directory
                    processed_yaml_path = PROCESSED_DIR / (original_name + '.yml')
                    processed_json_path = PROCESSED_DIR / (original_name + '.json')

                    metadata = {}
                    original_metadata_path = None

                    # Check in metadata directory first
                    if yaml_path.exists():
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            metadata = yaml.safe_load(f)
                        original_metadata_path = yaml_path
                    elif json_path.exists():
                        metadata = load_json_file(json_path)
                        original_metadata_path = json_path
                    # Then check in processed directory
                    elif processed_yaml_path.exists():
                        with open(processed_yaml_path, 'r', encoding='utf-8') as f:
                            metadata = yaml.safe_load(f)
                        original_metadata_path = processed_yaml_path
                    elif processed_json_path.exists():
                        metadata = load_json_file(processed_json_path)
                        original_metadata_path = processed_json_path

                    # Add to processed photos
                    processed_photos.append({
                        'name': os.path.basename(photo_path),
                        'local_path': photo_path,
                        'metadata_path': original_metadata_path,  # Use the path to the original metadata file
                        'metadata': metadata,
                        'analysis_path': analysis_path,
                        'analysis': analysis
                    })

        logger.info(f"Found {len(processed_photos)} processed photos")
        return processed_photos
    except Exception as e:
        logger.error(f"Error finding processed photos: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        # Load metadata schema
        schema = load_metadata_schema()

        # Find processed photos
        processed_photos = find_processed_photos()

        if processed_photos:
            print(f"\nFound {len(processed_photos)} processed photos")

            # Get next file number
            next_number = get_next_file_number()

            # Prepare photos for upload
            upload_info = []
            for i, photo_info in enumerate(processed_photos):
                file_number = next_number + i
                info = prepare_photo_for_upload(photo_info, schema, file_number)
                upload_info.append(info)

            logger.info(f"Prepared {len(upload_info)} photos for upload")
            print(f"\nPrepared {len(upload_info)} photos for upload:")
            for info in upload_info:
                logger.info(f"Prepared {info['original_name']} -> {info['target_name']}")
                print(f"- {info['original_name']} -> {info['target_name']}")

            logger.info(f"Photos and metadata saved to: {UPLOAD_DIR} and {UPLOAD_METADATA_DIR}")
            print(f"\nPhotos and metadata saved to:")
            print(f"- Photos: {UPLOAD_DIR}")
            print(f"- Metadata: {UPLOAD_METADATA_DIR}")
        else:
            print("No processed photos found. Please run photo_metadata.py and openai_analyzer.py first.")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        print(f"Error: {str(e)}")
