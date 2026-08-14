from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import run_monitor


class FakeMutex:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _config(tmp_path):
    return SimpleNamespace(
        ERROR_LOG_DIRECTORY=tmp_path / "errors",
        LHM_COLLECTOR_EXECUTABLE=tmp_path / "LibreHardwareMonitorCollector.exe",
        LHM_COLLECTOR_TIMEOUT_SECONDS=10,
        SENSOR_MAP={
            "gpu_temp_c": "/gpu/temperature/0",
            "gpu_hotspot_temp_c": "/gpu/temperature/2",
            "nvme_adata_temp_c": "/nvme/temperature/0",
            "cpu_usage_percent": "/cpu/load/0",
            "gpu_usage_percent": "/gpu/load/0",
        },
        REQUIRED_SENSOR_KEYS={
            "gpu_temp_c",
            "cpu_usage_percent",
            "gpu_usage_percent",
        },
        DAILY_LOG_DIRECTORY=tmp_path / "daily",
        SMTP_SENDER="sender@example.com",
        SMTP_RECIPIENTS=["recipient@example.com"],
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=465,
        SMTP_APP_PASSWORD="secret",
        SMTP_TIMEOUT_SECONDS=5,
        DISPLAY_LABELS={},
    )


def test_successful_lhm_run_appends_a_new_lhm_daily_record(tmp_path, monkeypatch):
    config = _config(tmp_path)
    snapshot = SimpleNamespace(timestamp=datetime(2026, 8, 14, 10, 0))
    monkeypatch.setitem(sys.modules, "config", config)
    monkeypatch.setattr(run_monitor, "WindowsMutex", FakeMutex)
    monkeypatch.setattr(run_monitor, "collect_snapshot", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        run_monitor,
        "extract_sensor_values",
        lambda *args, **kwargs: {
            "gpu_temp_c": 51.0,
            "gpu_hotspot_temp_c": 63.0,
            "nvme_adata_temp_c": 41.0,
            "cpu_usage_percent": 10.0,
            "gpu_usage_percent": 16.0,
        },
    )
    monkeypatch.setattr(
        run_monitor,
        "collect_windows_metrics",
        lambda: {"ram_used_mb": 1000.0, "ram_available_mb": 2000.0, "ram_used_percent": 33.3, "partitions": {}},
    )
    monkeypatch.setattr(run_monitor, "build_report_message", lambda **kwargs: object())
    monkeypatch.setattr(run_monitor, "send_gmail_report", lambda *args, **kwargs: None)

    assert run_monitor.main() == 0
    daily_path = tmp_path / "daily" / "lhm_20260814.csv"
    with daily_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["gpu_hotspot_temp_c"] == "63.0"
    assert rows[0]["nvme_adata_temp_c"] == "41.0"


def test_smtp_failure_does_not_append_an_lhm_daily_record(tmp_path, monkeypatch):
    config = _config(tmp_path)
    snapshot = SimpleNamespace(timestamp=datetime(2026, 8, 14, 10, 0))
    monkeypatch.setitem(sys.modules, "config", config)
    monkeypatch.setattr(run_monitor, "WindowsMutex", FakeMutex)
    monkeypatch.setattr(run_monitor, "collect_snapshot", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        run_monitor,
        "extract_sensor_values",
        lambda *args, **kwargs: {
            "gpu_temp_c": 51.0,
            "cpu_usage_percent": 10.0,
            "gpu_usage_percent": 16.0,
        },
    )
    monkeypatch.setattr(
        run_monitor,
        "collect_windows_metrics",
        lambda: {"ram_used_mb": 1000.0, "ram_available_mb": 2000.0, "ram_used_percent": 33.3, "partitions": {}},
    )
    monkeypatch.setattr(run_monitor, "build_report_message", lambda **kwargs: object())
    monkeypatch.setattr(run_monitor, "send_gmail_report", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")))

    assert run_monitor.main() == 1
    assert not (tmp_path / "daily" / "lhm_20260814.csv").exists()
