# LibreHardwareMonitor Server Hardware Log

Three Windows tasks collect LibreHardwareMonitor data hourly, send one Gmail HTML report at 11:59 PM, and retain only the latest seven calendar days of LHM daily CSV files. The collector does not use a GUI or remain running between samples.

## Setup

1. Install Python dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

2. Install the .NET 8 SDK and publish the collector:

   ```powershell
   dotnet publish collector/LibreHardwareMonitorCollector.csproj -c Release -r win-x64 --self-contained true -o collector/publish/win-x64
   ```

3. Replace `config.py` with a copy of `config.example.py`, then set Gmail credentials and run an administrator PowerShell inventory scan:

   ```powershell
   .\collector\publish\win-x64\LibreHardwareMonitorCollector.exe --inventory .\hwLog\lhm_sensor_inventory.json
   ```

4. Inspect `hwLog/lhm_sensor_inventory.json` and confirm the configured identifiers exist. If LHM reuses an identifier, the collector appends a stable `~sensor-name` suffix so every inventory identifier remains unique.

5. From an elevated PowerShell, install the tasks:

   ```powershell
   .\install_scheduled_tasks.ps1
   ```

   The script prompts once for the current Windows account password and registers these highest-privilege tasks so they can run while the account is logged out:

   - `LibreHardwareMonitor - Collect Hourly` at the top of every hour
   - `LibreHardwareMonitor - Send Daily Report` daily at 11:59 PM
   - `LibreHardwareMonitor - Cleanup Daily Logs` daily at 12:15 AM

   The installer also removes the obsolete `HWiNFO64 - Send Hourly Report` and `LibreHardwareMonitor - Send Hourly Report` tasks when present.

## Sensor mapping and report flow

GPU Core, GPU Hot Spot, ADATA NVMe Composite, HFS SSD, and WDC HDD temperatures are recorded when exposed by the current inventory. This host's elevated inventory does not expose CPU or DIMM Temperature sensors, so those fields are intentionally absent. NVMe temperature/10 and temperature/11 are warning/critical limits and are not logged as live readings.

The hourly collection task appends each successful sample directly to the current day's `hwLog/daily_reports/lhm_YYYYMMDD.csv` without sending mail. At 11:59 PM, the report task reads the complete CSV, uses its last row as the current state, generates the temperature and CPU/GPU/RAM usage graphs from the day's rows, and sends one email. Reporting never appends another row.

The cleanup task keeps today and the previous six calendar days, for a maximum of seven current `lhm_YYYYMMDD.csv` files. It never removes historical `hw_*.csv`, the sensor inventory, error logs, or unrelated files. When the configured sensor set changes, the current CSV header is expanded and older rows receive blank values for the new columns.

## Verify

Run each operation manually:

```powershell
py run_monitor.py collect
py run_monitor.py report
py run_monitor.py cleanup
```

`collect` creates or appends today's CSV. `report` sends the email only when today's CSV contains at least one sample. `cleanup` applies the seven-day retention window. Failures write a UTF-8 error log under `hwLog/error_logs`. Historical `hw_*.csv` files are retained unchanged and are not used by LHM reports.

## Development

```powershell
py -m pytest -q
dotnet test collector.tests/LibreHardwareMonitorCollector.Tests.csproj
```

The collector references the official `LibreHardwareMonitorLib` NuGet package version 0.9.6. Build artifacts under `collector/publish/` are deliberately not committed.
