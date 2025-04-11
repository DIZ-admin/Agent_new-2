#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Process Wrapper Script

This script wraps the execution of other scripts and updates their status in the process tracker.
"""

import sys
import os
import importlib
import time
import traceback

from src.utils.process_tracker import get_process_tracker
from src.utils.logging import get_logger

# Get logger
logger = get_logger("process_wrapper")

def run_module(module_name, pid):
    """
    Run a module and update its status in the process tracker.

    Args:
        module_name (str): Name of the module to run
        pid (int): Process ID to update

    Returns:
        int: Exit code of the module
    """
    logger.info(f"Running module {module_name} with PID {pid}")
    
    # Get process tracker
    process_tracker = get_process_tracker()
    
    # Update process status to running
    process_tracker.update_process(
        pid=pid,
        status="running",
        details={
            "progress": 0,
            "progress_message": f"Starting {module_name}..."
        }
    )
    
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Update progress
        process_tracker.update_process(
            pid=pid,
            details={
                "progress": 10,
                "progress_message": f"Module {module_name} loaded, executing..."
            }
        )
        
        # Run the module's main function if it exists
        if hasattr(module, 'main'):
            result = module.main()
        else:
            # If no main function, assume the module runs on import
            result = 0
        
        # Update process status to finished
        process_tracker.update_process(
            pid=pid,
            status="finished",
            details={
                "progress": 100,
                "progress_message": f"Module {module_name} completed successfully",
                "result": result
            }
        )
        
        logger.info(f"Module {module_name} completed successfully")
        return 0
    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()
        
        # Update process status to error
        process_tracker.update_process(
            pid=pid,
            status="error",
            details={
                "progress": 100,
                "progress_message": f"Error in {module_name}: {error_message}",
                "error": error_message,
                "stack_trace": stack_trace
            }
        )
        
        logger.error(f"Error running module {module_name}: {error_message}")
        logger.debug(f"Stack trace: {stack_trace}")
        return 1

def main():
    """
    Main function to run a module and update its status.
    """
    if len(sys.argv) < 3:
        print("Usage: python -m src.process_wrapper <module_name> <pid>")
        return 1
    
    module_name = sys.argv[1]
    pid = int(sys.argv[2])
    
    return run_module(module_name, pid)

if __name__ == "__main__":
    sys.exit(main())
