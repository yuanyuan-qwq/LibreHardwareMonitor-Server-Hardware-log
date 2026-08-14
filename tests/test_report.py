from __future__ import annotations

import math
from email import policy
from email.parser import BytesParser

from hwmonitor.report import _chart_values, _temperature_series, build_report_message


def test_discovers_all_temperature_fields_from_current_record():
    current = {
        "gpu_temp_c": 55.0,
        "gpu_hotspot_temp_c": 67.0,
        "nvme_adata_temp_c": 42.0,
        "cpu_usage_percent": 23.0,
    }
    labels = {
        "gpu_temp_c": "GPU Core (C)",
        "gpu_hotspot_temp_c": "GPU Hot Spot (C)",
        "nvme_adata_temp_c": "ADATA NVMe (C)",
    }

    assert _temperature_series(current, labels) == [
        ("gpu_temp_c", "GPU Core (C)"),
        ("gpu_hotspot_temp_c", "GPU Hot Spot (C)"),
        ("nvme_adata_temp_c", "ADATA NVMe (C)"),
    ]


def test_chart_values_turn_missing_historical_temperatures_into_gaps():
    values = _chart_values(
        [
            {"timestamp": "2026-08-15T09:00:00", "gpu_hotspot_temp_c": ""},
            {"timestamp": "2026-08-15T10:00:00"},
            {"timestamp": "2026-08-15T11:00:00", "gpu_hotspot_temp_c": 67.0},
        ],
        "gpu_hotspot_temp_c",
    )

    assert math.isnan(values[0])
    assert math.isnan(values[1])
    assert values[2] == 67.0


def test_builds_html_email_when_only_gpu_temperature_is_available():
    current = {
        "timestamp": "2026-08-13T10:00:00",
        "gpu_temp_c": 55.0,
        "cpu_usage_percent": 23.0,
        "gpu_usage_percent": 16.0,
        "ram_used_mb": 6144.0,
        "ram_available_mb": 10240.0,
        "ram_used_percent": 37.5,
        "partitions_json": '{"C:": {"free_gb": 100.0}}',
    }
    previous = {**current, "timestamp": "2026-08-13T09:00:00", "gpu_temp_c": 53.0}

    message = build_report_message(
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        current_record=current,
        history=[previous, current],
        display_labels={"gpu_temp_c": "GPU temperature (C)"},
    )

    parsed = BytesParser(policy=policy.default).parsebytes(message.as_bytes())
    html_part = parsed.get_body(("html",))
    assert "GPU temperature (C)" in html_part.get_content()
    assert "CPU temperature (C)" not in html_part.get_content()
    assert "Motherboard temperature (C)" not in html_part.get_content()
    assert "CPU and GPU usage" in html_part.get_content()
    assert "cid:temperature-trend" in html_part.get_content()
    assert "cid:resource-trend" in html_part.get_content()
    images = [part for part in parsed.walk() if part.get_content_type() == "image/png"]
    assert [image["Content-ID"] for image in images] == ["<temperature-trend>", "<resource-trend>"]


def test_builds_temperature_chart_when_old_rows_lack_new_optional_sensors():
    current = {
        "timestamp": "2026-08-15T10:00:00",
        "gpu_temp_c": 55.0,
        "gpu_hotspot_temp_c": 67.0,
        "nvme_adata_temp_c": 42.0,
        "cpu_usage_percent": 23.0,
        "gpu_usage_percent": 16.0,
        "partitions_json": "{}",
    }
    previous = {
        "timestamp": "2026-08-15T09:00:00",
        "gpu_temp_c": "53.0",
        "gpu_hotspot_temp_c": "",
        "nvme_adata_temp_c": "",
        "cpu_usage_percent": "20.0",
        "gpu_usage_percent": "12.0",
        "partitions_json": "{}",
    }

    message = build_report_message(
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        current_record=current,
        history=[previous, current],
        display_labels={
            "gpu_temp_c": "GPU Core (C)",
            "gpu_hotspot_temp_c": "GPU Hot Spot (C)",
            "nvme_adata_temp_c": "ADATA NVMe (C)",
        },
    )

    parsed = BytesParser(policy=policy.default).parsebytes(message.as_bytes())
    html_content = parsed.get_body(("html",)).get_content()
    assert "GPU Hot Spot (C)" in html_content
    assert "ADATA NVMe (C)" in html_content
    images = [part for part in parsed.walk() if part.get_content_type() == "image/png"]
    assert [image["Content-ID"] for image in images] == ["<temperature-trend>", "<resource-trend>"]
