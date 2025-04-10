#!/usr/bin/env python3
"""
Connection Test Script

This script tests connections to SharePoint and OpenAI API to validate credentials.
"""

import sys
import os
import logging
from dotenv import load_dotenv
import openai

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_connection')

# Add src directory to system path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import modules
try:
    from src.sharepoint_auth import test_connection as test_sharepoint_connection
    logger.info("Successfully imported SharePoint auth module")
except ImportError as e:
    logger.error(f"Error importing SharePoint auth module: {e}")
    sys.exit(1)


def test_openai_connection():
    """Test connection to OpenAI API."""
    try:
        # Load environment variables
        load_dotenv('config/config.env')
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            logger.error("OpenAI API key not found in environment variables")
            return False

        # Configure the OpenAI API key
        openai.api_key = api_key
        
        # Make a simple request to the API
        logger.info("Testing connection to OpenAI API...")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working?"}
            ],
            max_tokens=10
        )
        
        if response and response.choices and len(response.choices) > 0:
            logger.info(f"Successfully connected to OpenAI API. Response: {response.choices[0].message.content}")
            return True
        else:
            logger.error("Invalid response from OpenAI API")
            return False
            
    except Exception as e:
        logger.error(f"Error connecting to OpenAI API: {e}")
        return False


def main():
    """Main function to test connections."""
    print("\n=== Connection Test Script ===\n")
    
    # Test SharePoint connection
    print("\n--- Testing SharePoint Connection ---")
    sharepoint_success = test_sharepoint_connection()
    if sharepoint_success:
        print("✅ SharePoint connection successful!")
    else:
        print("❌ SharePoint connection failed!")
    
    # Test OpenAI connection
    print("\n--- Testing OpenAI Connection ---")
    openai_success = test_openai_connection()
    if openai_success:
        print("✅ OpenAI connection successful!")
    else:
        print("❌ OpenAI connection failed!")
    
    # Print summary
    print("\n--- Test Summary ---")
    if sharepoint_success and openai_success:
        print("✅ All connections successful!")
        return 0
    else:
        print("❌ Some connections failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
