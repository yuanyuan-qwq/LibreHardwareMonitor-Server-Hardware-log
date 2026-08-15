"""Collect local Windows memory and fixed-drive capacity information."""

from __future__ import annotations

import ctypes
from typing import Callable

import psutil


GIB = 1024**3
MIB = 1024**2


def collect_windows_metrics(
    *,
    psutil_module=psutil,
    is_fixed_drive: Callable[[str], bool] | None = None,
) -> dict[str, object]:
    """Return RAM information plus accessible Windows fixed drive capacities."""
    is_fixed_drive = is_fixed_drive or _is_fixed_drive
    memory = psutil_module.virtual_memory()
    partitions: dict[str, dict[str, float]] = {}
    for partition in psutil_module.disk_partitions(all=False):
        mountpoint = partition.mountpoint
        if not is_fixed_drive(mountpoint):
            continue
        try:
            usage = psutil_module.disk_usage(mountpoint)
        except OSError:
            continue
        partitions[mountpoint.rstrip("\\/")] = {
            "total_gb": round(usage.total / GIB, 2),
            "used_gb": round(usage.used / GIB, 2),
            "free_gb": round(usage.free / GIB, 2),
            "used_percent": float(usage.percent),
        }
    return {
        "ram_used_mb": round(memory.used / MIB, 2),
        "ram_available_mb": round(memory.available / MIB, 2),
        "ram_used_percent": float(memory.percent),
        "partitions": partitions,
    }


def _is_fixed_drive(mountpoint: str) -> bool:
    """Return whether a drive letter is a Windows fixed local volume."""
    if len(mountpoint) < 2 or mountpoint[1] != ":":
        return False
    return ctypes.windll.kernel32.GetDriveTypeW(mountpoint) == 3
