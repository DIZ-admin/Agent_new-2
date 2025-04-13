"""
Process Monitor Module

This module provides process monitoring functionality for the web interface.
"""

import os
import time
import select
import fcntl
import signal
import subprocess
import threading
from src.utils.logging import get_logger
from src.web.exceptions import ProcessExecutionError, TimeoutError

# Get logger
logger = get_logger('web.process_monitor')


class ProcessMonitor:
    """
    Process Monitor class for tracking and reporting process status.
    """
    
    def __init__(self, process, process_tracker, pid, script_name):
        """
        Initialize the process monitor.
        
        Args:
            process (subprocess.Popen): Process object
            process_tracker: Process tracker instance
            pid (int): Process ID
            script_name (str): Name of the script
        """
        self.process = process
        self.process_tracker = process_tracker
        self.pid = pid
        self.script_name = script_name
        self.start_time = time.time()
        self.stdout_data = b''
        self.stderr_data = b''
        self.total_time_estimate = 30  # Estimate time in seconds
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.RLock()
    
    def setup_nonblocking_io(self):
        """
        Set up non-blocking I/O for process stdout and stderr.
        
        Returns:
            tuple: (stdout_fd, stderr_fd)
        """
        with self.lock:
            stdout_fd = self.process.stdout.fileno()
            stderr_fd = self.process.stderr.fileno()
            
            # Set stdout to non-blocking mode
            fl = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
            fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            # Set stderr to non-blocking mode
            fl = fcntl.fcntl(stderr_fd, fcntl.F_GETFL)
            fcntl.fcntl(stderr_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            return stdout_fd, stderr_fd
            
    def poll_output(self, timeout=0.1):
        """
        Poll process output without blocking.
        
        Args:
            timeout (float): Select timeout in seconds
            
        Returns:
            tuple: (has_new_data, is_alive)
        """
        with self.lock:
            if self.process.poll() is not None:
                return False, False
                
            stdout_fd = self.process.stdout.fileno()
            stderr_fd = self.process.stderr.fileno()
            
            readable, _, _ = select.select([stdout_fd, stderr_fd], [], [], timeout)
            
            has_new_data = False
            
            if stdout_fd in readable:
                chunk = self.process.stdout.read()
                if chunk:
                    self.stdout_data += chunk
                    has_new_data = True
                    
                    # Log new output
                    lines = chunk.decode('utf-8', errors='replace').splitlines()
                    for line in lines:
                        if line.strip():
                            logger.info(f"{self.script_name} output: {line}")
                    
            if stderr_fd in readable:
                chunk = self.process.stderr.read()
                if chunk:
                    self.stderr_data += chunk
                    has_new_data = True
                    
                    # Log new output
                    lines = chunk.decode('utf-8', errors='replace').splitlines()
                    for line in lines:
                        if line.strip():
                            logger.warning(f"{self.script_name} error: {line}")
                    
            return has_new_data, True
            
    def update_progress(self, progress, message=None):
        """
        Update progress in the process tracker.
        
        Args:
            progress (int): Progress percentage (0-100)
            message (str, optional): Progress message
            
        Returns:
            None
        """
        with self.lock:
            elapsed = time.time() - self.start_time
            
            details = {
                "progress": progress,
                "elapsed_time": elapsed
            }
            
            if message:
                details["progress_message"] = message
            else:
                details["progress_message"] = f"Running {self.script_name}... ({progress}%)"
                
            self.process_tracker.update_process(
                pid=self.pid,
                details=details
            )
    
    def reset_to_blocking(self):
        """
        Reset file descriptors to blocking mode.
        
        Returns:
            None
        """
        with self.lock:
            if not self.process:
                return
                
            try:
                stdout_fd = self.process.stdout.fileno()
                stderr_fd = self.process.stderr.fileno()
                
                # Reset stdout to blocking mode
                fl_stdout = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
                fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl_stdout & ~os.O_NONBLOCK)
                
                # Reset stderr to blocking mode
                fl_stderr = fcntl.fcntl(stderr_fd, fcntl.F_GETFL)
                fcntl.fcntl(stderr_fd, fcntl.F_SETFL, fl_stderr & ~os.O_NONBLOCK)
            except Exception as e:
                logger.error(f"Error resetting to blocking mode: {str(e)}")
                
    def get_remaining_output(self, timeout=1):
        """
        Get any remaining output from the process.
        
        Args:
            timeout (int): Timeout in seconds
            
        Returns:
            tuple: (stdout_text, stderr_text)
        """
        with self.lock:
            try:
                # Reset to blocking mode before communicate
                self.reset_to_blocking()
                
                # Get remaining output with timeout
                remaining_stdout, remaining_stderr = self.process.communicate(timeout=timeout)
                
                if remaining_stdout:
                    self.stdout_data += remaining_stdout
                    
                if remaining_stderr:
                    self.stderr_data += remaining_stderr
            except subprocess.TimeoutExpired:
                # Kill the process if communicate times out
                self.process.kill()
                remaining_stdout, remaining_stderr = self.process.communicate()
                
                if remaining_stdout:
                    self.stdout_data += remaining_stdout
                    
                if remaining_stderr:
                    self.stderr_data += remaining_stderr
            except Exception as e:
                logger.error(f"Error getting remaining output: {str(e)}")
                
            # Decode stdout and stderr
            stdout_text = self.stdout_data.decode('utf-8', errors='replace')
            stderr_text = self.stderr_data.decode('utf-8', errors='replace')
            
            return stdout_text, stderr_text
            
    def monitor(self):
        """
        Monitor the process and update its status.
        
        This method should be called in a separate thread.
        
        Returns:
            None
        """
        self.is_monitoring = True
        
        try:
            # Set up non-blocking I/O
            self.setup_nonblocking_io()
            
            # Monitor the process
            while self.process.poll() is None and self.is_monitoring:
                # Poll for new output
                _, _ = self.poll_output()
                
                # Calculate progress based on elapsed time
                elapsed = time.time() - self.start_time
                progress = min(95, int(elapsed / self.total_time_estimate * 100))
                
                # Update progress
                self.update_progress(progress)
                
                # Sleep for a short time
                time.sleep(1)
                
            # Process has completed or monitoring stopped
            if not self.is_monitoring:
                logger.info(f"Monitoring stopped for process {self.script_name} (PID: {self.pid})")
                return
                
            # Get remaining output
            stdout_text, stderr_text = self.get_remaining_output()
            
            # Check if process completed successfully
            if self.process.returncode == 0:
                # Update process status to finished
                self.process_tracker.update_process(
                    pid=self.pid,
                    status="finished",
                    details={
                        "progress": 100,
                        "progress_message": f"{self.script_name} completed successfully",
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "elapsed_time": time.time() - self.start_time
                    }
                )
                logger.info(f"Process {self.script_name} (PID: {self.pid}) completed successfully")
            else:
                # Update process status to error
                self.process_tracker.update_process(
                    pid=self.pid,
                    status="error",
                    details={
                        "progress": 100,
                        "progress_message": f"Error in {self.script_name}: Return code {self.process.returncode}",
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "return_code": self.process.returncode,
                        "elapsed_time": time.time() - self.start_time
                    }
                )
                logger.error(f"Process {self.script_name} (PID: {self.pid}) failed with return code {self.process.returncode}")
        except Exception as e:
            # Update process status to error
            self.process_tracker.update_process(
                pid=self.pid,
                status="error",
                details={
                    "progress": 100,
                    "progress_message": f"Error monitoring {self.script_name}: {str(e)}",
                    "error": str(e)
                }
            )
            logger.error(f"Error monitoring process {self.script_name} (PID: {self.pid}): {str(e)}")
        finally:
            self.is_monitoring = False
            
    def start_monitoring(self):
        """
        Start monitoring the process in a separate thread.
        
        Returns:
            ProcessMonitor: Self for chaining
        """
        if self.is_monitoring:
            logger.warning(f"Process {self.script_name} (PID: {self.pid}) is already being monitored")
            return self
            
        # Create and start the monitor thread
        self.monitor_thread = threading.Thread(
            target=self.monitor,
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info(f"Started monitoring process {self.script_name} (PID: {self.pid})")
        
        return self
        
    def stop_monitoring(self):
        """
        Stop monitoring the process.
        
        Returns:
            None
        """
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            # Wait for the monitor thread to complete
            self.monitor_thread.join(timeout=2)
            
        logger.info(f"Stopped monitoring process {self.script_name} (PID: {self.pid})")
        
    def kill_process(self):
        """
        Kill the process.
        
        Returns:
            bool: True if process was killed, False otherwise
        """
        if not self.process:
            return False
            
        try:
            # Stop monitoring first
            self.stop_monitoring()
            
            # Check if process is still running
            if self.process.poll() is None:
                # Try to terminate gracefully first
                self.process.terminate()
                
                # Wait for a short time
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Force kill if terminate doesn't work
                    self.process.kill()
                    self.process.wait()
                    
                logger.info(f"Killed process {self.script_name} (PID: {self.pid})")
                
                # Update process status to killed
                self.process_tracker.update_process(
                    pid=self.pid,
                    status="killed",
                    details={
                        "progress": 100,
                        "progress_message": f"{self.script_name} was killed",
                        "elapsed_time": time.time() - self.start_time
                    }
                )
                
                return True
            else:
                logger.info(f"Process {self.script_name} (PID: {self.pid}) already completed")
                return False
        except Exception as e:
            logger.error(f"Error killing process {self.script_name} (PID: {self.pid}): {str(e)}")
            return False


def run_process(command, process_tracker, script_name, shell=False):
    """
    Run a process and monitor it.
    
    Args:
        command (list or str): Command to run
        process_tracker: Process tracker instance
        script_name (str): Name of the script
        shell (bool): Whether to run command in shell
        
    Returns:
        tuple: (process, monitor)
        
    Raises:
        ProcessExecutionError: If process fails to start
    """
    try:
        # Start the process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=False,
            bufsize=1
        )
        
        # Add process to tracker
        process_tracker.add_process(
            pid=process.pid,
            name=script_name,
            start_time=time.time(),
            status="running",
            details={
                "command": command,
                "started_by": "web",
                "progress": 0,
                "progress_message": "Starting process..."
            }
        )
        
        # Create and start monitor
        monitor = ProcessMonitor(process, process_tracker, process.pid, script_name)
        monitor.start_monitoring()
        
        logger.info(f"Started process {script_name} with PID {process.pid}")
        
        return process, monitor
    except Exception as e:
        raise ProcessExecutionError(f"Failed to start process {script_name}: {str(e)}")
