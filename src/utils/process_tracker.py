"""
Process Tracker Module

This module provides functionality to track running processes.
"""

import os
import time
import json
import threading
import psutil
from datetime import datetime
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager

# Get logger
logger = get_logger('process_tracker')

class ProcessTracker:
    """
    Class for tracking running processes.
    """

    def __init__(self):
        """
        Initialize the process tracker.
        """
        self.processes = {}
        self.lock = threading.Lock()
        self.path_manager = get_path_manager()
        self.processes_file = os.path.join(self.path_manager.config_dir, 'processes.json')
        self._load_processes()

    def _load_processes(self):
        """
        Load processes from file.
        """
        if os.path.exists(self.processes_file):
            try:
                with open(self.processes_file, 'r', encoding='utf-8') as f:
                    self.processes = json.load(f)

                # Check if processes are still running
                to_remove = []
                for pid, process_info in self.processes.items():
                    if not self._is_process_running(int(pid)):
                        to_remove.append(pid)

                # Remove finished processes
                for pid in to_remove:
                    self.processes.pop(pid)

                # Save updated processes
                self._save_processes()
            except Exception as e:
                logger.error(f"Error loading processes: {str(e)}")
                self.processes = {}

    def _save_processes(self):
        """
        Save processes to file.
        """
        try:
            with open(self.processes_file, 'w', encoding='utf-8') as f:
                json.dump(self.processes, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving processes: {str(e)}")

    def _is_process_running(self, pid):
        """
        Check if a process is running.

        Args:
            pid (int): Process ID.

        Returns:
            bool: True if the process is running, False otherwise.
        """
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    def add_process(self, pid, name, start_time=None, status="running", details=None):
        """
        Add a process to the tracker.

        Args:
            pid (int): Process ID.
            name (str): Process name.
            start_time (float, optional): Process start time. Defaults to current time.
            status (str, optional): Process status. Defaults to "running".
            details (dict, optional): Additional process details. Defaults to None.
        """
        with self.lock:
            if start_time is None:
                start_time = time.time()

            self.processes[str(pid)] = {
                "pid": pid,
                "name": name,
                "start_time": start_time,
                "status": status,
                "details": details or {},
                "last_updated": time.time()
            }

            self._save_processes()
            logger.info(f"Added process {name} (PID: {pid}) to tracker")

    def update_process(self, pid, status=None, details=None):
        """
        Update a process in the tracker.

        Args:
            pid (int): Process ID.
            status (str, optional): New process status. Defaults to None.
            details (dict, optional): New process details. Defaults to None.
        """
        with self.lock:
            pid_str = str(pid)
            if pid_str in self.processes:
                if status is not None:
                    self.processes[pid_str]["status"] = status

                if details is not None:
                    if "details" not in self.processes[pid_str]:
                        self.processes[pid_str]["details"] = {}

                    self.processes[pid_str]["details"].update(details)

                self.processes[pid_str]["last_updated"] = time.time()
                self._save_processes()
                logger.debug(f"Updated process {self.processes[pid_str]['name']} (PID: {pid})")

    def remove_process(self, pid):
        """
        Remove a process from the tracker.

        Args:
            pid (int): Process ID.
        """
        with self.lock:
            pid_str = str(pid)
            if pid_str in self.processes:
                process_name = self.processes[pid_str]["name"]
                self.processes.pop(pid_str)
                self._save_processes()
                logger.info(f"Removed process {process_name} (PID: {pid}) from tracker")

    def get_process(self, pid):
        """
        Get a process from the tracker.

        Args:
            pid (int): Process ID.

        Returns:
            dict: Process information.
        """
        pid_str = str(pid)
        return self.processes.get(pid_str)

    def get_all_processes(self):
        """
        Get all processes from the tracker.

        Returns:
            dict: All processes.
        """
        # Check if processes are still running
        with self.lock:
            to_remove = []
            for pid, process_info in self.processes.items():
                if not self._is_process_running(int(pid)):
                    to_remove.append(pid)

                    # Update status to "finished"
                    self.processes[pid]["status"] = "finished"
                    self.processes[pid]["last_updated"] = time.time()

            # Save updated processes
            if to_remove:
                self._save_processes()

            return self.processes

    def get_active_processes(self):
        """
        Get active processes from the tracker.

        Returns:
            dict: Active processes.
        """
        active_processes = {}
        all_processes = self.get_all_processes()

        for pid, process_info in all_processes.items():
            if process_info["status"] in ["running", "starting"]:
                active_processes[pid] = process_info

        return active_processes

    def get_process_status(self, pid):
        """
        Get the status of a process.

        Args:
            pid (int): Process ID.

        Returns:
            str: Process status.
        """
        process = self.get_process(pid)
        if process:
            return process["status"]
        return None

    def format_process_info(self, process_info):
        """
        Format process information for display.

        Args:
            process_info (dict): Process information.

        Returns:
            dict: Formatted process information.
        """
        formatted_info = process_info.copy()

        # Format start time
        start_time = datetime.fromtimestamp(process_info["start_time"])
        formatted_info["start_time_formatted"] = start_time.strftime("%Y-%m-%d %H:%M:%S")

        # Format last updated time
        last_updated = datetime.fromtimestamp(process_info["last_updated"])
        formatted_info["last_updated_formatted"] = last_updated.strftime("%Y-%m-%d %H:%M:%S")

        # Calculate duration
        duration = time.time() - process_info["start_time"]
        formatted_info["duration"] = self._format_duration(duration)

        return formatted_info

    def _format_duration(self, seconds):
        """
        Format duration in seconds to a human-readable string.

        Args:
            seconds (float): Duration in seconds.

        Returns:
            str: Formatted duration.
        """
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

# Singleton instance
_process_tracker = None

def get_process_tracker():
    """
    Get the process tracker instance.

    Returns:
        ProcessTracker: Process tracker instance.
    """
    global _process_tracker
    if _process_tracker is None:
        _process_tracker = ProcessTracker()
    return _process_tracker
