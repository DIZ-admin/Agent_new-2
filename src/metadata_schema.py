#!/usr/bin/env python3
"""
SharePoint Metadata Schema Analyzer

This module extracts the metadata schema from a SharePoint library
and saves it to a JSON file for later use.
"""

import json
from src.sharepoint_auth import get_sharepoint_context, get_library

# Import utilities
from src.utils.paths import get_path_manager, save_json_file
from src.utils.config import get_config
from src.utils.logging import get_logger

# Get logger
logger = get_logger('metadata_schema')

# Get configuration
config = get_config()

# Library settings
TARGET_LIBRARY_TITLE = config.sharepoint.target_library_title

# Get path manager for directories
path_manager = get_path_manager()
METADATA_SCHEMA_FILE = path_manager.config_dir / 'sharepoint_choices.json'


def get_field_schema(ctx, list_obj):
    """
    Get the field schema for a SharePoint list.

    Args:
        ctx (ClientContext): SharePoint client context
        list_obj (List): SharePoint list object

    Returns:
        list: List of field schema dictionaries
    """
    try:
        logger.info(f"Retrieving field schema for library: {list_obj.properties.get('Title')}")
        fields = list_obj.fields
        ctx.load(fields)
        ctx.execute_query()

        field_schema = []
        for field in fields:
            # Skip system fields and computed fields
            if (field.properties.get('Hidden') or
                field.properties.get('InternalName').startswith('_') or
                field.properties.get('TypeAsString') in ['Computed', 'Counter', 'Lookup', 'User', 'Thumbnail'] or
                field.properties.get('InternalName') in ['FileLeafRef', 'ComplianceAssetId', 'Modified', 'Editor',
                                                        'DocIcon', 'MediaServiceLocation', 'MediaServiceImageTags',
                                                        'ID', 'ContentType', 'Created', 'Author', 'CheckoutUser',
                                                        'LinkFilenameNoMenu', 'LinkFilename', 'FileSizeDisplay',
                                                        'ItemChildCount', 'FolderChildCount', 'AppAuthor', 'AppEditor',
                                                        'Edit', 'ParentVersionString', 'ParentLeafName']):
                continue

            # Extract field properties safely
            internal_name = field.properties.get('InternalName', '')
            title = field.properties.get('Title', '')
            field_type = field.properties.get('TypeAsString', '')
            required = field.properties.get('Required', False)
            description = field.properties.get('Description', '')

            # Skip fields with specific prefixes that are likely system fields
            if internal_name.startswith('_') or internal_name.startswith('ows_'):
                continue

            field_info = {
                'internal_name': internal_name,
                'title': title,
                'type': field_type,
                'required': required,
                'description': description
            }

            # Get choice values for choice fields
            if field_type in ['Choice', 'MultiChoice']:
                # Handle choices differently based on the API response structure
                choices = []
                choices_obj = field.properties.get('Choices')

                if choices_obj:
                    # Try different ways to extract choices based on the object type
                    if hasattr(choices_obj, 'get') and choices_obj.get('results'):
                        choices = choices_obj.get('results', [])
                    elif hasattr(choices_obj, '__iter__'):
                        choices = list(choices_obj)

                field_info['choices'] = choices

            field_schema.append(field_info)
            logger.debug(f"Added field to schema: {internal_name} ({field_type})")

        return field_schema
    except Exception as e:
        logger.error(f"Error retrieving field schema: {str(e)}")
        raise


def get_choice_fields(field_schema):
    """
    Extract choice fields from the field schema.

    Args:
        field_schema (list): List of field schema dictionaries

    Returns:
        dict: Dictionary of choice fields with their choices
    """
    choice_fields = {}
    for field in field_schema:
        if field.get('type') in ['Choice', 'MultiChoice'] and 'choices' in field:
            choice_fields[field['internal_name']] = {
                'title': field['title'],
                'type': field['type'],
                'choices': field.get('choices', [])
            }
    return choice_fields


def save_schema_to_json(schema, filename):
    """
    Save the schema to a JSON file.

    Args:
        schema (dict): Schema dictionary
        filename (str): Output filename
    """
    try:
        save_json_file(schema, filename)
        logger.info(f"Schema saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving schema to {filename}: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        # Get the SharePoint context
        ctx = get_sharepoint_context()

        # Get the target library
        target_library = get_library(ctx, TARGET_LIBRARY_TITLE)
        if not target_library:
            logger.error(f"Target library not found: {TARGET_LIBRARY_TITLE}")
            exit(1)

        # Get the field schema
        field_schema = get_field_schema(ctx, target_library)

        # Print field schema summary
        print(f"\nFound {len(field_schema)} metadata fields in target library:")
        for field in field_schema:
            field_type = field.get('type')
            required = "Required" if field.get('required') else "Optional"
            print(f"- {field.get('title')} ({field.get('internal_name')}): {field_type} [{required}]")
            if field_type in ['Choice', 'MultiChoice'] and 'choices' in field:
                choices_str = ', '.join(field.get('choices', []))
                print(f"  Choices: {choices_str}")

        # Extract choice fields
        choice_fields = get_choice_fields(field_schema)

        # Create schema dictionary
        schema = {
            'library_title': TARGET_LIBRARY_TITLE,
            'fields': field_schema,
            'choice_fields': choice_fields
        }

        # Save schema to JSON file
        save_schema_to_json(schema, METADATA_SCHEMA_FILE)
        print(f"\nMetadata schema saved to {METADATA_SCHEMA_FILE}")

    except Exception as e:
        logger.error(f"Error analyzing metadata schema: {str(e)}")
        print(f"Error: {str(e)}")
