"""Run the LibreHardwareMonitor collector and validate its JSON snapshot."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping


class LHMCollectionError(RuntimeError):
    """Raised when the external collector cannot provide a valid snapshot."""


class LHMValidationError(LHMCollectionError):
    """Raised when configured sensor values cannot be used in a report."""


@dataclass(frozen=True)
class LHMSensor:
    identifier: str
    hardware_name: str
    hardware_type: str
    name: str
    sensor_type: str
    value: float


@dataclass(frozen=True)
class LHMSnapshot:
    timestamp: datetime
    sensors: Mapping[str, LHMSensor]


Runner = Callable[..., subprocess.CompletedProcess[str]]


def collect_snapshot(
    executable: str | Path,
    *,
    timeout_seconds: int,
    runner: Runner = subprocess.run,
) -> LHMSnapshot:
    """Run the one-shot collector and parse its UTF-8 JSON standard output."""
    command = [str(executable)]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise LHMCollectionError(f"LibreHardwareMonitor collector timed out after {timeout_seconds} seconds") from error
    except OSError as error:
        raise LHMCollectionError(f"Unable to start LibreHardwareMonitor collector: {executable}") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "no error output"
        raise LHMCollectionError(
            f"LibreHardwareMonitor collector exit code {completed.returncode}: {detail}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LHMCollectionError("LibreHardwareMonitor collector did not produce valid JSON") from error
    return _parse_snapshot(payload)


def extract_sensor_values(
    snapshot: LHMSnapshot,
    sensor_map: Mapping[str, str],
    *,
    required_keys: set[str] | frozenset[str],
) -> dict[str, float]:
    """Map configured identifiers to report fields and enforce required values."""
    missing_keys = sorted(required_keys - sensor_map.keys())
    if missing_keys:
        raise LHMValidationError(
            f"Required LibreHardwareMonitor sensor mapping missing: {', '.join(missing_keys)}"
        )
    values: dict[str, float] = {}
    missing_identifiers: list[str] = []
    for field, identifier in sensor_map.items():
        sensor = snapshot.sensors.get(identifier)
        if sensor is None:
            if field in required_keys:
                missing_identifiers.append(field)
            continue
        values[field] = sensor.value
    if missing_identifiers:
        raise LHMValidationError(
            f"Required LibreHardwareMonitor sensor values missing: {', '.join(missing_identifiers)}"
        )
    return values


def _parse_snapshot(payload: object) -> LHMSnapshot:
    if not isinstance(payload, dict):
        raise LHMCollectionError("LibreHardwareMonitor collector JSON must be an object")
    timestamp = _parse_timestamp(payload.get("timestamp"))
    raw_sensors = payload.get("sensors")
    if not isinstance(raw_sensors, list):
        raise LHMCollectionError("LibreHardwareMonitor collector JSON has no sensors array")
    sensors: dict[str, LHMSensor] = {}
    for raw_sensor in raw_sensors:
        sensor = _parse_sensor(raw_sensor)
        if sensor.identifier in sensors:
            raise LHMCollectionError(f"Duplicate LibreHardwareMonitor identifier: {sensor.identifier}")
        sensors[sensor.identifier] = sensor
    return LHMSnapshot(timestamp=timestamp, sensors=sensors)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise LHMCollectionError("LibreHardwareMonitor collector timestamp is invalid")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as error:
        raise LHMCollectionError("LibreHardwareMonitor collector timestamp is invalid") from error


def _parse_sensor(value: object) -> LHMSensor:
    if not isinstance(value, dict):
        raise LHMCollectionError("LibreHardwareMonitor collector sensor is invalid")
    required_text = ("identifier", "hardware_name", "hardware_type", "name", "sensor_type")
    fields = {key: value.get(key) for key in required_text}
    if any(not isinstance(item, str) or not item for item in fields.values()):
        raise LHMCollectionError("LibreHardwareMonitor collector sensor text fields are invalid")
    raw_number = value.get("value")
    if isinstance(raw_number, bool) or not isinstance(raw_number, (int, float)):
        raise LHMCollectionError("LibreHardwareMonitor collector sensor value is invalid")
    number = float(raw_number)
    if not math.isfinite(number):
        raise LHMCollectionError("LibreHardwareMonitor collector sensor value is invalid")
    return LHMSensor(value=number, **fields)
