#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Auto Process Script

This script automatically runs all the necessary scripts in sequence to process photos:
1. metadata_schema.py - Get metadata schema from SharePoint
2. photo_metadata.py - Download photos and extract metadata
3. openai_analyzer.py - Analyze photos with OpenAI
4. metadata_generator.py - Generate metadata for upload
5. sharepoint_uploader.py - Upload photos to SharePoint
"""

import sys
import subprocess
import time

# Import utilities
from src.utils.paths import get_path_manager
from src.utils.config import get_config
from src.utils.logging import get_logger, rotate_logs

# Get logger
logger = get_logger("auto_process")

# Get configuration
config = get_config()

# Get path manager for directories
path_manager = get_path_manager()

def run_script(script_name):
    """
    Run a Python script and return its exit code.

    Args:
        script_name (str): Name of the script to run

    Returns:
        int: Exit code of the script
    """
    logger.info(f"Running {script_name}...")
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, "-m", f"src.{script_name.replace('.py', '')}"],
            check=True,
            capture_output=True,
            text=True
        )

        # Log output
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"{script_name} output: {line}")

        elapsed_time = time.time() - start_time
        logger.info(f"Successfully completed {script_name} in {elapsed_time:.2f} seconds")
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_name}: {str(e)}")
        if e.stdout:
            for line in e.stdout.splitlines():
                logger.info(f"{script_name} output: {line}")
        if e.stderr:
            for line in e.stderr.splitlines():
                logger.error(f"{script_name} error: {line}")
        return e.returncode

def clean_downloads_directory():
    """
    Clean the downloads directory after processing.
    """
    try:
        downloads_dir = path_manager.downloads_dir
        files = list(downloads_dir.glob("*"))

        if files:
            logger.info(f"Cleaning downloads directory: {len(files)} files")
            for file in files:
                if file.is_file():
                    file.unlink()
                    logger.debug(f"Removed file: {file}")
            logger.info("Downloads directory cleaned")
        else:
            logger.info("Downloads directory is already empty")

        return True
    except Exception as e:
        logger.error(f"Error cleaning downloads directory: {str(e)}")
        return False

def main():
    """
    Main function to run all scripts in sequence.
    """
    # Rotate logs to remove old log files
    rotate_logs(max_days=30)

    logger.info("Starting automatic photo processing")

    # List of scripts to run in order
    scripts = [
        "metadata_schema.py",
        "photo_metadata.py",
        "openai_analyzer.py",
        "metadata_generator.py",
        "sharepoint_uploader.py"
    ]

    # Run each script in sequence
    for script in scripts:
        exit_code = run_script(script)
        if exit_code != 0:
            logger.error(f"Script {script} failed with exit code {exit_code}. Stopping process.")
            return exit_code

    # Clean downloads directory after successful processing
    clean_downloads_directory()

    logger.info("All scripts completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
