from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import hwmonitor


def _completed(stdout: str, *, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["collector.exe"], returncode, stdout, stderr)


def _payload() -> str:
    return """{
      "timestamp": "2026-08-14T10:00:00",
      "sensors": [
        {"identifier": "/cpu/temperature/0", "hardware_name": "CPU", "hardware_type": "Cpu", "name": "Package", "sensor_type": "Temperature", "value": 50.5},
        {"identifier": "/gpu/load/0", "hardware_name": "GPU", "hardware_type": "GpuNvidia", "name": "Core", "sensor_type": "Load", "value": 16.0}
      ]
    }"""


def _lhm_api():
    return hwmonitor.lhm


def test_collect_snapshot_parses_the_collector_contract():
    snapshot = _lhm_api().collect_snapshot(
        Path("collector.exe"),
        timeout_seconds=10,
        runner=lambda *args, **kwargs: _completed(_payload()),
    )

    assert snapshot.timestamp == datetime(2026, 8, 14, 10, 0)
    assert snapshot.sensors["/cpu/temperature/0"].value == 50.5
    assert snapshot.sensors["/gpu/load/0"].sensor_type == "Load"


def test_collect_snapshot_rejects_nonzero_collector_exit():
    with pytest.raises(_lhm_api().LHMCollectionError, match="exit code 1.*access denied"):
        _lhm_api().collect_snapshot(
            Path("collector.exe"),
            timeout_seconds=10,
            runner=lambda *args, **kwargs: _completed("", returncode=1, stderr="access denied"),
        )


def test_collect_snapshot_reports_a_timeout():
    def timeout_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    with pytest.raises(_lhm_api().LHMCollectionError, match="timed out"):
        _lhm_api().collect_snapshot(Path("collector.exe"), timeout_seconds=10, runner=timeout_runner)


def test_extract_sensor_values_rejects_missing_required_identifier():
    snapshot = _lhm_api().collect_snapshot(
        Path("collector.exe"),
        timeout_seconds=10,
        runner=lambda *args, **kwargs: _completed(_payload()),
    )

    with pytest.raises(_lhm_api().LHMValidationError, match="missing.*gpu_temp_c"):
        _lhm_api().extract_sensor_values(
            snapshot,
            {"cpu_temp_c": "/cpu/temperature/0"},
            required_keys={"cpu_temp_c", "gpu_temp_c"},
        )


def test_collect_snapshot_rejects_invalid_json():
    with pytest.raises(_lhm_api().LHMCollectionError, match="valid JSON"):
        _lhm_api().collect_snapshot(
            Path("collector.exe"),
            timeout_seconds=10,
            runner=lambda *args, **kwargs: _completed("not-json"),
        )
