"""
Main Views Module

This module provides the main views for the web interface.
"""

import os
import subprocess
import time
import json
import threading
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager
from src.utils.registry import get_registry
from src.web.views.photos import allowed_file
from src.utils.process_tracker import get_process_tracker

# Get logger
logger = get_logger('web.main')

# Create blueprint
bp = Blueprint('main', __name__)


def monitor_process(process, pid, script_name):
    """
    Monitor a process and update its status in the process tracker.

    Args:
        process (subprocess.Popen): Process object
        pid (int): Process ID in the tracker
        script_name (str): Name of the script being run
    """
    # Get process tracker
    process_tracker = get_process_tracker()

    try:
        # Simulate progress updates
        start_time = time.time()
        total_time_estimate = 30  # Estimate 30 seconds for completion

        # Create non-blocking I/O streams
        import io
        import select
        import fcntl
        import os

        # Set stdout and stderr to non-blocking mode
        stdout_fd = process.stdout.fileno()
        stderr_fd = process.stderr.fileno()
        fl = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
        fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        fl = fcntl.fcntl(stderr_fd, fcntl.F_GETFL)
        fcntl.fcntl(stderr_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # Buffers for stdout and stderr
        stdout_data = b''
        stderr_data = b''

        # Update progress every second
        while process.poll() is None:
            # Check for new output
            readable, _, _ = select.select([stdout_fd, stderr_fd], [], [], 0.1)

            if stdout_fd in readable:
                chunk = process.stdout.read()
                if chunk:
                    stdout_data += chunk
                    # Log new output
                    for line in chunk.decode('utf-8', errors='replace').splitlines():
                        if line.strip():
                            logger.info(f"{script_name} output: {line}")

            if stderr_fd in readable:
                chunk = process.stderr.read()
                if chunk:
                    stderr_data += chunk
                    # Log new output
                    for line in chunk.decode('utf-8', errors='replace').splitlines():
                        if line.strip():
                            logger.warning(f"{script_name} error: {line}")

            # Calculate progress based on elapsed time
            elapsed = time.time() - start_time
            progress = min(95, int(elapsed / total_time_estimate * 100))

            # Update process status
            process_tracker.update_process(
                pid=pid,
                details={
                    "progress": progress,
                    "progress_message": f"Running {script_name}... ({progress}%)",
                    "elapsed_time": elapsed
                }
            )

            # Sleep for a short time
            time.sleep(1)

        # Process has completed, get any remaining output
        try:
            # Reset file descriptors to blocking mode before communicate
            # This prevents potential resource leaks
            fl_stdout = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
            fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl_stdout & ~os.O_NONBLOCK)
            fl_stderr = fcntl.fcntl(stderr_fd, fcntl.F_GETFL)
            fcntl.fcntl(stderr_fd, fcntl.F_SETFL, fl_stderr & ~os.O_NONBLOCK)

            remaining_stdout, remaining_stderr = process.communicate(timeout=1)
            if remaining_stdout:
                stdout_data += remaining_stdout
            if remaining_stderr:
                stderr_data += remaining_stderr
        except subprocess.TimeoutExpired:
            process.kill()
            remaining_stdout, remaining_stderr = process.communicate()
            if remaining_stdout:
                stdout_data += remaining_stdout
            if remaining_stderr:
                stderr_data += remaining_stderr

        # Decode stdout and stderr
        stdout_text = stdout_data.decode('utf-8', errors='replace')
        stderr_text = stderr_data.decode('utf-8', errors='replace')

        # Check if process completed successfully
        if process.returncode == 0:
            # Update process status to finished
            process_tracker.update_process(
                pid=pid,
                status="finished",
                details={
                    "progress": 100,
                    "progress_message": f"{script_name} completed successfully",
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "elapsed_time": time.time() - start_time
                }
            )
            logger.info(f"Process {script_name} (PID: {pid}) completed successfully")
        else:
            # Update process status to error
            process_tracker.update_process(
                pid=pid,
                status="error",
                details={
                    "progress": 100,
                    "progress_message": f"Error in {script_name}: Return code {process.returncode}",
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "return_code": process.returncode,
                    "elapsed_time": time.time() - start_time
                }
            )
            logger.error(f"Process {script_name} (PID: {pid}) failed with return code {process.returncode}")
    except Exception as e:
        # Update process status to error
        process_tracker.update_process(
            pid=pid,
            status="error",
            details={
                "progress": 100,
                "progress_message": f"Error monitoring {script_name}: {str(e)}",
                "error": str(e)
            }
        )
        logger.error(f"Error monitoring process {script_name} (PID: {pid}): {str(e)}")

@bp.route('/')
def index():
    """Render the dashboard page."""
    # Get statistics
    path_manager = get_path_manager()
    registry = get_registry()

    # Count files in directories
    downloads_count = len(os.listdir(path_manager.downloads_dir))
    analysis_count = len([f for f in os.listdir(path_manager.analysis_dir) if f.endswith('.json')])
    upload_count = len([f for f in os.listdir(path_manager.upload_dir) if not f == 'metadata'])
    uploaded_count = len([f for f in os.listdir(path_manager.uploaded_dir) if not f.endswith('.json') and not f.endswith('.yml')])

    # Get recent activity based on actual files in the system
    recent_activity = []

    # Add files from processed directory
    processed_files = [f for f in os.listdir(path_manager.processed_dir) if allowed_file(f)]
    for filename in processed_files[:5]:
        file_path = os.path.join(path_manager.processed_dir, filename)
        recent_activity.append({
            'type': 'processed',
            'filename': filename,
            'timestamp': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'info': {
                'path': file_path,
                'size': os.path.getsize(file_path)
            }
        })

    # Add files from uploaded directory
    uploaded_files = [f for f in os.listdir(path_manager.uploaded_dir) if allowed_file(f)]
    for filename in uploaded_files[:5]:
        file_path = os.path.join(path_manager.uploaded_dir, filename)
        # Check if metadata exists
        metadata_path = os.path.join(path_manager.uploaded_dir, os.path.splitext(filename)[0] + '.json')
        metadata = None
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata for {filename}: {str(e)}")

        recent_activity.append({
            'type': 'uploaded',
            'filename': filename,
            'timestamp': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'info': {
                'path': file_path,
                'size': os.path.getsize(file_path),
                'metadata': metadata
            }
        })

    # Sort by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
    recent_activity = recent_activity[:10]  # Keep only 10 most recent

    return render_template('main/index.html',
                          downloads_count=downloads_count,
                          analysis_count=analysis_count,
                          upload_count=upload_count,
                          uploaded_count=uploaded_count,
                          processed_count=len(processed_files),
                          uploaded_files_count=len(uploaded_files),
                          recent_activity=recent_activity)

@bp.route('/run/<script>', methods=['POST'])
def run_script(script):
    """Run a script."""
    valid_scripts = {
        'metadata_schema': 'src.metadata_schema',
        'photo_metadata': 'src.photo_metadata',
        'openai_analyzer': 'src.openai_analyzer',
        'metadata_generator': 'src.metadata_generator',
        'sharepoint_uploader': 'src.sharepoint_uploader',
        'auto_process': 'src.auto_process'
    }

    if script not in valid_scripts:
        flash(f"Invalid script: {script}", "danger")
        return redirect(url_for('main.index'))

    try:
        # Run the script in a subprocess
        module = valid_scripts[script]
        process = subprocess.Popen(['python', '-m', module],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

        # Get process tracker
        process_tracker = get_process_tracker()

        # Add process to tracker
        process_tracker.add_process(
            pid=process.pid,
            name=script,
            start_time=time.time(),
            status="running",
            details={
                "module": module,
                "started_by": "web",
                "progress": 0,
                "progress_message": "Starting process..."
            }
        )

        # Get friendly name for the script
        script_names = {
            'metadata_schema': 'Load Metadata Schema',
            'photo_metadata': 'Download Photos',
            'openai_analyzer': 'Analyze Photos with OpenAI',
            'metadata_generator': 'Generate Metadata',
            'sharepoint_uploader': 'Upload to SharePoint',
            'auto_process': 'Full Process'
        }
        friendly_name = script_names.get(script, script)

        # Start a thread to monitor the process
        monitor_thread = threading.Thread(
            target=monitor_process,
            args=(process, process.pid, script),
            daemon=True
        )
        monitor_thread.start()

        # Flash message with link to process details
        flash(f"<strong>{friendly_name}</strong> started! <a href='{url_for('processes.view_process', pid=process.pid)}' class='alert-link'>View progress</a>", "success")
        logger.info(f"Started {script} process via web interface with PID {process.pid}")

        # Redirect to process details page
        return redirect(url_for('processes.view_process', pid=process.pid))
    except Exception as e:
        flash(f"Error running {script}: {str(e)}", "danger")
        logger.error(f"Error running {script}: {str(e)}")
        return redirect(url_for('main.index'))

@bp.route('/status')
def status():
    """Get system status."""
    # Get statistics
    path_manager = get_path_manager()
    registry = get_registry()

    # Count files in directories
    downloads_count = len(os.listdir(path_manager.downloads_dir))
    analysis_count = len([f for f in os.listdir(path_manager.analysis_dir) if f.endswith('.json')])
    upload_count = len([f for f in os.listdir(path_manager.upload_dir) if not f == 'metadata'])
    uploaded_count = len([f for f in os.listdir(path_manager.uploaded_dir) if not f.endswith('.json') and not f.endswith('.yml')])

    # Get registry statistics
    processed_files_list = registry.get_processed_files()
    uploaded_files_list = registry.get_uploaded_files()

    # Check if processes are running
    processes = []
    try:
        # Check for Python processes
        output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq python.exe'], universal_newlines=True)
        processes = [line for line in output.split('\n') if 'python.exe' in line]
    except Exception as e:
        logger.error(f"Error checking processes: {str(e)}")

    return jsonify({
        'downloads_count': downloads_count,
        'analysis_count': analysis_count,
        'upload_count': upload_count,
        'uploaded_count': uploaded_count,
        'processed_count': len(processed_files_list),
        'uploaded_files_count': len(uploaded_files_list),
        'processes': len(processes),
        'timestamp': datetime.now().isoformat()
    })
