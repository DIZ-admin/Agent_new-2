"""
Web Server Module

This module provides a web server for the ERNI Photo Processor.
"""

import os
from src.web import create_app
from src.utils.logging import get_logger

# Get logger
logger = get_logger('web_server')

def main():
    """
    Main function for web server.
    """
    try:
        # Create Flask app
        app = create_app()
        
        # Get host and port from environment variables or use defaults
        host = os.environ.get('WEB_HOST', '0.0.0.0')
        port = int(os.environ.get('WEB_PORT', 5000))
        
        # Run app
        logger.info(f"Starting web server on {host}:{port}")
        app.run(host=host, port=port, debug=True)
    except Exception as e:
        logger.error(f"Error starting web server: {str(e)}")
        raise

if __name__ == "__main__":
    main()
