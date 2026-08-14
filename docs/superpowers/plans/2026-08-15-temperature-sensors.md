# GPU and Storage Temperature Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record and report every real-time GPU and storage temperature currently exposed by LibreHardwareMonitor on this X99 host while keeping older same-day CSV rows readable.

**Architecture:** Keep the C# collector contract unchanged and add the discovered identifiers through Python configuration. Upgrade an existing daily CSV header before appending, derive temperature chart series from the current record, and represent missing historical values as `NaN` so Matplotlib draws gaps.

**Tech Stack:** Python 3, pytest, standard-library `csv`, Matplotlib, LibreHardwareMonitor collector JSON

## Global Constraints

- Use the existing official `LibreHardwareMonitorLib` 0.9.6 collector without changing its JSON contract.
- Include `/gpu-nvidia/0/temperature/0`, `/gpu-nvidia/0/temperature/2`, `/nvme/2/temperature/0`, `/ssd/0/temperature/0`, and `/hdd/1/temperature/0`.
- Do not include `/nvme/2/temperature/10` or `/nvme/2/temperature/11`; they are warning and critical thresholds, not live measurements.
- Do not invent CPU or DIMM temperature fields while the elevated inventory exposes no real `Temperature` sensors for them.
- Keep `gpu_temp_c`, `cpu_usage_percent`, and `gpu_usage_percent` required; all newly added temperatures are optional.
- Send mail before appending the daily row, preserving the rule that SMTP failure does not change the CSV.

---

### Task 1: Expand an Existing Daily CSV Schema Safely

**Files:**
- Modify: `hwmonitor/daily_log.py`
- Test: `tests/test_daily_log.py`

**Interfaces:**
- Consumes: `append_daily_record(log_directory, day, record, fieldnames, *, path_factory)` as called by `run_monitor.main()`.
- Produces: `_expand_csv_schema(path: Path, fieldnames: Sequence[str]) -> None`; after it returns, a non-empty existing CSV has exactly the requested header and all prior row values are preserved.

- [ ] **Step 1: Write a failing schema-expansion test**

Add this test to `tests/test_daily_log.py`:

```python
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
```

- [ ] **Step 2: Run the test and verify the old header breaks the append**

Run: `py -m pytest tests/test_daily_log.py::test_expands_existing_header_and_preserves_old_rows -v`

Expected: FAIL because `gpu_hotspot_temp_c` is not present in the existing CSV header.

- [ ] **Step 3: Implement schema expansion before append**

In `hwmonitor/daily_log.py`, call `_expand_csv_schema(path, fieldnames)` after creating the parent directory and before opening the file for append. Implement it with a sibling temporary file so the original is not truncated during conversion:

```python
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
```

- [ ] **Step 4: Run the daily-log tests**

Run: `py -m pytest tests/test_daily_log.py -v`

Expected: all tests PASS, including the existing same-day and midnight behavior.

- [ ] **Step 5: Commit the independently tested CSV migration**

```powershell
git add -- hwmonitor/daily_log.py tests/test_daily_log.py
git commit -m "feat: expand daily CSV temperature fields"
```

### Task 2: Build Dynamic Temperature Series with Historical Gaps

**Files:**
- Modify: `hwmonitor/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `current_record` keys ending in `_temp_c` and their optional human-readable entries in `display_labels`.
- Produces: `_temperature_series(current_record, display_labels) -> list[tuple[str, str]]` and `_chart_values(history, key) -> list[float]`; missing or blank values become `math.nan`.

- [ ] **Step 1: Write failing tests for dynamic series and gaps**

Add imports and tests to `tests/test_report.py`:

```python
import math

from hwmonitor.report import _chart_values, _temperature_series


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
```

- [ ] **Step 2: Run the new report tests and verify the helpers are missing**

Run: `py -m pytest tests/test_report.py -v`

Expected: test collection FAILS because `_chart_values` and `_temperature_series` do not exist.

- [ ] **Step 3: Implement dynamic series selection and tolerant numeric conversion**

In `hwmonitor/report.py`, import `math`, replace the fixed GPU series passed to `_render_chart`, and add the helpers:

```python
def _temperature_series(
    current_record: Mapping[str, object],
    display_labels: Mapping[str, str],
) -> list[tuple[str, str]]:
    return [
        (key, display_labels.get(key, key))
        for key in current_record
        if key.endswith("_temp_c")
    ]


def _chart_values(history: Sequence[Mapping[str, object]], key: str) -> list[float]:
    values: list[float] = []
    for row in history:
        value = row.get(key)
        values.append(math.nan if value in (None, "") else float(value))
    return values
```

Change the temperature chart call to:

```python
temperature_chart = _render_chart(
    history,
    _temperature_series(current_record, display_labels),
    "Temperature trend (C)",
)
```

Change `_render_chart` to plot `_chart_values(history, key)` instead of indexing every row directly.

- [ ] **Step 4: Add an email-level regression test with missing old values**

Add this test to `tests/test_report.py`:

```python
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
```

- [ ] **Step 5: Run the report tests**

Run: `py -m pytest tests/test_report.py -v`

Expected: all tests PASS and Matplotlib renders the optional series without a `KeyError` or `ValueError`.

- [ ] **Step 6: Commit the independently tested reporting change**

```powershell
git add -- hwmonitor/report.py tests/test_report.py
git commit -m "feat: chart available hardware temperatures"
```

### Task 3: Configure the Five Real-Time Temperature Sensors

**Files:**
- Modify: `config.example.py`
- Modify locally, never stage: `config.py`
- Modify: `tests/test_lhm_runner.py`
- Create: `tests/test_config_example.py`

**Interfaces:**
- Consumes: the identifiers already present in `hwLog/lhm_sensor_inventory.json`.
- Produces: five temperature fields in `SENSOR_MAP`; only `gpu_temp_c` remains in `REQUIRED_SENSOR_KEYS` among them.

- [ ] **Step 1: Write a failing configuration-contract test**

Create `tests/test_config_example.py`:

```python
from __future__ import annotations

import runpy
from pathlib import Path


def test_example_maps_live_gpu_and_storage_temperatures_only():
    config = runpy.run_path(str(Path(__file__).parents[1] / "config.example.py"))

    assert config["SENSOR_MAP"] == {
        "cpu_usage_percent": "/intelcpu/0/load/0",
        "gpu_temp_c": "/gpu-nvidia/0/temperature/0",
        "gpu_hotspot_temp_c": "/gpu-nvidia/0/temperature/2",
        "nvme_adata_temp_c": "/nvme/2/temperature/0",
        "ssd_hfs_temp_c": "/ssd/0/temperature/0",
        "hdd_wdc_temp_c": "/hdd/1/temperature/0",
        "gpu_usage_percent": "/gpu-nvidia/0/load/0",
    }
    assert "/nvme/2/temperature/10" not in config["SENSOR_MAP"].values()
    assert "/nvme/2/temperature/11" not in config["SENSOR_MAP"].values()
    assert config["REQUIRED_SENSOR_KEYS"] == {
        "cpu_usage_percent",
        "gpu_temp_c",
        "gpu_usage_percent",
    }
```

- [ ] **Step 2: Run the test and verify the optional mappings are absent**

Run: `py -m pytest tests/test_config_example.py -v`

Expected: FAIL because the example currently maps only GPU Core temperature.

- [ ] **Step 3: Add exact mappings and LibreHardwareMonitor names**

Update both `config.example.py` and the ignored local `config.py` with these entries, without touching SMTP credentials:

```python
SENSOR_MAP = {
    "cpu_usage_percent": "/intelcpu/0/load/0",
    "gpu_temp_c": "/gpu-nvidia/0/temperature/0",
    "gpu_hotspot_temp_c": "/gpu-nvidia/0/temperature/2",
    "nvme_adata_temp_c": "/nvme/2/temperature/0",
    "ssd_hfs_temp_c": "/ssd/0/temperature/0",
    "hdd_wdc_temp_c": "/hdd/1/temperature/0",
    "gpu_usage_percent": "/gpu-nvidia/0/load/0",
}
```

Add these display labels to both files:

```python
"gpu_temp_c": "GPU Core (C)",
"gpu_hotspot_temp_c": "GPU Hot Spot (C)",
"nvme_adata_temp_c": "ADATA SX8200PNP Composite Temperature (C)",
"ssd_hfs_temp_c": "HFS128G39TND-N210A Temperature (C)",
"hdd_wdc_temp_c": "WDC WD10EZEX-00BN5A0 Temperature (C)",
```

Do not add the optional keys to `REQUIRED_SENSOR_KEYS`.

- [ ] **Step 4: Exercise optional values through the runner test**

Import `csv`, then extend the fake `SENSOR_MAP` in `_config`:

```python
"gpu_hotspot_temp_c": "/gpu/temperature/2",
"nvme_adata_temp_c": "/nvme/temperature/0",
```

In the successful test's `extract_sensor_values` replacement, return the corresponding readings:

```python
"gpu_hotspot_temp_c": 63.0,
"nvme_adata_temp_c": 41.0,
```

Replace the final file-existence assertion in that test with a row-level check:

```python
daily_path = tmp_path / "daily" / "lhm_20260814.csv"
with daily_path.open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
assert rows[0]["gpu_hotspot_temp_c"] == "63.0"
assert rows[0]["nvme_adata_temp_c"] == "41.0"
```

Keep `test_smtp_failure_does_not_append_an_lhm_daily_record` unchanged as the failure-order regression.

- [ ] **Step 5: Run configuration and runner tests**

Run: `py -m pytest tests/test_config_example.py tests/test_lhm_runner.py -v`

Expected: all tests PASS; the successful run writes optional temperatures and the SMTP failure still writes no file.

- [ ] **Step 6: Commit only repository-safe configuration and tests**

```powershell
git add -- config.example.py tests/test_config_example.py tests/test_lhm_runner.py
git commit -m "feat: map GPU and storage temperatures"
```

Confirm `config.py` is not staged because it contains local SMTP credentials.

### Task 4: Document and Verify the Complete Temperature Flow

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the final configuration, daily CSV schema migration, and dynamic chart behavior from Tasks 1–3.
- Produces: operator documentation that distinguishes real live temperatures from unavailable CPU/DIMM sensors and NVMe threshold values.

- [ ] **Step 1: Update the README sensor-mapping section**

Document the five exact live identifiers and explain:

```text
GPU Core, GPU Hot Spot, ADATA NVMe Composite, HFS SSD, and WDC HDD temperatures are recorded when exposed by the current inventory. This host's elevated inventory does not expose CPU or DIMM Temperature sensors, so those fields are intentionally absent. NVMe temperature/10 and temperature/11 are warning/critical limits and are not logged as live readings.
```

Also state that `lhm_YYYYMMDD.csv` is the source for the same-day graph, that the in-memory current sample is added before rendering, that the row is appended only after successful SMTP delivery, and that a changed header is expanded with blanks for older rows.

- [ ] **Step 2: Run the complete Python test suite**

Run: `py -m pytest -v`

Expected: all Python tests PASS.

- [ ] **Step 3: Run the collector test suite to confirm the unchanged contract**

Run: `dotnet test collector.tests/LibreHardwareMonitorCollector.Tests.csproj -c Release`

Expected: all C# tests PASS.

- [ ] **Step 4: Validate the configured identifiers against inventory without exposing credentials**

Run this read-only check:

```powershell
@'
import json
import runpy
from pathlib import Path

root = Path.cwd()
config = runpy.run_path(str(root / "config.py"))
inventory = json.loads((root / "hwLog" / "lhm_sensor_inventory.json").read_text(encoding="utf-8-sig"))
available = {sensor["identifier"] for sensor in inventory["sensors"]}
missing = {key: identifier for key, identifier in config["SENSOR_MAP"].items() if identifier not in available}
raise SystemExit(f"Missing identifiers: {missing}" if missing else "All configured identifiers are present.")
'@ | py -
```

Expected: `All configured identifiers are present.` No SMTP values are printed.

- [ ] **Step 5: Check formatting and review the final diff**

Run:

```powershell
git diff --check
git status --short
git diff -- README.md config.example.py hwmonitor/daily_log.py hwmonitor/report.py tests
```

Expected: no whitespace errors; only intended source, test, documentation, and pre-existing user changes appear. `config.py` remains ignored and unstaged.

- [ ] **Step 6: Commit the documentation**

```powershell
git add -- README.md
git commit -m "docs: explain temperature reporting flow"
```

- [ ] **Step 7: Perform the operator-only live check**

From an elevated PowerShell session, run `py run_monitor.py`. Expected: exit code `0`, one email containing the five available temperature readings and both CID graphs, and one new row in the current `hwLog/daily_reports/lhm_YYYYMMDD.csv`. This intentionally sends a real email, so it is not part of automated execution without operator approval.
