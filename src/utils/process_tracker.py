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
        logger.info(f"Инициализация ProcessTracker, файл процессов: {self.processes_file}")
        self._load_processes()

    def _load_processes(self):
        """
        Load processes from file.
        """
        if os.path.exists(self.processes_file):
            try:
                with open(self.processes_file, 'r', encoding='utf-8') as f:
                    self.processes = json.load(f)
                logger.info(f"Загружено процессов из файла: {len(self.processes)}")

                # Check if processes are still running
                to_remove = []
                for pid, process_info in self.processes.items():
                    try:
                        if not self._is_process_running(int(pid)):
                            to_remove.append(pid)
                            logger.info(f"Процесс не запущен и будет удален: PID={pid}, name={process_info.get('name')}")
                    except Exception as e:
                        to_remove.append(pid)
                        logger.error(f"Ошибка при проверке процесса: PID={pid}, error={str(e)}")

                # Remove finished processes
                for pid in to_remove:
                    try:
                        self.processes.pop(pid)
                    except Exception as e:
                        logger.error(f"Ошибка при удалении процесса: PID={pid}, error={str(e)}")

                # Save updated processes
                self._save_processes()
            except Exception as e:
                logger.error(f"Ошибка загрузки процессов: {str(e)}")
                self.processes = {}
        else:
            logger.info("Файл процессов не существует, создаем пустой список процессов")
            self.processes = {}
            self._save_processes()

    def _save_processes(self):
        """
        Save processes to file.
        """
        try:
            with open(self.processes_file, 'w', encoding='utf-8') as f:
                json.dump(self.processes, f, indent=4)
            logger.info(f"Сохранено процессов в файл: {len(self.processes)}")
        except Exception as e:
            logger.error(f"Ошибка сохранения процессов: {str(e)}")

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
            is_running = process.is_running()
            logger.debug(f"Проверка процесса: PID={pid}, is_running={is_running}")
            return is_running
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            logger.debug(f"Процесс не существует или недоступен: PID={pid}")
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
            try:
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
                logger.info(f"Добавлен процесс {name} (PID: {pid}) в трекер")
            except Exception as e:
                logger.error(f"Ошибка при добавлении процесса: {name} (PID: {pid}), error={str(e)}")

    def update_process(self, pid, status=None, details=None):
        """
        Update a process in the tracker.

        Args:
            pid (int): Process ID.
            status (str, optional): New process status. Defaults to None.
            details (dict, optional): New process details. Defaults to None.
        """
        with self.lock:
            try:
                pid_str = str(pid)
                if pid_str in self.processes:
                    if status is not None:
                        self.processes[pid_str]["status"] = status
                        logger.info(f"Обновлен статус процесса: PID={pid}, status={status}")

                    if details is not None:
                        if "details" not in self.processes[pid_str]:
                            self.processes[pid_str]["details"] = {}

                        self.processes[pid_str]["details"].update(details)
                        logger.info(f"Обновлены детали процесса: PID={pid}")

                    self.processes[pid_str]["last_updated"] = time.time()
                    self._save_processes()
                    logger.debug(f"Обновлен процесс {self.processes[pid_str]['name']} (PID: {pid})")
                else:
                    logger.warning(f"Процесс не найден при обновлении: PID={pid}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении процесса: PID={pid}, error={str(e)}")

    def remove_process(self, pid):
        """
        Remove a process from the tracker.

        Args:
            pid (int): Process ID.
        """
        with self.lock:
            try:
                pid_str = str(pid)
                if pid_str in self.processes:
                    process_name = self.processes[pid_str].get("name", "Unknown")
                    self.processes.pop(pid_str)
                    self._save_processes()
                    logger.info(f"Удален процесс {process_name} (PID: {pid}) из трекера")
                    return True
                else:
                    logger.warning(f"Процесс не найден при удалении: PID={pid}")
                    return False
            except Exception as e:
                logger.error(f"Ошибка при удалении процесса: PID={pid}, error={str(e)}")
                return False

    def get_process(self, pid):
        """
        Get a process from the tracker.

        Args:
            pid (int): Process ID.

        Returns:
            dict: Process information.
        """
        pid_str = str(pid)
        process = self.processes.get(pid_str)
        if process:
            logger.debug(f"Получен процесс: PID={pid}, name={process.get('name')}")
        else:
            logger.debug(f"Процесс не найден: PID={pid}")
        return process

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
                try:
                    if not self._is_process_running(int(pid)):
                        to_remove.append(pid)
                        logger.info(f"Процесс не запущен и будет помечен как завершенный: PID={pid}, name={process_info.get('name')}")

                        # Update status to "finished"
                        self.processes[pid]["status"] = "finished"
                        self.processes[pid]["last_updated"] = time.time()
                except Exception as e:
                    to_remove.append(pid)
                    logger.error(f"Ошибка при проверке процесса: PID={pid}, error={str(e)}")
                    try:
                        # Update status to "error"
                        self.processes[pid]["status"] = "error"
                        self.processes[pid]["last_updated"] = time.time()
                        if "details" not in self.processes[pid]:
                            self.processes[pid]["details"] = {}
                        self.processes[pid]["details"]["error"] = str(e)
                    except Exception as inner_e:
                        logger.error(f"Ошибка при обновлении статуса процесса: PID={pid}, error={str(inner_e)}")

            # Save updated processes
            if to_remove:
                self._save_processes()

            logger.info(f"Получено всего процессов: {len(self.processes)}")
            return self.processes

    def get_active_processes(self):
        """
        Get active processes from the tracker.

        Returns:
            dict: Active processes.
        """
        active_processes = {}
        try:
            all_processes = self.get_all_processes()

            for pid, process_info in all_processes.items():
                try:
                    if process_info.get("status") in ["running", "starting"]:
                        active_processes[pid] = process_info
                        logger.info(f"Активный процесс: PID={pid}, name={process_info.get('name')}, status={process_info.get('status')}")
                except Exception as e:
                    logger.error(f"Ошибка при обработке процесса: PID={pid}, error={str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при получении активных процессов: {str(e)}")

        logger.info(f"Получено активных процессов: {len(active_processes)}")
        return active_processes

    def get_process_status(self, pid):
        """
        Get the status of a process.

        Args:
            pid (int): Process ID.

        Returns:
            str: Process status.
        """
        try:
            process = self.get_process(pid)
            if process:
                status = process.get("status", "unknown")
                logger.debug(f"Статус процесса: PID={pid}, status={status}")
                return status
            logger.debug(f"Процесс не найден при получении статуса: PID={pid}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении статуса процесса: PID={pid}, error={str(e)}")
            return "error"

    def format_process_info(self, process_info):
        """
        Format process information for display.

        Args:
            process_info (dict): Process information.

        Returns:
            dict: Formatted process information.
        """
        if not process_info:
            return None

        try:
            formatted_info = process_info.copy()

            # Format start time
            start_time = datetime.fromtimestamp(process_info.get("start_time", time.time()))
            formatted_info["start_time_formatted"] = start_time.strftime("%Y-%m-%d %H:%M:%S")

            # Format last updated time
            last_updated = datetime.fromtimestamp(process_info.get("last_updated", time.time()))
            formatted_info["last_updated_formatted"] = last_updated.strftime("%Y-%m-%d %H:%M:%S")

            # Calculate duration
            duration = time.time() - process_info.get("start_time", time.time())
            formatted_info["duration"] = self._format_duration(duration)

            return formatted_info
        except Exception as e:
            logger.error(f"Error formatting process info: {str(e)}")
            # Return a minimal valid process info
            return {
                "pid": process_info.get("pid", 0),
                "name": process_info.get("name", "Unknown"),
                "status": "error",
                "start_time": time.time(),
                "start_time_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": "0s",
                "last_updated": time.time(),
                "last_updated_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": {"error": str(e)}
            }

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
