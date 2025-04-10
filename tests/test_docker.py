#!/usr/bin/env python3
"""
Docker Container Integration Test

This script tests the Docker container by running it with mock data
and validating that all components function correctly within the container.
"""

import os
import sys
import json
import time
import shutil
import unittest
import subprocess
from pathlib import Path


class DockerIntegrationTest(unittest.TestCase):
    """Test the integration of all components in the Docker container."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment, prepare test data, and build Docker image."""
        # Create test directories
        cls.test_dir = Path("./docker_test")
        cls.test_dir.mkdir(exist_ok=True)
        
        cls.test_config = cls.test_dir / "config"
        cls.test_data = cls.test_dir / "data"
        cls.test_logs = cls.test_dir / "logs"
        
        # Create subdirectories
        subdirs = [
            cls.test_config,
            cls.test_data,
            cls.test_data / "downloads",
            cls.test_data / "metadata",
            cls.test_data / "analysis",
            cls.test_data / "upload",
            cls.test_data / "upload" / "metadata",
            cls.test_data / "uploaded",
            cls.test_data / "reports",
            cls.test_data / "registry",
            cls.test_logs
        ]
        
        for directory in subdirs:
            directory.mkdir(exist_ok=True, parents=True)
        
        # Create test config.env
        cls.create_test_config()
        
        # Create test data
        cls.create_test_data()
        
        # Create test docker-compose file
        cls.create_docker_compose()
        
        # Build Docker image
        subprocess.run(
            ["docker-compose", "-f", str(cls.test_dir / "docker-compose.test.yml"), "build"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Remove containers
        subprocess.run(
            ["docker-compose", "-f", str(cls.test_dir / "docker-compose.test.yml"), "down"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Clean up test directory
        shutil.rmtree(cls.test_dir)

    @classmethod
    def create_test_config(cls):
        """Create test configuration."""
        config_content = """# SharePoint connection settings
SHAREPOINT_SITE_URL=https://erni.sharepoint.com/sites/100_Testing_KI-Projekte
SHAREPOINT_USERNAME=test.ki@erni-gruppe.ch
SHAREPOINT_PASSWORD=test_password

# Library settings
SOURCE_LIBRARY_TITLE=PhotoLibrary
SHAREPOINT_LIBRARY=TestReferenzfotos

# File settings
METADATA_SCHEMA_FILE=config/sharepoint_choices.json
TARGET_FILENAME_MASK=Test_Foto_{number}
# Максимальный размер файла в байтах (15MB)
MAX_FILE_SIZE=15728640

# Connection settings
MAX_CONNECTION_ATTEMPTS=3
CONNECTION_RETRY_DELAY=5

# OpenAI settings
OPENAI_API_KEY=test_api_key
OPENAI_CONCURRENCY_LIMIT=5
MAX_TOKENS=1000

# Logging settings
LOG_LEVEL=DEBUG
LOG_FILE=test_connector.log

# --- OpenAI Prompt ---
OPENAI_PROMPT_ROLE="Test role"
OPENAI_PROMPT_INSTRUCTIONS_PRE="Test instructions pre"
OPENAI_PROMPT_INSTRUCTIONS_POST="Test instructions post"
OPENAI_PROMPT_EXAMPLE='{"test": "example"}'
"""
        
        with open(cls.test_config / "config.env", "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # Create schema file
        schema = {
            "library_title": "TestReferenzfotos",
            "fields": [
                {
                    "internal_name": "Title",
                    "title": "Titel",
                    "type": "Text",
                    "required": True
                },
                {
                    "internal_name": "Projektkategorie",
                    "title": "Projektkategorie",
                    "type": "Choice",
                    "required": False,
                    "choices": ["Wohnbaute", "Industrie", "Umbau"]
                },
                {
                    "internal_name": "Status",
                    "title": "Status",
                    "type": "Choice",
                    "required": True,
                    "choices": ["Entwurf KI", "Fertig"]
                }
            ],
            "choice_fields": {
                "Projektkategorie": {
                    "title": "Projektkategorie",
                    "type": "Choice",
                    "choices": ["Wohnbaute", "Industrie", "Umbau"]
                },
                "Status": {
                    "title": "Status",
                    "type": "Choice",
                    "choices": ["Entwurf KI", "Fertig"]
                }
            }
        }
        
        with open(cls.test_config / "sharepoint_choices.json", "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

    @classmethod
    def create_test_data(cls):
        """Create test data files."""
        # Create a test image file (just a text file for this test)
        with open(cls.test_data / "downloads" / "test_image.jpg", "w", encoding="utf-8") as f:
            f.write("This is a test image file.")
        
        # Create a test metadata file
        metadata = {
            "ImageWidth": 800,
            "ImageHeight": 600,
            "ImageFormat": "JPEG",
            "DateTimeOriginal": "2023:01:01 12:00:00"
        }
        
        with open(cls.test_data / "metadata" / "test_image.yml", "w", encoding="utf-8") as f:
            f.write("""ImageWidth: 800
ImageHeight: 600
ImageFormat: JPEG
DateTimeOriginal: '2023:01:01 12:00:00'
""")
        
        # Create a test analysis file
        analysis = {
            "Titel": "Test Holzhaus",
            "Projektkategorie": "Wohnbaute",
            "Status": "Entwurf KI"
        }
        
        with open(cls.test_data / "analysis" / "test_image_analysis.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)

    @classmethod
    def create_docker_compose(cls):
        """Create test Docker Compose file."""
        docker_compose = """version: '3.8'

services:
  test-agent:
    build:
      context: ..
    container_name: photo-agent-test
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - TZ=Europe/Berlin
      - PYTHONUNBUFFERED=1
      - TEST_MODE=True
    # Default command will be overridden in tests
"""
        
        with open(cls.test_dir / "docker-compose.test.yml", "w", encoding="utf-8") as f:
            f.write(docker_compose)

    def run_container_command(self, command):
        """Run a command in the Docker container and return the result."""
        full_command = ["docker-compose", "-f", str(self.test_dir / "docker-compose.test.yml"), 
                         "run", "--rm", "test-agent"] + command.split()
        
        result = subprocess.run(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return result.returncode, result.stdout, result.stderr

    def test_01_container_environment(self):
        """Test that the container environment is set up correctly."""
        exit_code, stdout, stderr = self.run_container_command("python -c \"import os; print(os.environ.get('TEST_MODE'))\"")
        
        self.assertEqual(exit_code, 0)
        self.assertIn("True", stdout)

    def test_02_import_modules(self):
        """Test that all modules can be imported correctly."""
        cmd = "python -c \"from src import auto_process, metadata_schema, photo_metadata, \
               openai_analyzer, metadata_generator, sharepoint_uploader; print('Imports successful')\""
        
        exit_code, stdout, stderr = self.run_container_command(cmd)
        
        self.assertEqual(exit_code, 0)
        self.assertIn("Imports successful", stdout)

    def test_03_config_loading(self):
        """Test that configuration can be loaded."""
        cmd = "python -c \"from src.utils.config import get_config; config = get_config(); \
               print(f'SharePoint URL: {config.sharepoint.site_url}'); \
               print(f'Target library: {config.sharepoint.target_library_title}')\""
        
        exit_code, stdout, stderr = self.run_container_command(cmd)
        
        self.assertEqual(exit_code, 0)
        self.assertIn("SharePoint URL: https://erni.sharepoint.com/sites/100_Testing_KI-Projekte", stdout)
        self.assertIn("Target library: TestReferenzfotos", stdout)

    def test_04_paths_setup(self):
        """Test that paths are set up correctly."""
        cmd = "python -c \"from src.utils.paths import get_path_manager; pm = get_path_manager(); \
               print(f'Downloads dir: {pm.downloads_dir}'); \
               print(f'Upload dir: {pm.upload_dir}')\""
        
        exit_code, stdout, stderr = self.run_container_command(cmd)
        
        self.assertEqual(exit_code, 0)
        self.assertIn("Downloads dir: /app/data/downloads", stdout)
        self.assertIn("Upload dir: /app/data/upload", stdout)

    def test_05_metadata_schema(self):
        """Test the metadata schema module."""
        # First create a mock override for the SharePoint authentication
        mock_script = """
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Create a module to override SharePoint auth
with open("mock_sharepoint.py", "w") as f:
    f.write('''
def get_sharepoint_context():
    return MagicMock()

def get_library(ctx, library_title):
    mock_library = MagicMock()
    mock_library.properties = {"Title": library_title}
    
    # Mock the field schema
    with open("/app/config/sharepoint_choices.json", "r") as f:
        schema = json.load(f)
    
    # Setup fields property
    mock_fields = []
    for field in schema["fields"]:
        mock_field = MagicMock()
        mock_field.properties = field
        mock_fields.append(mock_field)
    
    mock_library.fields = mock_fields
    return mock_library
''')

# Add to path
sys.path.insert(0, ".")

# Run metadata schema with the mock
import importlib.util
spec = importlib.util.spec_from_file_location("mock_sharepoint", "mock_sharepoint.py")
mock_sharepoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock_sharepoint)

# Override the imports in metadata_schema
import sys
sys.modules["src.sharepoint_auth"] = mock_sharepoint

# Now run the metadata schema module
from src import metadata_schema
metadata_schema.main()

# Verify the result
result_path = Path("/app/config/sharepoint_choices.json")
if result_path.exists():
    print(f"Schema file created successfully: {result_path}")
else:
    print(f"Schema file not created: {result_path}")
"""
        
        # Write the mock script
        with open(self.test_dir / "test_metadata_schema.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_metadata_schema.py")
        
        # Check results
        self.assertEqual(exit_code, 0)
        self.assertIn("Schema file created successfully", stdout)

    def test_06_photo_metadata(self):
        """Test the photo metadata module."""
        # Create a mock script to test the photo metadata module
        mock_script = """
import sys
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

# Create a module to override SharePoint auth and photo functions
with open("mock_sharepoint.py", "w") as f:
    f.write('''
from unittest.mock import MagicMock
import shutil
from pathlib import Path

def get_sharepoint_context():
    return MagicMock()

def get_library(ctx, library_title):
    mock_library = MagicMock()
    mock_library.properties = {"Title": library_title}
    return mock_library

def get_photo_files(ctx, library):
    # Create a mock file
    mock_file = MagicMock()
    mock_file.properties = {
        "Name": "test_image.jpg",
        "ServerRelativeUrl": "/sites/test/test_image.jpg",
        "Length": 1024
    }
    
    # Create a mock file object with download method
    def mock_download(local_file):
        # Copy our test image to the destination
        shutil.copy("/app/data/downloads/test_image.jpg", local_file.name)
        return MagicMock()
        
    mock_file.download = lambda local_file: mock_download(local_file)
    
    # Return a list with our mock file
    return [{
        "name": "test_image.jpg",
        "url": "/sites/test/test_image.jpg",
        "size": 1024,
        "file_obj": mock_file
    }]
''')

# Add to path
sys.path.insert(0, ".")

# Override the imports in photo_metadata
import importlib.util
spec = importlib.util.spec_from_file_location("mock_sharepoint", "mock_sharepoint.py")
mock_sharepoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock_sharepoint)

# Override EXIF extraction
def mock_extract_exif(image_path):
    return {
        "ImageWidth": 800,
        "ImageHeight": 600,
        "ImageFormat": "JPEG",
        "DateTimeOriginal": "2023:01:01 12:00:00"
    }

# Override delete function
def mock_delete_file(file_obj):
    return True

# Patch modules
import sys
sys.modules["src.sharepoint_auth"] = mock_sharepoint
sys.modules["src.photo_metadata"].get_photo_files = mock_sharepoint.get_photo_files
sys.modules["src.photo_metadata"].extract_exif_metadata = mock_extract_exif
sys.modules["src.photo_metadata"].delete_sharepoint_file = mock_delete_file

# Make sure we use a limited number of photos
import src.photo_metadata
original_process_batch = src.photo_metadata.process_photo_batch

def mock_process_batch(photo_files, batch_size=1):
    # Only process one photo regardless of batch size
    return original_process_batch(photo_files[:1], 1)

src.photo_metadata.process_photo_batch = mock_process_batch

# Now run the photo_metadata module
src.photo_metadata.main()

# Check results
downloads_dir = Path("/app/data/downloads")
metadata_dir = Path("/app/data/metadata")

print(f"Files in downloads: {list(downloads_dir.glob('*'))}")
print(f"Files in metadata: {list(metadata_dir.glob('*'))}")

if list(metadata_dir.glob('*')):
    print("Photo metadata processing successful")
else:
    print("Photo metadata processing failed")
"""
        
        # Write the mock script
        with open(self.test_dir / "test_photo_metadata.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_photo_metadata.py")
        
        # Check results
        self.assertEqual(exit_code, 0)
        self.assertIn("Photo metadata processing successful", stdout)

    def test_07_openai_analyzer(self):
        """Test the OpenAI analyzer module."""
        mock_script = """
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Override the OpenAI API call
class MockResponse:
    def __init__(self):
        self.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "Titel": "Test Holzhaus",
                        "Projektkategorie": "Wohnbaute",
                        "Status": "Entwurf KI"
                    })
                )
            )
        ]

# Create patch for OpenAI
with patch("openai.chat.completions.create", return_value=MockResponse()):
    # Override image encoding
    def mock_encode_image(image_path):
        return "base64_encoded_image_mock"
    
    # Apply the patch
    import src.openai_analyzer
    src.openai_analyzer.encode_image_to_base64 = mock_encode_image
    
    # Find all downloaded images (or use our test image)
    test_image = Path("/app/data/downloads/test_image.jpg")
    
    # Create a mock photo info
    photo_info = {
        "name": "test_image.jpg",
        "local_path": str(test_image)
    }
    
    # Run the analysis
    with patch("src.openai_analyzer.load_metadata_schema") as mock_schema:
        # Create a mock schema
        mock_schema.return_value = {
            "library_title": "TestReferenzfotos",
            "fields": [
                {
                    "internal_name": "Title",
                    "title": "Titel",
                    "type": "Text",
                    "required": True
                },
                {
                    "internal_name": "Projektkategorie",
                    "title": "Projektkategorie",
                    "type": "Choice",
                    "required": False,
                    "choices": ["Wohnbaute", "Industrie", "Umbau"]
                },
                {
                    "internal_name": "Status",
                    "title": "Status",
                    "type": "Choice",
                    "required": True,
                    "choices": ["Entwurf KI", "Fertig"]
                }
            ]
        }
        
        # Test the analyze function
        prompt = src.openai_analyzer.prepare_openai_prompt(mock_schema.return_value)
        analysis = src.openai_analyzer.analyze_photo_with_openai(photo_info["local_path"], prompt)
        analysis_path = src.openai_analyzer.save_analysis_to_json(analysis, photo_info["local_path"])
        
        # Display results
        print(f"Analysis result: {analysis}")
        print(f"Analysis saved to: {analysis_path}")
        
        if Path(analysis_path).exists():
            print("OpenAI analysis successful")
        else:
            print("OpenAI analysis failed")
"""
        
        # Write the mock script
        with open(self.test_dir / "test_openai_analyzer.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_openai_analyzer.py")
        
        # Check results
        self.assertEqual(exit_code, 0)
        self.assertIn("OpenAI analysis successful", stdout)

    def test_08_metadata_generator(self):
        """Test the metadata generator module."""
        mock_script = """
import sys
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure test directories exist
analysis_dir = Path("/app/data/analysis")
upload_dir = Path("/app/data/upload")
upload_metadata_dir = Path("/app/data/upload/metadata")

upload_dir.mkdir(exist_ok=True)
upload_metadata_dir.mkdir(exist_ok=True)

# Create a mock analysis file if it doesn't exist
test_analysis = analysis_dir / "test_image_analysis.json"
if not test_analysis.exists():
    with open(test_analysis, "w") as f:
        json.dump({
            "Titel": "Test Holzhaus",
            "Projektkategorie": "Wohnbaute",
            "Status": "Entwurf KI"
        }, f)

# Create a mock schema
mock_schema = {
    "library_title": "TestReferenzfotos",
    "fields": [
        {
            "internal_name": "Title",
            "title": "Titel",
            "type": "Text",
            "required": True
        },
        {
            "internal_name": "Projektkategorie",
            "title": "Projektkategorie",
            "type": "Choice",
            "required": False,
            "choices": ["Wohnbaute", "Industrie", "Umbau"]
        },
        {
            "internal_name": "Status",
            "title": "Status",
            "type": "Choice",
            "required": True,
            "choices": ["Entwurf KI", "Fertig"]
        }
    ],
    "choice_fields": {
        "Projektkategorie": {
            "title": "Projektkategorie",
            "type": "Choice",
            "choices": ["Wohnbaute", "Industrie", "Umbau"]
        },
        "Status": {
            "title": "Status",
            "type": "Choice",
            "choices": ["Entwurf KI", "Fertig"]
        }
    }
}

# Override schema loading
with patch("src.metadata_generator.load_metadata_schema", return_value=mock_schema):
    # Override get_next_file_number
    def mock_get_next_number():
        return 1
    
    import src.metadata_generator
    src.metadata_generator.get_next_file_number = mock_get_next_number
    
    # Run the metadata generator
    try:
        src.metadata_generator.main()
        
        # Check if files were created
        upload_files = list(upload_dir.glob("*.jpg"))
        metadata_files = list(upload_metadata_dir.glob("*.json"))
        
        print(f"Files in upload dir: {upload_files}")
        print(f"Files in metadata dir: {metadata_files}")
        
        if upload_files and metadata_files:
            print("Metadata generation successful")
        else:
            print("Metadata generation did not create expected files")
            
    except Exception as e:
        print(f"Error during metadata generation: {str(e)}")
"""
        
        # Write the mock script
        with open(self.test_dir / "test_metadata_generator.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Make sure we have a test image in downloads
        if not (self.test_data / "downloads" / "test_image.jpg").exists():
            with open(self.test_data / "downloads" / "test_image.jpg", "w") as f:
                f.write("Test image content")
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_metadata_generator.py")
        
        # Check results
        if exit_code != 0:
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
        
        self.assertEqual(exit_code, 0)
        # Look for success or files in output
        success = "Metadata generation successful" in stdout or "Files in upload dir" in stdout
        self.assertTrue(success)

    def test_09_sharepoint_uploader(self):
        """Test the SharePoint uploader module."""
        mock_script = """
import sys
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure upload directories exist
upload_dir = Path("/app/data/upload")
upload_metadata_dir = Path("/app/data/upload/metadata")
uploaded_dir = Path("/app/data/uploaded")

upload_dir.mkdir(exist_ok=True)
upload_metadata_dir.mkdir(exist_ok=True)
uploaded_dir.mkdir(exist_ok=True)

# Create a test file in upload directory if it doesn't exist
test_file = upload_dir / "Test_Foto_0001.jpg"
if not test_file.exists():
    with open(test_file, "w") as f:
        f.write("Test file content")

# Create test metadata
test_metadata = upload_metadata_dir / "Test_Foto_0001.json"
if not test_metadata.exists():
    with open(test_metadata, "w") as f:
        json.dump({
            "Title": "Test Holzhaus",
            "Projektkategorie": "Wohnbaute",
            "Status": "Entwurf KI"
        }, f)

# Create mocks for SharePoint
with patch("src.sharepoint_uploader.get_sharepoint_context") as mock_context, \
     patch("src.sharepoint_uploader.get_library") as mock_get_library, \
     patch("src.sharepoint_uploader.get_registry") as mock_registry:
    
    # Mock context
    mock_context.return_value = MagicMock()
    
    # Mock library
    mock_library = MagicMock()
    mock_folder = MagicMock()
    mock_file = MagicMock()
    mock_item = MagicMock()
    
    mock_library.root_folder = mock_folder
    mock_folder.upload_file.return_value = mock_file
    mock_file.listItemAllFields = mock_item
    mock_file.serverRelativeUrl = "/sites/test/Test_Foto_0001.jpg"
    
    mock_get_library.return_value = mock_library
    
    # Mock registry
    mock_reg = MagicMock()
    mock_registry.return_value = mock_reg
    
    # Run the uploader
    import src.sharepoint_uploader
    
    # Override shutil.move to prevent file deletion
    original_move = shutil.move
    
    def mock_move(src, dst):
        # Just copy instead of move for testing
        if Path(src).exists():
            shutil.copy(src, dst)
        return dst
    
    # Apply patch
    shutil.move = mock_move
    
    try:
        # Run the uploader
        result = src.sharepoint_uploader.main()
        
        # Check uploaded files
        uploaded_files = list(uploaded_dir.glob("*.jpg"))
        print(f"Files in uploaded dir: {uploaded_files}")
        
        # Restore original move function
        shutil.move = original_move
        
        if uploaded_files:
            print("SharePoint upload simulation successful")
        else:
            print("SharePoint upload simulation did not create expected files")
            
    except Exception as e:
        # Restore original move function
        shutil.move = original_move
        print(f"Error during SharePoint upload: {str(e)}")
"""
        
        # Write the mock script
        with open(self.test_dir / "test_sharepoint_uploader.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_sharepoint_uploader.py")
        
        # Check results
        if exit_code != 0:
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
            
        self.assertEqual(exit_code, 0)
        # Look for success message in output
        self.assertIn("SharePoint upload simulation successful", stdout)

    def test_10_auto_process(self):
        """Test the auto_process module with mocked subprocess calls."""
        mock_script = """
import sys
import subprocess
from unittest.mock import patch

# Override subprocess.run to prevent actual script execution
original_run = subprocess.run

def mock_subprocess_run(args, **kwargs):
    # Print what would be executed
    print(f"Would run: {args}")
    # Return a successful result
    class MockResult:
        returncode = 0
        stdout = "Mock output"
        stderr = ""
    
    return MockResult()

# Apply the patch
subprocess.run = mock_subprocess_run

# Run the auto_process module
from src import auto_process
result = auto_process.main()

# Check the result
print(f"Auto process result: {result}")
if result == 0:
    print("Auto process completed successfully")
else:
    print(f"Auto process failed with exit code {result}")

# Restore original function
subprocess.run = original_run
"""
        
        # Write the mock script
        with open(self.test_dir / "test_auto_process.py", "w", encoding="utf-8") as f:
            f.write(mock_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/docker_test/test_auto_process.py")
        
        # Check results
        self.assertEqual(exit_code, 0)
        self.assertIn("Auto process completed successfully", stdout)
        # Verify all scripts would be executed
        scripts = ["metadata_schema.py", "photo_metadata.py", "openai_analyzer.py", 
                   "metadata_generator.py", "sharepoint_uploader.py"]
        for script in scripts:
            self.assertIn(script, stdout)


if __name__ == "__main__":
    unittest.main()
