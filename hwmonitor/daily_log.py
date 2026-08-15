"""Persist and read the compact per-day monitoring log."""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Mapping, Sequence


def daily_log_path(log_directory: str | Path, day: date) -> Path:
    return Path(log_directory) / f"hw_{day:%Y%m%d}.csv"


def lhm_daily_log_path(log_directory: str | Path, day: date) -> Path:
    """Return an LHM-specific daily path without altering historical CSV files."""
    return Path(log_directory) / f"lhm_{day:%Y%m%d}.csv"


def append_daily_record(
    log_directory: str | Path,
    day: date,
    record: Mapping[str, object],
    fieldnames: Sequence[str],
    *,
    path_factory: Callable[[str | Path, date], Path] = daily_log_path,
) -> Path:
    """Append one record, creating a UTF-8 daily CSV and its header when needed."""
    path = path_factory(log_directory, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    _expand_csv_schema(path, fieldnames)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        if write_header:
            writer.writeheader()
        writer.writerow(record)
    return path


def _expand_csv_schema(path: Path, fieldnames: Sequence[str]) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        existing_fieldnames = reader.fieldnames or []
        if existing_fieldnames == list(fieldnames):
            return
        unexpected = set(existing_fieldnames) - set(fieldnames)
        if unexpected:
            raise ValueError(f"Existing CSV has fields not present in the requested schema: {sorted(unexpected)}")
        rows = list(reader)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_daily_records(path: str | Path) -> list[dict[str, str]]:
    """Read successfully recorded same-day samples for reporting."""
    with Path(path).open("r", newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def delete_expired_lhm_logs(
    log_directory: str | Path,
    today: date,
    retention_days: int = 7,
) -> list[Path]:
    """Delete dated LHM CSV files older than the inclusive retention window."""
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    directory = Path(log_directory)
    if not directory.exists():
        return []

    cutoff = today - timedelta(days=retention_days - 1)
    deleted: list[Path] = []
    for path in directory.glob("lhm_????????.csv"):
        try:
            file_day = datetime.strptime(path.stem.removeprefix("lhm_"), "%Y%m%d").date()
        except ValueError:
            continue
        if file_day < cutoff:
            path.unlink()
            deleted.append(path)
    return deleted
