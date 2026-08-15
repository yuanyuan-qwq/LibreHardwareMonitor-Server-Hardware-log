"""Windows Task Scheduler entry point for collection, reporting, and cleanup."""

from __future__ import annotations

import json
import sys
from datetime import datetime

from hwmonitor.daily_log import (
    append_daily_record,
    delete_expired_lhm_logs,
    lhm_daily_log_path,
    read_daily_records,
)
from hwmonitor.error_log import configure_error_logger
from hwmonitor.lhm import collect_snapshot, extract_sensor_values
from hwmonitor.locking import AlreadyRunningError, WindowsMutex
from hwmonitor.report import build_report_message
from hwmonitor.smtp_client import send_gmail_report
from hwmonitor.system_info import collect_windows_metrics


VALID_ACTIONS = {"collect", "report", "cleanup"}
MUTEX_NAMES = {
    "collect": r"Global\LibreHardwareMonitorCollectHourly",
    "report": r"Global\LibreHardwareMonitorSendDailyReport",
    "cleanup": r"Global\LibreHardwareMonitorCleanupDailyLogs",
}


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    action = arguments[0].lower() if arguments else "collect"
    if len(arguments) > 1 or action not in VALID_ACTIONS:
        print("Usage: py run_monitor.py [collect|report|cleanup]", file=sys.stderr)
        return 2

    try:
        import config
    except ModuleNotFoundError:
        print("Missing config.py. Copy config.example.py to config.py and fill in the values.", file=sys.stderr)
        return 2

    now = datetime.now()
    logger = configure_error_logger(config.ERROR_LOG_DIRECTORY, now.date())
    try:
        with WindowsMutex(MUTEX_NAMES[action]):
            if action == "collect":
                _collect_and_append(config)
            elif action == "report":
                _send_daily_report(config, now)
            else:
                deleted = delete_expired_lhm_logs(
                    config.DAILY_LOG_DIRECTORY,
                    now.date(),
                    retention_days=getattr(config, "DAILY_LOG_RETENTION_DAYS", 7),
                )
                logger.info("Deleted %d expired LibreHardwareMonitor daily CSV files", len(deleted))
    except AlreadyRunningError as error:
        logger.warning("Skipped overlapping scheduled run: %s", error)
        return 0
    except Exception as error:
        logger.exception("Hardware monitoring %s failed", action)
        print(
            f"Hardware monitoring {action} failed: {error}. "
            f"See error log: {config.ERROR_LOG_DIRECTORY}",
            file=sys.stderr,
        )
        return 1
    return 0


def _collect_and_append(config) -> None:
    snapshot = collect_snapshot(
        config.LHM_COLLECTOR_EXECUTABLE,
        timeout_seconds=config.LHM_COLLECTOR_TIMEOUT_SECONDS,
    )
    record = _build_record(snapshot, config)
    append_daily_record(
        config.DAILY_LOG_DIRECTORY,
        snapshot.timestamp.date(),
        record,
        _fieldnames(config),
        path_factory=lhm_daily_log_path,
    )


def _send_daily_report(config, now: datetime) -> None:
    target = lhm_daily_log_path(config.DAILY_LOG_DIRECTORY, now.date())
    if not target.is_file():
        raise FileNotFoundError(f"No LibreHardwareMonitor daily CSV exists for {now:%Y-%m-%d}: {target}")
    history = read_daily_records(target)
    if not history:
        raise ValueError(f"LibreHardwareMonitor daily CSV is empty: {target}")

    current_record = history[-1]
    message = build_report_message(
        sender=config.SMTP_SENDER,
        recipients=config.SMTP_RECIPIENTS,
        current_record=current_record,
        history=history,
        display_labels=_display_labels(config),
    )
    send_gmail_report(
        message,
        host=config.SMTP_HOST,
        port=config.SMTP_PORT,
        username=config.SMTP_SENDER,
        app_password=config.SMTP_APP_PASSWORD,
        timeout_seconds=config.SMTP_TIMEOUT_SECONDS,
    )


def _build_record(snapshot, config) -> dict[str, object]:
    record: dict[str, object] = {"timestamp": snapshot.timestamp.isoformat(timespec="seconds")}
    record.update(
        extract_sensor_values(
            snapshot,
            config.SENSOR_MAP,
            required_keys=set(config.REQUIRED_SENSOR_KEYS),
        )
    )
    dimm_temperatures = [
        value for key, value in record.items() if key.startswith("ram_dimm_") and key.endswith("_temp_c")
    ]
    if dimm_temperatures:
        record["ram_max_temp_c"] = max(dimm_temperatures)
    metrics = collect_windows_metrics()
    record["ram_used_mb"] = metrics["ram_used_mb"]
    record["ram_available_mb"] = metrics["ram_available_mb"]
    record["ram_used_percent"] = metrics["ram_used_percent"]
    record["partitions_json"] = json.dumps(metrics["partitions"], ensure_ascii=False, sort_keys=True)
    return record


def _fieldnames(config) -> list[str]:
    return [
        "timestamp",
        *config.SENSOR_MAP.keys(),
        *(["ram_max_temp_c"] if any(key.startswith("ram_dimm_") for key in config.SENSOR_MAP) else []),
        "ram_used_mb",
        "ram_available_mb",
        "ram_used_percent",
        "partitions_json",
    ]


def _display_labels(config) -> dict[str, str]:
    labels = dict(config.DISPLAY_LABELS)
    if not hasattr(config, "DRIVE_LABELS"):
        return labels
    for number, name in enumerate(config.DRIVE_LABELS, start=1):
        labels[f"disk_{number}_temp_c"] = f"{name}温度 (°C)"
    return labels


if __name__ == "__main__":
    sys.exit(main())
