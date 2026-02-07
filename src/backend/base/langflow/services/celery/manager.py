"""Celery Worker Manager - 管理 Celery worker 生命周期."""

import os
import subprocess
import sys
from pathlib import Path

import psutil

from langflow.logging.logger import logger


class CeleryWorkerManager:
    """管理 Celery worker 进程的启动和停止."""

    def __init__(self):
        self.celery_process: subprocess.Popen | None = None

    def stop_existing_celery_workers(self) -> int:
        """停止所有现有的 Celery worker 进程.

        Returns:
            int: 停止的 worker 数量

        """
        stopped_count = 0

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and any(
                    "celery" in str(arg) and "langflow.core.celery_app" in str(arg) for arg in cmdline
                ):
                    logger.info(f"Stopping existing Celery worker (PID: {proc.info['pid']})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        stopped_count += 1
                    except psutil.TimeoutExpired:
                        logger.warning(f"Celery worker (PID: {proc.info['pid']}) didn't stop gracefully, killing it")
                        proc.kill()
                        stopped_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if stopped_count > 0:
            logger.info(f"Stopped {stopped_count} existing Celery worker(s)")

        return stopped_count

    def start_celery_worker(self) -> bool:
        """启动 Celery worker 进程.

        Returns:
            bool: 启动是否成功

        """
        # Redis 配置
        redis_host = os.environ.get("LANGFLOW_REDIS_HOST", "192.168.110.185")
        redis_port = os.environ.get("LANGFLOW_REDIS_PORT", "6379")
        redis_password = os.environ.get("LANGFLOW_REDIS_PASSWORD", "ImagDev@123")

        # 设置环境变量
        env = os.environ.copy()
        env["LANGFLOW_REDIS_HOST"] = redis_host
        env["LANGFLOW_REDIS_PORT"] = redis_port
        env["LANGFLOW_REDIS_PASSWORD"] = redis_password

        # Python 可执行文件路径
        python_exe = str(Path(".venv/bin/python").absolute()) if Path(".venv/bin/python").exists() else sys.executable

        # 日志文件路径
        log_file_path = Path("celery_worker.log").absolute()

        # Celery 命令
        celery_cmd = [
            python_exe,
            "-m",
            "celery",
            "-A",
            "langflow.core.celery_app",
            "worker",
            "--loglevel=info",
            f"--logfile={log_file_path}",
            "--pidfile=",  # 禁用 pidfile
        ]

        logger.info(f"Starting Celery worker with Redis at {redis_host}:{redis_port}")
        logger.info(f"Celery logs will be written to: {log_file_path}")

        try:
            self.celery_process = subprocess.Popen(celery_cmd, env=env, cwd=Path.cwd())  # noqa: S603
            logger.info(f"Celery worker started (PID: {self.celery_process.pid})")
        except OSError as e:
            logger.error(f"Failed to start Celery worker: {e}")
            return False
        else:
            return True

    def stop_celery_worker(self) -> None:
        """停止当前管理的 Celery worker 进程."""
        if self.celery_process is not None:
            try:
                logger.info(f"Stopping Celery worker (PID: {self.celery_process.pid})")
                self.celery_process.terminate()
                try:
                    self.celery_process.wait(timeout=5)
                    logger.info("Celery worker stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("Celery worker didn't stop gracefully, killing it")
                    self.celery_process.kill()
                    self.celery_process.wait()
                    logger.info("Celery worker killed")
            except OSError as e:
                logger.error(f"Error stopping Celery worker: {e}")
            finally:
                self.celery_process = None


# 全局单例实例
_celery_manager: CeleryWorkerManager | None = None


def get_celery_manager() -> CeleryWorkerManager:
    """获取 Celery manager 单例实例."""
    global _celery_manager  # noqa: PLW0603
    if _celery_manager is None:
        _celery_manager = CeleryWorkerManager()
    return _celery_manager
