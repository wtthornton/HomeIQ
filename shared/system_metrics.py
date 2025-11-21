"""
System Resource Metrics Collection
"""

import asyncio
import contextlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil

from .metrics_collector import MetricPoint, MetricsCollector


@dataclass
class SystemResourceMetrics:
    """System resource metrics data structure"""
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    memory_percent: float
    memory_used_bytes: int
    memory_total_bytes: int
    disk_percent: float
    disk_used_bytes: int
    disk_total_bytes: int
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: tuple | None = None


@dataclass
class ProcessMetrics:
    """Process-specific metrics data structure"""
    timestamp: datetime
    pid: int
    cpu_percent: float
    memory_rss: int
    memory_vms: int
    memory_percent: float
    num_threads: int
    num_fds: int | None = None
    create_time: float = 0.0


class SystemMetricsCollector:
    """System-wide resource metrics collection"""

    def __init__(self, metrics_collector: MetricsCollector | None = None):
        self.metrics_collector = metrics_collector
        self._running = False
        self._collection_task: asyncio.Task | None = None
        self.collection_interval = 30  # seconds

        # Previous network stats for calculating rates
        self._prev_network_stats = None
        self._prev_network_time = None

    async def start(self):
        """Start system metrics collection"""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())

    async def stop(self):
        """Stop system metrics collection"""
        if not self._running:
            return

        self._running = False

        if self._collection_task:
            self._collection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._collection_task

    async def _collection_loop(self):
        """Main collection loop"""
        while self._running:
            try:
                await self._collect_system_metrics()
                await self._collect_process_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in system metrics collection: {e}")

    async def _collect_system_metrics(self):
        """Collect system-wide resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_io = psutil.disk_io_counters()

            # Network metrics
            network = psutil.net_io_counters()

            # Load average (Unix only)
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = None

            # Calculate network rates
            network_send_rate = 0
            network_recv_rate = 0
            current_time = time.time()

            if self._prev_network_stats and self._prev_network_time:
                time_diff = current_time - self._prev_network_time
                if time_diff > 0:
                    network_send_rate = (network.bytes_sent - self._prev_network_stats.bytes_sent) / time_diff
                    network_recv_rate = (network.bytes_recv - self._prev_network_stats.bytes_recv) / time_diff

            self._prev_network_stats = network
            self._prev_network_time = current_time

            # Create metrics point
            if self.metrics_collector:
                point = MetricPoint(
                    measurement="system_resources",
                    tags={"host": psutil.uname().node},
                    fields={
                        "cpu_percent": cpu_percent,
                        "cpu_count": cpu_count,
                        "cpu_count_logical": cpu_count_logical,
                        "memory_percent": memory.percent,
                        "memory_used_bytes": memory.used,
                        "memory_total_bytes": memory.total,
                        "memory_available_bytes": memory.available,
                        "swap_percent": swap.percent,
                        "swap_used_bytes": swap.used,
                        "swap_total_bytes": swap.total,
                        "disk_percent": disk.percent,
                        "disk_used_bytes": disk.used,
                        "disk_total_bytes": disk.total,
                        "disk_free_bytes": disk.free,
                        "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
                        "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
                        "network_bytes_sent": network.bytes_sent,
                        "network_bytes_recv": network.bytes_recv,
                        "network_send_rate": network_send_rate,
                        "network_recv_rate": network_recv_rate,
                        "load_avg_1min": load_avg[0] if load_avg else 0,
                        "load_avg_5min": load_avg[1] if load_avg else 0,
                        "load_avg_15min": load_avg[2] if load_avg else 0,
                    },
                    timestamp=datetime.utcnow(),
                    service="system",
                )

                self.metrics_collector._add_to_buffer(point)

        except Exception as e:
            print(f"Error collecting system metrics: {e}")

    async def _collect_process_metrics(self):
        """Collect process-specific metrics"""
        try:
            # Get current process
            process = psutil.Process()

            # CPU and memory
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # Thread and file descriptor counts
            num_threads = process.num_threads()
            try:
                num_fds = process.num_fds()
            except (AttributeError, psutil.AccessDenied):
                num_fds = None

            # Process creation time
            create_time = process.create_time()

            # Create metrics point
            if self.metrics_collector:
                point = MetricPoint(
                    measurement="process_resources",
                    tags={
                        "host": psutil.uname().node,
                        "pid": str(process.pid),
                        "name": process.name(),
                    },
                    fields={
                        "cpu_percent": cpu_percent,
                        "memory_rss": memory_info.rss,
                        "memory_vms": memory_info.vms,
                        "memory_percent": memory_percent,
                        "num_threads": num_threads,
                        "num_fds": num_fds or 0,
                        "create_time": create_time,
                    },
                    timestamp=datetime.utcnow(),
                    service="process",
                )

                self.metrics_collector._add_to_buffer(point)

        except Exception as e:
            print(f"Error collecting process metrics: {e}")

    def get_current_metrics(self) -> dict[str, Any]:
        """Get current system metrics snapshot"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent()
            cpu_count = psutil.cpu_count()

            # Memory
            memory = psutil.virtual_memory()

            # Disk
            disk = psutil.disk_usage("/")

            # Network
            network = psutil.net_io_counters()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                },
                "memory": {
                    "percent": memory.percent,
                    "used_bytes": memory.used,
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                },
                "disk": {
                    "percent": disk.percent,
                    "used_bytes": disk.used,
                    "total_bytes": disk.total,
                    "free_bytes": disk.free,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                },
            }
        except Exception as e:
            return {"error": str(e)}


class ContainerMetricsCollector:
    """Docker container metrics collection"""

    def __init__(self, metrics_collector: MetricsCollector | None = None):
        self.metrics_collector = metrics_collector
        self._running = False
        self._collection_task: asyncio.Task | None = None
        self.collection_interval = 30  # seconds

    async def start(self):
        """Start container metrics collection"""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())

    async def stop(self):
        """Stop container metrics collection"""
        if not self._running:
            return

        self._running = False

        if self._collection_task:
            self._collection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._collection_task

    async def _collection_loop(self):
        """Main collection loop"""
        while self._running:
            try:
                await self._collect_container_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in container metrics collection: {e}")

    async def _collect_container_metrics(self):
        """Collect Docker container metrics"""
        try:
            # Get all processes
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    # Check if this is a Docker container process
                    cmdline = proc.info["cmdline"]
                    if cmdline and any("docker" in str(arg).lower() for arg in cmdline):
                        # This is a simplified check - in production you'd use Docker API
                        container_name = self._extract_container_name(cmdline)

                        if container_name:
                            await self._collect_single_container_metrics(proc, container_name)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            print(f"Error collecting container metrics: {e}")

    def _extract_container_name(self, cmdline: list) -> str | None:
        """Extract container name from command line"""
        # This is a simplified implementation
        # In production, you'd parse Docker command line arguments properly
        for arg in cmdline:
            if "homeiq" in str(arg):
                return "homeiq-container"
        return None

    async def _collect_single_container_metrics(self, proc: psutil.Process, container_name: str):
        """Collect metrics for a single container"""
        try:
            # Get process metrics
            cpu_percent = proc.cpu_percent()
            memory_info = proc.memory_info()
            memory_percent = proc.memory_percent()

            # Create metrics point
            if self.metrics_collector:
                point = MetricPoint(
                    measurement="container_resources",
                    tags={
                        "container_name": container_name,
                        "pid": str(proc.pid),
                    },
                    fields={
                        "cpu_percent": cpu_percent,
                        "memory_rss": memory_info.rss,
                        "memory_vms": memory_info.vms,
                        "memory_percent": memory_percent,
                    },
                    timestamp=datetime.utcnow(),
                    service="container",
                )

                self.metrics_collector._add_to_buffer(point)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            print(f"Error collecting container metrics for {container_name}: {e}")


# Utility functions
def get_system_info() -> dict[str, Any]:
    """Get basic system information"""
    try:
        uname = psutil.uname()
        boot_time = psutil.boot_time()

        return {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
        }
    except Exception as e:
        return {"error": str(e)}


def get_memory_info() -> dict[str, Any]:
    """Get detailed memory information"""
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "virtual": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
            },
        }
    except Exception as e:
        return {"error": str(e)}


def get_disk_info() -> dict[str, Any]:
    """Get disk usage information"""
    try:
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()

        return {
            "usage": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
            "io": {
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0,
            },
        }
    except Exception as e:
        return {"error": str(e)}


def get_network_info() -> dict[str, Any]:
    """Get network interface information"""
    try:
        network = psutil.net_io_counters()
        interfaces = psutil.net_if_addrs()

        return {
            "io": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
            "interfaces": {
                name: [
                    {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    }
                    for addr in addrs
                ]
                for name, addrs in interfaces.items()
            },
        }
    except Exception as e:
        return {"error": str(e)}
