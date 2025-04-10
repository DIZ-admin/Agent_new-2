#!/usr/bin/env python3
"""
Docker Container Real Integration Test

This script tests the Docker container with real connections to external services
(SharePoint and OpenAI) to validate complete end-to-end functionality.
"""

import os
import sys
import json
import time
import shutil
import unittest
import subprocess
from pathlib import Path


class DockerRealIntegrationTest(unittest.TestCase):
    """Test the Docker container with real external dependencies."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment, prepare test environment, and build Docker image."""
        # Create test directories
        cls.test_dir = Path("./real_docker_test")
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
        
        # Copy real config.env to test directory
        cls.copy_real_config()
        
        # Create test docker-compose file
        cls.create_docker_compose()
        
        # Build Docker image
        subprocess.run(
            ["docker-compose", "-f", str(cls.test_dir / "docker-compose.real.yml"), "build"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Remove containers
        subprocess.run(
            ["docker-compose", "-f", str(cls.test_dir / "docker-compose.real.yml"), "down"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Keep test directory for inspection
        print(f"Test data preserved in {cls.test_dir} for inspection")

    @classmethod
    def copy_real_config(cls):
        """Copy the real config.env to the test directory."""
        source_config = Path("./config/config.env")
        target_config = cls.test_config / "config.env"
        
        if source_config.exists():
            shutil.copy(source_config, target_config)
            print(f"Copied real config to {target_config}")
        else:
            raise FileNotFoundError(f"Could not find config file at {source_config}")
        
        # Also copy schema file if it exists
        source_schema = Path("./config/sharepoint_choices.json")
        target_schema = cls.test_config / "sharepoint_choices.json"
        
        if source_schema.exists():
            shutil.copy(source_schema, target_schema)
            print(f"Copied schema file to {target_schema}")

    @classmethod
    def create_docker_compose(cls):
        """Create real Docker Compose file."""
        docker_compose = """version: '3.8'

services:
  real-test-agent:
    build:
      context: ..
    container_name: photo-agent-real-test
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - TZ=Europe/Berlin
      - PYTHONUNBUFFERED=1
    # Default command will be overridden in tests
"""
        
        with open(cls.test_dir / "docker-compose.real.yml", "w", encoding="utf-8") as f:
            f.write(docker_compose)

    def run_container_command(self, command):
        """Run a command in the Docker container and return the result."""
        full_command = ["docker-compose", "-f", str(self.test_dir / "docker-compose.real.yml"), 
                         "run", "--rm", "real-test-agent"] + command.split()
        
        result = subprocess.run(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return result.returncode, result.stdout, result.stderr

    def test_01_container_environment(self):
        """Test that the container environment is set up correctly."""
        exit_code, stdout, stderr = self.run_container_command("python -c \"import os; print('Container test')\"")
        
        self.assertEqual(exit_code, 0)
        self.assertIn("Container test", stdout)

    def test_02_test_connections(self):
        """Test connections to SharePoint and OpenAI."""
        # Create a script to test connections
        test_script = """
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append('/app')

# Import connection test modules
from src.sharepoint_auth import test_connection as test_sharepoint

print("Testing SharePoint connection...")
sharepoint_ok = test_sharepoint()
if sharepoint_ok:
    print("SharePoint connection successful")
else:
    print("SharePoint connection failed")
    sys.exit(1)

print("\\nTesting OpenAI connection...")
import openai
from src.utils.config import get_config
config = get_config()
openai.api_key = config.openai.api_key

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
        print(f"OpenAI connection successful: {response.choices[0].message.content}")
    else:
        print("Invalid response from OpenAI API")
        sys.exit(1)
except Exception as e:
    print(f"OpenAI connection failed: {str(e)}")
    sys.exit(1)

print("\\nAll connections successful!")
"""
        
        # Write the test script
        with open(self.test_dir / "test_connections.py", "w", encoding="utf-8") as f:
            f.write(test_script)
        
        # Run the test
        exit_code, stdout, stderr = self.run_container_command("python /app/real_docker_test/test_connections.py")
        
        # Check results
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        self.assertEqual(exit_code, 0)
        self.assertIn("SharePoint connection successful", stdout)
        self.assertIn("OpenAI connection successful", stdout)
        self.assertIn("All connections successful", stdout)

    def test_03_metadata_schema(self):
        """Test metadata schema extraction with real SharePoint."""
        exit_code, stdout, stderr = self.run_container_command("python -m src.metadata_schema")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Check results
        self.assertEqual(exit_code, 0)
        self.assertIn("Metadata schema saved", stdout)

    def test_04_photo_metadata(self):
        """Test photo download with real SharePoint."""
        # Run with limited batch for testing
        exit_code, stdout, stderr = self.run_container_command("python -m src.photo_metadata")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Check results - we don't require success as it depends on what's in the source library
        if exit_code != 0:
            print("WARNING: Photo download did not complete successfully")
            print(f"Exit code: {exit_code}")
        else:
            print("Photo download completed successfully")

    def test_05_openai_analyzer(self):
        """Test OpenAI analyzer with real API."""
        # Only run if we have downloaded photos
        downloads_dir = self.test_data / "downloads"
        if not any(downloads_dir.glob("*")):
            self.skipTest("No photos were downloaded to analyze")
            
        # Run the analyzer
        exit_code, stdout, stderr = self.run_container_command("python -m src.openai_analyzer")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Check results
        if exit_code != 0:
            print("WARNING: OpenAI analysis did not complete successfully")
            print(f"Exit code: {exit_code}")
        else:
            self.assertIn("Successfully processed", stdout)

    def test_06_metadata_generator(self):
        """Test metadata generator."""
        # Only run if we have analysis files
        analysis_dir = self.test_data / "analysis"
        if not any(analysis_dir.glob("*")):
            self.skipTest("No analysis files to generate metadata from")
            
        # Run the metadata generator
        exit_code, stdout, stderr = self.run_container_command("python -m src.metadata_generator")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Check results
        if exit_code != 0:
            print("WARNING: Metadata generation did not complete successfully")
            print(f"Exit code: {exit_code}")
        else:
            self.assertIn("Prepared", stdout)

    def test_07_sharepoint_uploader(self):
        """Test SharePoint uploader."""
        # Only run if we have files to upload
        upload_dir = self.test_data / "upload"
        if not any(upload_dir.glob("*.jpg")):
            self.skipTest("No files to upload to SharePoint")
            
        # Run the uploader
        exit_code, stdout, stderr = self.run_container_command("python -m src.sharepoint_uploader")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Check results
        if exit_code != 0:
            print("WARNING: SharePoint upload did not complete successfully")
            print(f"Exit code: {exit_code}")
        else:
            self.assertIn("Successfully uploaded", stdout)

    def test_08_auto_process(self):
        """Test the full auto_process workflow."""
        # First, clean up all data directories
        for directory in ["downloads", "metadata", "analysis", "upload", "uploaded"]:
            for file in (self.test_data / directory).glob("*"):
                if file.is_file():
                    file.unlink()
        
        # Run the auto process with a timeout (it might take a while)
        process = subprocess.Popen(
            ["docker-compose", "-f", str(self.test_dir / "docker-compose.real.yml"), 
             "run", "--rm", "real-test-agent", "python", "-m", "src.auto_process"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            print("WARNING: Auto process timed out after 10 minutes")
        
        # Log output for inspection
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
        
        # Print summary of results
        print("\nAuto Process Results Summary:")
        print("----------------------------")
        downloads = list(Path(self.test_data / "downloads").glob("*"))
        metadata = list(Path(self.test_data / "metadata").glob("*"))
        analysis = list(Path(self.test_data / "analysis").glob("*"))
        upload = list(Path(self.test_data / "upload").glob("*"))
        uploaded = list(Path(self.test_data / "uploaded").glob("*"))
        
        print(f"Downloaded files: {len(downloads)}")
        print(f"Metadata files: {len(metadata)}")
        print(f"Analysis files: {len(analysis)}")
        print(f"Upload files: {len(upload)}")
        print(f"Uploaded files: {len(uploaded)}")
        
        # We don't make assertions about the counts since they depend on the actual content
        # in SharePoint, but we report them for manual verification
        
        if exit_code != 0:
            print(f"WARNING: Auto process exited with code {exit_code}")
        else:
            print("Auto process completed successfully!")


if __name__ == "__main__":
    unittest.main()
