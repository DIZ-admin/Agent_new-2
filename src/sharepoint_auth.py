#!/usr/bin/env python3
"""
SharePoint Authentication Module

This module handles authentication to SharePoint and provides functions
for interacting with SharePoint libraries.
"""

from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext

# Import utilities
from src.utils.config import get_config
from src.utils.logging import get_logger

# Get logger
logger = get_logger('sharepoint_auth')

# Get configuration
config = get_config()

# SharePoint connection settings
SHAREPOINT_SITE_URL = config.sharepoint.site_url
SHAREPOINT_USERNAME = config.sharepoint.username
SHAREPOINT_PASSWORD = config.sharepoint.password
MAX_CONNECTION_ATTEMPTS = config.sharepoint.max_connection_attempts
CONNECTION_RETRY_DELAY = config.sharepoint.connection_retry_delay

# Library settings
SOURCE_LIBRARY_TITLE = config.sharepoint.source_library_title
TARGET_LIBRARY_TITLE = config.sharepoint.target_library_title


def get_sharepoint_context():
    """
    Create and return a SharePoint client context using credentials from environment variables.

    Returns:
        ClientContext: Authenticated SharePoint client context
    """
    try:
        logger.info(f"Authenticating to SharePoint site: {SHAREPOINT_SITE_URL}")
        credentials = UserCredential(SHAREPOINT_USERNAME, SHAREPOINT_PASSWORD)
        ctx = ClientContext(SHAREPOINT_SITE_URL).with_credentials(credentials)
        return ctx
    except Exception as e:
        logger.error(f"Failed to authenticate to SharePoint: {str(e)}")
        raise


def test_connection():
    """
    Test the connection to SharePoint by retrieving the web title.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        ctx = get_sharepoint_context()
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        logger.info(f"Successfully connected to SharePoint site: {web.properties['Title']}")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False


def get_library(ctx, library_title):
    """
    Get a SharePoint document library by title.

    Args:
        ctx (ClientContext): SharePoint client context
        library_title (str): Title of the document library

    Returns:
        List: SharePoint list object representing the document library
    """
    try:
        logger.info(f"Retrieving library: {library_title}")
        lists = ctx.web.lists
        ctx.load(lists)
        ctx.execute_query()

        for lst in lists:
            if lst.properties.get('Title') == library_title:
                logger.info(f"Found library: {library_title}")
                return lst

        logger.error(f"Library not found: {library_title}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving library {library_title}: {str(e)}")
        raise


if __name__ == "__main__":
    # Test the connection when run directly
    success = test_connection()
    if success:
        print("Connection to SharePoint successful!")

        # Get the source and target libraries
        ctx = get_sharepoint_context()
        source_library = get_library(ctx, SOURCE_LIBRARY_TITLE)
        target_library = get_library(ctx, TARGET_LIBRARY_TITLE)

        if source_library:
            print(f"Source library found: {SOURCE_LIBRARY_TITLE}")
        else:
            print(f"Source library not found: {SOURCE_LIBRARY_TITLE}")

        if target_library:
            print(f"Target library found: {TARGET_LIBRARY_TITLE}")
        else:
            print(f"Target library not found: {TARGET_LIBRARY_TITLE}")
    else:
        print("Connection to SharePoint failed!")
