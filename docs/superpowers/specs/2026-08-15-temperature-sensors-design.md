# GPU and Storage Temperature Expansion Design

## Goal

Add every real-time temperature currently exposed by LibreHardwareMonitor on this X99 host to the daily CSV, HTML email, and temperature trend chart. Do not invent CPU or DIMM temperatures when the elevated inventory does not expose them.

## Sensor Mapping

The configured temperature fields are:

- `gpu_temp_c` -> `/gpu-nvidia/0/temperature/0` (GPU Core)
- `gpu_hotspot_temp_c` -> `/gpu-nvidia/0/temperature/2` (GPU Hot Spot)
- `nvme_adata_temp_c` -> `/nvme/2/temperature/0` (ADATA composite temperature)
- `ssd_hfs_temp_c` -> `/ssd/0/temperature/0` (HFS SSD temperature)
- `hdd_wdc_temp_c` -> `/hdd/1/temperature/0` (WDC HDD temperature)

NVMe warning and critical temperature thresholds are not measurements and must not be included. CPU and DIMM temperature fields remain absent until a future elevated inventory exposes real `Temperature` sensors.

## Report and Data Flow

The collector contract is unchanged. Python maps the five temperature identifiers alongside CPU/GPU usage and Windows system information. The temperature chart discovers configured `*_temp_c` fields from the current record and plots GPU Core, GPU Hot Spot, NVMe, SSD, and HDD series. The resource chart remains CPU/GPU usage.

The report continues to read successful rows from the current `lhm_YYYYMMDD.csv`, add the current sample in memory, render both charts, send mail, and append the current row only after mail succeeds.

## Daily CSV Compatibility

When the current day's CSV has an older header, the daily-log module expands it to the new field list before appending. Existing rows are preserved, and newly introduced columns are blank for historical rows. Chart rendering treats blank or missing historical temperature values as gaps rather than failing.

## Failure Handling and Tests

Required fields remain GPU temperature, CPU usage, and GPU usage. GPU Hot Spot and storage temperatures are optional: their temporary absence does not block the report, and missing values create chart gaps.

Tests cover expanded daily headers, preservation of existing rows, temperature charts with missing historical values, the five configured mappings, and the existing rule that SMTP failure does not append a daily row.
