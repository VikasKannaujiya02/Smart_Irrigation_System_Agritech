"""Health Monitor and System Diagnostics for AI Smart Irrigation System."""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace

try:
    import psutil
except ImportError:
    class _PsutilFallback:
        @staticmethod
        def cpu_percent(interval: float | None = None) -> float:
            if interval:
                time.sleep(interval)
            try:
                load_avg = os.getloadavg()[0]
                cpu_count = os.cpu_count() or 1
                return min(100.0, max(0.0, (load_avg / cpu_count) * 100.0))
            except (AttributeError, OSError):
                return 0.0

        @staticmethod
        def virtual_memory() -> SimpleNamespace:
            return SimpleNamespace(percent=0.0, used=0, total=0)

        @staticmethod
        def disk_usage(path: str) -> SimpleNamespace:
            usage = shutil.disk_usage(path)
            percent = (usage.used / usage.total * 100.0) if usage.total else 0.0
            return SimpleNamespace(percent=percent, used=usage.used, total=usage.total)

    psutil = _PsutilFallback()

from ..configuration_manager import config_manager
from ..database.connection import SQLiteConnectionPool

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    uptime_seconds: float
    timestamp: str


@dataclass
class HealthCheckResult:
    status: HealthStatus
    timestamp: str
    checks: Dict[str, Dict[str, Any]]


class HealthMonitor:
    def __init__(self):
        self.config = config_manager.get_config()
        self.start_time = time.time()
        self.db_path = Path(__file__).parent.parent.parent / self.config.database.sqlite_path

    def collect_metrics(self) -> SystemMetrics:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(self.db_path.parent.parent)).percent
        uptime = time.time() - self.start_time

        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            disk_usage_percent=disk,
            uptime_seconds=uptime,
            timestamp=datetime.now().isoformat()
        )

    def check_health(self) -> HealthCheckResult:
        checks = {}
        overall_status = HealthStatus.HEALTHY

        # CPU check
        cpu = psutil.cpu_percent(interval=0.1)
        cpu_status = HealthStatus.HEALTHY
        if cpu > 90:
            cpu_status = HealthStatus.UNHEALTHY
            overall_status = HealthStatus.UNHEALTHY
        elif cpu > 70:
            cpu_status = HealthStatus.WARNING
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        checks["cpu"] = {
            "status": cpu_status.value,
            "percent": cpu
        }

        # Memory check
        memory = psutil.virtual_memory()
        mem_status = HealthStatus.HEALTHY
        if memory.percent > 90:
            mem_status = HealthStatus.UNHEALTHY
            overall_status = HealthStatus.UNHEALTHY
        elif memory.percent > 75:
            mem_status = HealthStatus.WARNING
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        checks["memory"] = {
            "status": mem_status.value,
            "percent": memory.percent,
            "used_mb": memory.used // (1024 * 1024),
            "total_mb": memory.total // (1024 * 1024)
        }

        # Disk check
        disk = psutil.disk_usage(str(self.db_path.parent.parent))
        disk_status = HealthStatus.HEALTHY
        if disk.percent > 95:
            disk_status = HealthStatus.UNHEALTHY
            overall_status = HealthStatus.UNHEALTHY
        elif disk.percent > 80:
            disk_status = HealthStatus.WARNING
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        checks["disk"] = {
            "status": disk_status.value,
            "percent": disk.percent,
            "used_gb": disk.used // (1024 * 1024 * 1024),
            "total_gb": disk.total // (1024 * 1024 * 1024)
        }

        # Database check
        db_ok = self._check_database()
        db_status = HealthStatus.HEALTHY if db_ok else HealthStatus.UNHEALTHY
        if not db_ok:
            overall_status = HealthStatus.UNHEALTHY
        checks["database"] = {
            "status": db_status.value,
            "ok": db_ok
        }

        return HealthCheckResult(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            checks=checks
        )

    def _check_database(self) -> bool:
        try:
            pool = SQLiteConnectionPool(self.db_path)
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_diagnostics(self) -> Dict[str, Any]:
        metrics = self.collect_metrics()
        health = self.check_health()

        return {
            "system_metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_usage_percent": metrics.disk_usage_percent,
                "uptime_seconds": metrics.uptime_seconds
            },
            "health": {
                "status": health.status.value,
                "checks": health.checks
            },
            "environment": {
                "project_name": self.config.project_name,
                "environment": self.config.environment.value
            },
            "timestamp": datetime.now().isoformat()
        }
