#!/usr/bin/env python3
"""
Integration Test for Photo Agent

This script performs end-to-end testing of the Photo Agent workflow 
by mocking external services and validating the interactions between components.
"""

import os
import sys
import shutil
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.utils.config import get_config
from src.utils.paths import get_path_manager


class IntegrationTest(unittest.TestCase):
    """Integration test for the full Photo Agent workflow."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Get configuration and paths
        cls.config = get_config()
        cls.path_manager = get_path_manager()
        
        # Create test directory structure
        cls.test_dir = Path("./test_data")
        cls.test_downloads = cls.test_dir / "downloads"
        cls.test_metadata = cls.test_dir / "metadata"
        cls.test_analysis = cls.test_dir / "analysis"
        cls.test_upload = cls.test_dir / "upload"
        cls.test_uploaded = cls.test_dir / "uploaded"
        
        # Create test directories
        for directory in [cls.test_dir, cls.test_downloads, cls.test_metadata, 
                          cls.test_analysis, cls.test_upload, cls.test_uploaded]:
            directory.mkdir(exist_ok=True, parents=True)
        
        # Create sample test files
        cls.create_test_files()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Remove test directory
        shutil.rmtree(cls.test_dir)

    @classmethod
    def create_test_files(cls):
        """Create sample files for testing."""
        # Create a sample JSON schema
        sample_schema = {
            "library_title": "Test Library",
            "fields": [
                {
                    "internal_name": "Title",
                    "title": "Titel",
                    "type": "Text",
                    "required": True
                },
                {
                    "internal_name": "Description", 
                    "title": "Beschreibung",
                    "type": "Note",
                    "required": False
                },
                {
                    "internal_name": "Category",
                    "title": "Projektkategorie",
                    "type": "Choice",
                    "required": False,
                    "choices": ["Wohnbaute", "Industrie", "Umbau"]
                }
            ],
            "choice_fields": {
                "Category": {
                    "title": "Projektkategorie",
                    "type": "Choice",
                    "choices": ["Wohnbaute", "Industrie", "Umbau"]
                }
            }
        }
        
        # Save sample schema
        with open(cls.test_dir / "test_schema.json", "w", encoding="utf-8") as f:
            json.dump(sample_schema, f, indent=2)
        
        # Create a sample "downloaded" image file (just a text file for testing)
        with open(cls.test_downloads / "test_image.jpg", "w", encoding="utf-8") as f:
            f.write("This is a mock image file for testing.")
        
        # Create a sample metadata file
        sample_metadata = {
            "ImageWidth": 800,
            "ImageHeight": 600,
            "ImageFormat": "JPEG",
            "DateTimeOriginal": "2023:01:01 12:00:00"
        }
        
        with open(cls.test_metadata / "test_image.json", "w", encoding="utf-8") as f:
            json.dump(sample_metadata, f, indent=2)
        
        # Create a sample OpenAI analysis result
        sample_analysis = {
            "Titel": "Modernes Holzhaus mit Holzfassade",
            "Projektkategorie": "Wohnbaute",
            "Beschreibung": "Ein modernes Einfamilienhaus mit vertikaler Holzfassade und großen Fenstern."
        }
        
        with open(cls.test_analysis / "test_image_analysis.json", "w", encoding="utf-8") as f:
            json.dump(sample_analysis, f, indent=2)

    def test_1_metadata_schema(self):
        """Test metadata schema extraction."""
        with patch("src.metadata_schema.get_sharepoint_context") as mock_context, \
             patch("src.metadata_schema.get_library") as mock_get_library, \
             patch("src.metadata_schema.get_field_schema") as mock_get_schema:
            
            # Mock SharePoint responses
            mock_context.return_value = MagicMock()
            mock_library = MagicMock()
            mock_library.properties = {"Title": "Test Library"}
            mock_get_library.return_value = mock_library
            
            # Mock schema data
            with open(self.test_dir / "test_schema.json", "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            
            mock_get_schema.return_value = schema_data["fields"]
            
            # Import here to use the patched functions
            from src.metadata_schema import get_choice_fields, save_schema_to_json
            
            # Run the test
            choice_fields = get_choice_fields(schema_data["fields"])
            save_schema_to_json({
                "library_title": "Test Library",
                "fields": schema_data["fields"],
                "choice_fields": choice_fields
            }, self.test_dir / "output_schema.json")
            
            # Verify results
            self.assertTrue((self.test_dir / "output_schema.json").exists())
            with open(self.test_dir / "output_schema.json", "r", encoding="utf-8") as f:
                saved_schema = json.load(f)
            
            self.assertEqual(saved_schema["library_title"], "Test Library")
            self.assertIn("fields", saved_schema)
            self.assertIn("choice_fields", saved_schema)

    def test_2_photo_metadata(self):
        """Test photo metadata extraction."""
        with patch("src.photo_metadata.get_sharepoint_context") as mock_context, \
             patch("src.photo_metadata.get_library") as mock_get_library, \
             patch("src.photo_metadata.get_photo_files") as mock_get_photos, \
             patch("src.photo_metadata.extract_exif_metadata") as mock_exif, \
             patch("src.photo_metadata.download_photo") as mock_download, \
             patch("src.photo_metadata.delete_sharepoint_file") as mock_delete:
            
            # Mock SharePoint responses
            mock_context.return_value = MagicMock()
            mock_library = MagicMock()
            mock_library.properties = {"Title": "Test Library"}
            mock_get_library.return_value = mock_library
            
            # Mock file download
            mock_download.return_value = self.test_downloads / "test_image.jpg"
            
            # Mock EXIF data
            with open(self.test_metadata / "test_image.json", "r", encoding="utf-8") as f:
                exif_data = json.load(f)
            
            mock_exif.return_value = exif_data
            
            # Mock successful deletion
            mock_delete.return_value = True
            
            # Mock photo files
            mock_file = MagicMock()
            mock_file.properties = {"Name": "test_image.jpg", "ServerRelativeUrl": "/sites/test/test_image.jpg", "Length": 10240}
            photo_files = [{
                "name": "test_image.jpg",
                "url": "/sites/test/test_image.jpg",
                "size": 10240,
                "file_obj": mock_file
            }]
            mock_get_photos.return_value = photo_files
            
            # Import here to use the patched functions
            from src.photo_metadata import process_photo_batch
            
            # Run the test
            processed = process_photo_batch(photo_files, 1)
            
            # Verify results
            self.assertEqual(len(processed), 1)
            self.assertEqual(processed[0]["name"], "test_image.jpg")
            mock_download.assert_called_once()
            mock_exif.assert_called_once()
            mock_delete.assert_called_once()

    def test_3_openai_analyzer(self):
        """Test OpenAI analyzer."""
        with patch("openai.chat.completions.create") as mock_openai, \
             patch("src.openai_analyzer.encode_image_to_base64") as mock_encode:
            
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps({
                "Titel": "Modernes Holzhaus mit Holzfassade",
                "Projektkategorie": "Wohnbaute",
                "Beschreibung": "Ein modernes Einfamilienhaus mit vertikaler Holzfassade und großen Fenstern."
            })
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_openai.return_value = mock_response
            
            # Mock base64 encoding
            mock_encode.return_value = "base64encodedstring"
            
            # Import necessary functions
            from src.openai_analyzer import analyze_photo_with_openai, save_analysis_to_json
            
            # Test analyze function
            analysis = analyze_photo_with_openai(
                self.test_downloads / "test_image.jpg", 
                "Test prompt"
            )
            
            # Verify results
            self.assertIn("Titel", analysis)
            self.assertEqual(analysis["Projektkategorie"], "Wohnbaute")
            
            # Test saving analysis
            analysis_path = save_analysis_to_json(
                analysis, 
                self.test_downloads / "test_image.jpg"
            )
            
            self.assertTrue(analysis_path.exists())

    def test_4_metadata_generator(self):
        """Test metadata generator."""
        # Use the sample files we created
        with patch("src.metadata_generator.load_metadata_schema") as mock_schema:
            
            # Mock schema
            with open(self.test_dir / "test_schema.json", "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            
            mock_schema.return_value = schema_data
            
            # Create a test photo info
            photo_info = {
                "name": "test_image.jpg",
                "local_path": self.test_downloads / "test_image.jpg",
                "analysis": {
                    "Titel": "Modernes Holzhaus mit Holzfassade",
                    "Projektkategorie": "Wohnbaute",
                    "Beschreibung": "Ein modernes Einfamilienhaus mit vertikaler Holzfassade und großen Fenstern."
                }
            }
            
            # Import functions
            from src.metadata_generator import (
                generate_target_filename, 
                generate_metadata_for_upload,
                save_metadata_for_upload
            )
            
            # Test filename generation
            target_filename = generate_target_filename("test_image.jpg", 1)
            self.assertIn("Erni_Referenzfoto_0001", target_filename)
            
            # Test metadata generation
            metadata = generate_metadata_for_upload(photo_info, schema_data, target_filename)
            self.assertIn("Title", metadata)
            self.assertEqual(metadata["Title"], "Modernes Holzhaus mit Holzfassade")
            
            # Test metadata saving
            with patch("src.metadata_generator.UPLOAD_METADATA_DIR", self.test_upload):
                metadata_path = save_metadata_for_upload(metadata, target_filename)
                self.assertTrue(Path(metadata_path).exists())

    def test_5_sharepoint_uploader(self):
        """Test SharePoint uploader."""
        with patch("src.sharepoint_uploader.get_sharepoint_context") as mock_context, \
             patch("src.sharepoint_uploader.get_library") as mock_get_library, \
             patch("src.sharepoint_uploader.get_files_for_upload") as mock_get_files:
            
            # Mock SharePoint responses
            mock_context.return_value = MagicMock()
            mock_library = MagicMock()
            mock_folder = MagicMock()
            mock_file = MagicMock()
            mock_item = MagicMock()
            
            # Setup the mock chain
            mock_library.root_folder = mock_folder
            mock_folder.upload_file.return_value = mock_file
            mock_file.listItemAllFields = mock_item
            mock_get_library.return_value = mock_library
            
            # Create test upload files
            # Create a test file in upload directory
            os.makedirs(self.test_upload, exist_ok=True)
            test_upload_file = self.test_upload / "Erni_Referenzfoto_0001.jpg"
            with open(test_upload_file, "w", encoding="utf-8") as f:
                f.write("Test file content")
            
            # Create metadata
            os.makedirs(self.test_upload / "metadata", exist_ok=True)
            test_metadata_file = self.test_upload / "metadata" / "Erni_Referenzfoto_0001.json"
            with open(test_metadata_file, "w", encoding="utf-8") as f:
                json.dump({
                    "Title": "Modernes Holzhaus",
                    "Category": "Wohnbaute"
                }, f)
            
            # Mock files for upload
            mock_get_files.return_value = [{
                "name": "Erni_Referenzfoto_0001.jpg",
                "path": test_upload_file,
                "metadata_path": test_metadata_file,
                "metadata": {
                    "Title": "Modernes Holzhaus",
                    "Category": "Wohnbaute"
                }
            }]
            
            # Import function
            from src.sharepoint_uploader import upload_file_to_sharepoint, upload_files_to_sharepoint
            
            # Patch the registry
            with patch("src.sharepoint_uploader.get_registry") as mock_registry:
                mock_reg = MagicMock()
                mock_registry.return_value = mock_reg
                
                # Patch the move operation
                with patch("src.sharepoint_uploader.shutil.move") as mock_move:
                    mock_move.return_value = None
                    
                    # Run the test
                    success, failed = upload_files_to_sharepoint(mock_get_files.return_value)
                    
                    # Verify results
                    self.assertEqual(len(success), 1)
                    self.assertEqual(len(failed), 0)
                    mock_folder.upload_file.assert_called()
                    mock_item.update.assert_called_once()
                    mock_reg.mark_as_uploaded.assert_called()

    def test_6_full_process_integration(self):
        """Test the full process integration."""
        # Override default directories for testing
        with patch("src.utils.paths.PathManager") as MockPathManager:
            # Make the path manager return our test directories
            mock_path_manager = MagicMock()
            mock_path_manager.downloads_dir = self.test_downloads
            mock_path_manager.metadata_dir = self.test_metadata
            mock_path_manager.analysis_dir = self.test_analysis
            mock_path_manager.upload_dir = self.test_upload
            mock_path_manager.upload_metadata_dir = self.test_upload / "metadata"
            mock_path_manager.uploaded_dir = self.test_uploaded
            mock_path_manager.config_dir = self.test_dir
            MockPathManager.return_value = mock_path_manager
            
            # Also patch the subprocess calls to prevent actual script execution
            with patch("src.auto_process.subprocess.run") as mock_run:
                # Make subprocess.run return success for all scripts
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Test output"
                mock_run.return_value = mock_result
                
                # Import the main process
                from src.auto_process import main
                
                # Run the test
                result = main()
                
                # Verify results
                self.assertEqual(result, 0)
                self.assertEqual(mock_run.call_count, 5)  # One call for each script


if __name__ == "__main__":
    unittest.main()
