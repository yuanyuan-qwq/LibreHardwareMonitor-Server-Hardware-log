"""Copy this file to config.py, then fill in credentials and LHM sensor identifiers."""

from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent
HWLOG_DIRECTORY = PROJECT_DIRECTORY / "hwLog"
DAILY_LOG_DIRECTORY = HWLOG_DIRECTORY / "daily_reports"
ERROR_LOG_DIRECTORY = HWLOG_DIRECTORY / "error_logs"
LHM_INVENTORY_PATH = HWLOG_DIRECTORY / "lhm_sensor_inventory.json"
DAILY_LOG_RETENTION_DAYS = 7

# Build with: dotnet publish collector/LibreHardwareMonitorCollector.csproj -c Release -r win-x64 --self-contained true -o collector/publish/win-x64
LHM_COLLECTOR_EXECUTABLE = PROJECT_DIRECTORY / "collector" / "publish" / "win-x64" / "LibreHardwareMonitorCollector.exe"
LHM_COLLECTOR_TIMEOUT_SECONDS = 30

# Populate all required stable identifiers from an elevated inventory scan.
SENSOR_MAP = {
    "cpu_usage_percent": "/intelcpu/0/load/0",
    "gpu_temp_c": "/gpu-nvidia/0/temperature/0",
    "gpu_hotspot_temp_c": "/gpu-nvidia/0/temperature/2",
    "nvme_adata_temp_c": "/nvme/2/temperature/0",
    "ssd_hfs_temp_c": "/ssd/0/temperature/0",
    "hdd_wdc_temp_c": "/hdd/1/temperature/0",
    "gpu_usage_percent": "/gpu-nvidia/0/load/0",
}
REQUIRED_SENSOR_KEYS = {
    "cpu_usage_percent",
    "gpu_temp_c",
    "gpu_usage_percent",
}

DISPLAY_LABELS = {
    "gpu_temp_c": "GPU Core (C)",
    "gpu_hotspot_temp_c": "GPU Hot Spot (C)",
    "nvme_adata_temp_c": "ADATA SX8200PNP Composite Temperature (C)",
    "ssd_hfs_temp_c": "HFS128G39TND-N210A Temperature (C)",
    "hdd_wdc_temp_c": "WDC WD10EZEX-00BN5A0 Temperature (C)",
    "cpu_usage_percent": "CPU usage (%)",
    "gpu_usage_percent": "GPU usage (%)",
    "ram_used_mb": "RAM used (MB)",
    "ram_available_mb": "RAM available (MB)",
    "ram_used_percent": "RAM used (%)",
}

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 30
SMTP_SENDER = "your.gmail.address@gmail.com"
SMTP_APP_PASSWORD = "paste-16-character-google-app-password-here"
SMTP_RECIPIENTS = ["recipient@example.com"]
