from __future__ import annotations

from types import SimpleNamespace

from hwmonitor.system_info import collect_windows_metrics


class FakePsutil:
    def virtual_memory(self):
        return SimpleNamespace(total=16 * 1024**3, used=6 * 1024**3, available=10 * 1024**3, percent=37.5)

    def disk_partitions(self, all=False):
        return [
            SimpleNamespace(mountpoint="C:\\"),
            SimpleNamespace(mountpoint="D:\\"),
            SimpleNamespace(mountpoint="Z:\\"),
        ]

    def disk_usage(self, mountpoint):
        sizes = {
            "C:\\": (500, 300, 200, 60.0),
            "D:\\": (1000, 250, 750, 25.0),
        }
        total, used, free, percent = sizes[mountpoint]
        gib = 1024**3
        return SimpleNamespace(total=total * gib, used=used * gib, free=free * gib, percent=percent)


def test_collects_ram_and_only_fixed_local_drive_letters():
    metrics = collect_windows_metrics(
        psutil_module=FakePsutil(),
        is_fixed_drive=lambda mountpoint: mountpoint in {"C:\\", "D:\\"},
    )

    assert metrics["ram_used_mb"] == 6144.0
    assert metrics["ram_available_mb"] == 10240.0
    assert metrics["ram_used_percent"] == 37.5
    assert metrics["partitions"] == {
        "C:": {"total_gb": 500.0, "used_gb": 300.0, "free_gb": 200.0, "used_percent": 60.0},
        "D:": {"total_gb": 1000.0, "used_gb": 250.0, "free_gb": 750.0, "used_percent": 25.0},
    }
