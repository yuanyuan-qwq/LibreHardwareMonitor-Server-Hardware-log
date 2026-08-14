# LibreHardwareMonitor Server Hardware Log

The hourly Windows task runs a self-contained LibreHardwareMonitor collector once, sends a Gmail HTML report with CPU/GPU trend charts, appends the successful sample to `hwLog/daily_reports/lhm_YYYYMMDD.csv`, and exits. It does not use a GUI or leave a hardware-monitor process running.

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

5. From an elevated PowerShell, install the task:

   ```powershell
   .\install_scheduled_tasks.ps1
   ```

   The script prompts for the current Windows account password and registers `LibreHardwareMonitor - Send Hourly Report` with highest privileges and Password logon, so it can run while the account is logged out.

## Sensor mapping and report flow

GPU Core, GPU Hot Spot, ADATA NVMe Composite, HFS SSD, and WDC HDD temperatures are recorded when exposed by the current inventory. This host's elevated inventory does not expose CPU or DIMM Temperature sensors, so those fields are intentionally absent. NVMe temperature/10 and temperature/11 are warning/critical limits and are not logged as live readings.

The current day's `hwLog/daily_reports/lhm_YYYYMMDD.csv` is the source for the same-day graph. The in-memory current sample is added before the graph is rendered, so the emailed chart includes the newest readings. The row is appended to the daily CSV only after successful SMTP delivery. When the configured sensor set changes, the CSV header is expanded and older rows receive blank values for the new columns.

## Verify

Run one report manually:

```powershell
py run_monitor.py
```

Success creates or appends `hwLog/daily_reports/lhm_YYYYMMDD.csv` and sends the email. Failures write a UTF-8 error log under `hwLog/error_logs`; no daily row is added on failure. Historical `hw_*.csv` files are retained unchanged and are not used by LHM reports.

## Development

```powershell
py -m pytest -q
dotnet test collector.tests/LibreHardwareMonitorCollector.Tests.csproj
```

The collector references the official `LibreHardwareMonitorLib` NuGet package version 0.9.6. Build artifacts under `collector/publish/` are deliberately not committed.
