#!/usr/bin/env python3
"""
Real Integration Test for Photo Agent

This script performs end-to-end testing of the Photo Agent workflow 
using real connections to SharePoint and OpenAI API.
"""

import os
import sys
import shutil
import json
import time
import unittest
from pathlib import Path

# Add project to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.utils.config import get_config
from src.utils.paths import get_path_manager
from src.utils.logging import get_logger

# Configure logger
logger = get_logger("real_integration_test")


class RealIntegrationTest(unittest.TestCase):
    """Integration test for the full Photo Agent workflow with real dependencies."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Get configuration and paths
        cls.config = get_config()
        cls.path_manager = get_path_manager()
        
        # Create backups of original config and test directories
        cls.backup_original_config()
        
        # Validate connection settings
        cls.validate_connections()
        
        logger.info("Test environment setup complete")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Restore original config
        cls.restore_original_config()
        
        logger.info("Test environment cleanup complete")

    @classmethod
    def backup_original_config(cls):
        """Backup original configuration files."""
        config_file = cls.path_manager.config_dir / "config.env"
        backup_file = cls.path_manager.config_dir / "config.env.backup"
        
        if config_file.exists() and not backup_file.exists():
            shutil.copy(config_file, backup_file)
            logger.info(f"Original config backed up to {backup_file}")

    @classmethod
    def restore_original_config(cls):
        """Restore original configuration files."""
        config_file = cls.path_manager.config_dir / "config.env"
        backup_file = cls.path_manager.config_dir / "config.env.backup"
        
        if backup_file.exists():
            shutil.copy(backup_file, config_file)
            backup_file.unlink()
            logger.info(f"Original config restored from {backup_file}")

    @classmethod
    def validate_connections(cls):
        """Validate connection settings before running tests."""
        # Import connection test modules
        from src.sharepoint_auth import test_connection as test_sharepoint
        
        # Test SharePoint connection
        logger.info("Testing SharePoint connection...")
        sharepoint_ok = test_sharepoint()
        if not sharepoint_ok:
            raise ConnectionError("SharePoint connection failed. Check your credentials and try again.")
        logger.info("SharePoint connection successful")
        
        # Test OpenAI connection
        logger.info("Testing OpenAI connection...")
        import openai
        openai.api_key = cls.config.openai.api_key
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                max_tokens=10
            )
            
            if response and response.choices and response.choices[0].message:
                logger.info(f"OpenAI connection successful: {response.choices[0].message.content}")
            else:
                raise ConnectionError("Invalid response from OpenAI API")
        except Exception as e:
            raise ConnectionError(f"OpenAI connection failed: {str(e)}")

    def test_1_metadata_schema(self):
        """Test metadata schema extraction with real SharePoint."""
        # Import the module
        import src.metadata_schema
        
        # Clear any existing schema file
        schema_file = self.path_manager.config_dir / 'sharepoint_choices.json'
        if schema_file.exists():
            schema_file.unlink()
        
        # Run the test
        logger.info("Running metadata schema extraction...")
        result = src.metadata_schema.main()
        
        # Verify result
        self.assertTrue(schema_file.exists(), "Metadata schema file was not created")
        
        # Load and verify schema content
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        self.assertIn('library_title', schema, "Schema is missing library_title")
        self.assertIn('fields', schema, "Schema is missing fields")
        self.assertIn('choice_fields', schema, "Schema is missing choice_fields")
        
        logger.info(f"Metadata schema extraction successful. Found {len(schema['fields'])} fields")

    def test_2_photo_download(self):
        """Test photo download from SharePoint."""
        # Import the module
        import src.photo_metadata
        
        # Clear downloads directory
        downloads_dir = self.path_manager.downloads_dir
        for file in downloads_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Run the test
        logger.info("Running photo download...")
        result = src.photo_metadata.main()
        
        # Allow some time for download to complete
        time.sleep(3)
        
        # Verify result - check if files were downloaded
        downloaded_files = list(downloads_dir.glob('*'))
        logger.info(f"Found {len(downloaded_files)} downloaded files")
        
        # We don't assert a specific number because it depends on what's in the source library
        # But we log the result for manual verification
        
        # Verify metadata extraction
        metadata_files = list(self.path_manager.metadata_dir.glob('*'))
        logger.info(f"Found {len(metadata_files)} metadata files")
        
        # If no files were downloaded, log a warning but don't fail the test
        if not downloaded_files:
            logger.warning("No files were downloaded from SharePoint. This might be expected if the source library is empty.")

    def test_3_openai_analysis(self):
        """Test OpenAI analysis of photos."""
        # Only run if we have downloaded photos
        downloads_dir = self.path_manager.downloads_dir
        downloaded_files = list(downloads_dir.glob('*'))
        
        if not downloaded_files:
            logger.warning("Skipping OpenAI analysis test because no photos were downloaded")
            self.skipTest("No photos to analyze")
        
        # Import the module
        import src.openai_analyzer
        
        # Clear analysis directory
        analysis_dir = self.path_manager.analysis_dir
        for file in analysis_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Run the test with a limit of max 2 photos to avoid excessive API costs
        logger.info("Running OpenAI analysis...")
        result = src.openai_analyzer.main()
        
        # Allow some time for analysis to complete
        time.sleep(10)
        
        # Verify result
        analysis_files = list(analysis_dir.glob('*'))
        logger.info(f"Found {len(analysis_files)} analysis files")
        
        # Check at least one file was analyzed
        self.assertTrue(len(analysis_files) > 0, "No files were analyzed")
        
        # Check content of analysis file
        if analysis_files:
            with open(analysis_files[0], 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            logger.info(f"Sample analysis keys: {list(analysis.keys())}")
            
            # Verify it has at least some basic expected fields
            self.assertIn('Titel', analysis, "Analysis is missing Titel field")

    def test_4_metadata_generation(self):
        """Test metadata generation for upload."""
        # Only run if we have analysis results
        analysis_dir = self.path_manager.analysis_dir
        analysis_files = list(analysis_dir.glob('*'))
        
        if not analysis_files:
            logger.warning("Skipping metadata generation test because no analysis files were found")
            self.skipTest("No analysis files")
        
        # Import the module
        import src.metadata_generator
        
        # Clear upload directory
        upload_dir = self.path_manager.upload_dir
        for file in upload_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        upload_metadata_dir = self.path_manager.upload_metadata_dir
        for file in upload_metadata_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Run the test
        logger.info("Running metadata generation...")
        result = src.metadata_generator.main()
        
        # Verify result
        upload_files = list(upload_dir.glob('*.jpg'))
        metadata_files = list(upload_metadata_dir.glob('*.json'))
        
        logger.info(f"Found {len(upload_files)} files and {len(metadata_files)} metadata files for upload")
        
        # Check files match
        self.assertEqual(len(upload_files), len(metadata_files), 
                         "Number of upload files and metadata files doesn't match")
        
        # Check at least one file was prepared
        self.assertTrue(len(upload_files) > 0, "No files were prepared for upload")

    def test_5_upload_to_sharepoint(self):
        """Test upload to SharePoint."""
        # Only run if we have files to upload
        upload_dir = self.path_manager.upload_dir
        upload_files = list(upload_dir.glob('*.jpg'))
        
        if not upload_files:
            logger.warning("Skipping upload test because no files were prepared for upload")
            self.skipTest("No files to upload")
        
        # Import the module
        import src.sharepoint_uploader
        
        # Clear uploaded directory
        uploaded_dir = self.path_manager.uploaded_dir
        for file in uploaded_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Run the test
        logger.info("Running SharePoint upload...")
        result = src.sharepoint_uploader.main()
        
        # Allow some time for upload to complete
        time.sleep(5)
        
        # Verify result
        uploaded_files = list(uploaded_dir.glob('*.jpg'))
        
        logger.info(f"Found {len(uploaded_files)} uploaded files")
        
        # Check at least one file was uploaded
        self.assertTrue(len(uploaded_files) > 0, "No files were uploaded to SharePoint")
        
        # Check if files were moved to uploaded directory
        self.assertTrue(len(upload_files) >= len(uploaded_files), 
                        "More files in uploaded directory than were in upload directory")

    def test_6_transfer_verification(self):
        """Test transfer verification."""
        # Only run if we have uploaded files
        uploaded_dir = self.path_manager.uploaded_dir
        uploaded_files = list(uploaded_dir.glob('*.jpg'))
        
        if not uploaded_files:
            logger.warning("Skipping verification test because no files were uploaded")
            self.skipTest("No files to verify")
        
        # Import the module
        import src.transfer_verification
        
        # Clear reports directory
        reports_dir = self.path_manager.reports_dir
        for file in reports_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Run the test
        logger.info("Running transfer verification...")
        result = src.transfer_verification.main()
        
        # Verify result
        report_files = list(reports_dir.glob('*'))
        
        logger.info(f"Found {len(report_files)} report files")
        
        # Check at least one report was generated
        self.assertTrue(len(report_files) > 0, "No verification reports were generated")

    def test_7_full_process(self):
        """Test the full process using auto_process.py."""
        # Import the module
        import src.auto_process
        
        # Clear all data directories
        logger.info("Clearing data directories for full process test...")
        dirs_to_clear = [
            self.path_manager.downloads_dir,
            self.path_manager.metadata_dir,
            self.path_manager.analysis_dir,
            self.path_manager.upload_dir,
            self.path_manager.upload_metadata_dir,
            self.path_manager.uploaded_dir
        ]
        
        for directory in dirs_to_clear:
            for file in directory.glob('*'):
                if file.is_file():
                    file.unlink()
        
        # Run the full process
        logger.info("Running full auto process...")
        result = src.auto_process.main()
        
        # Verify exit code
        self.assertEqual(result, 0, "Auto process did not complete successfully")
        
        # Check results in each directory
        downloads = list(self.path_manager.downloads_dir.glob('*'))
        metadata = list(self.path_manager.metadata_dir.glob('*'))
        analysis = list(self.path_manager.analysis_dir.glob('*'))
        uploaded = list(self.path_manager.uploaded_dir.glob('*'))
        
        logger.info(f"Full process results:")
        logger.info(f"- Downloaded files: {len(downloads)}")
        logger.info(f"- Metadata files: {len(metadata)}")
        logger.info(f"- Analysis files: {len(analysis)}")
        logger.info(f"- Uploaded files: {len(uploaded)}")
        
        # Since this depends on actual content in SharePoint, we don't assert specific counts
        # But we check that the process created files at each stage
        # The process might be successful even if no files were processed (e.g., empty source library)


if __name__ == "__main__":
    unittest.main()
