from __future__ import annotations

import csv
import json
from datetime import date

import pytest

from hwmonitor.daily_log import append_daily_record, read_daily_records


FIELDNAMES = ["timestamp", "cpu_temp_c", "partitions_json"]


def test_appends_same_day_records_to_one_date_named_csv(tmp_path):
    record = {
        "timestamp": "2026-08-13T10:00:00",
        "cpu_temp_c": 51.2,
        "partitions_json": json.dumps({"C:": {"free_gb": 100.0}}),
    }

    first_path = append_daily_record(tmp_path, date(2026, 8, 13), record, FIELDNAMES)
    second_path = append_daily_record(
        tmp_path,
        date(2026, 8, 13),
        {**record, "timestamp": "2026-08-13T11:00:00"},
        FIELDNAMES,
    )

    assert first_path == tmp_path / "hw_20260813.csv"
    assert second_path == first_path
    with first_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["timestamp"] for row in rows] == [
        "2026-08-13T10:00:00",
        "2026-08-13T11:00:00",
    ]


def test_creates_a_new_csv_after_midnight(tmp_path):
    record = {
        "timestamp": "2026-08-13T23:00:00",
        "cpu_temp_c": 51.2,
        "partitions_json": "{}",
    }

    before_midnight = append_daily_record(tmp_path, date(2026, 8, 13), record, FIELDNAMES)
    after_midnight = append_daily_record(
        tmp_path,
        date(2026, 8, 14),
        {**record, "timestamp": "2026-08-14T00:00:00"},
        FIELDNAMES,
    )

    assert before_midnight.name == "hw_20260813.csv"
    assert after_midnight.name == "hw_20260814.csv"
    assert read_daily_records(after_midnight) == [
        {"timestamp": "2026-08-14T00:00:00", "cpu_temp_c": "51.2", "partitions_json": "{}"}
    ]


def test_expands_existing_header_and_preserves_old_rows(tmp_path):
    path = tmp_path / "lhm_20260815.csv"
    path.write_text(
        "timestamp,gpu_temp_c\n2026-08-15T09:00:00,52.0\n",
        encoding="utf-8",
    )

    append_daily_record(
        tmp_path,
        date(2026, 8, 15),
        {
            "timestamp": "2026-08-15T10:00:00",
            "gpu_temp_c": 54.0,
            "gpu_hotspot_temp_c": 66.0,
        },
        ["timestamp", "gpu_temp_c", "gpu_hotspot_temp_c"],
        path_factory=lambda directory, day: path,
    )

    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [
        {
            "timestamp": "2026-08-15T09:00:00",
            "gpu_temp_c": "52.0",
            "gpu_hotspot_temp_c": "",
        },
        {
            "timestamp": "2026-08-15T10:00:00",
            "gpu_temp_c": "54.0",
            "gpu_hotspot_temp_c": "66.0",
        },
    ]


def test_rejects_schema_contraction_without_changing_existing_csv(tmp_path):
    path = tmp_path / "lhm_20260815.csv"
    original = b"timestamp,gpu_temp_c\r\n2026-08-15T09:00:00,52.0\r\n"
    path.write_bytes(original)

    with pytest.raises(
        ValueError,
        match="Existing CSV has fields not present in the requested schema:.*gpu_temp_c",
    ):
        append_daily_record(
            tmp_path,
            date(2026, 8, 15),
            {"timestamp": "2026-08-15T10:00:00"},
            ["timestamp"],
            path_factory=lambda directory, day: path,
        )

    assert path.read_bytes() == original
