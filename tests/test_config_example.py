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
