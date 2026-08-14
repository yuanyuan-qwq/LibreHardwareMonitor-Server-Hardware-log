# RAM Usage Chart Design

## Goal

Add Windows RAM utilization to the existing resource-usage trend chart in the hourly LibreHardwareMonitor email report.

## Design

Use the existing `ram_used_percent` value already collected by `run_monitor.py` and already stored in each daily CSV row. Add it as a third series beside CPU and GPU usage in the existing resource chart because all three values use the same percentage scale.

Update the resource chart title, HTML heading, and image alternative text to refer to CPU, GPU, and RAM usage. Keep the existing CID image, email layout, CSV schema, collection flow, and SMTP ordering unchanged.

## Scope

Modify only `hwmonitor/report.py`. Do not create a separate RAM chart, add a second axis, graph RAM megabytes, or change sensor/configuration mappings.

Per the operator's explicit request, do not add or run tests for this change. Commit the report change and push it to the configured `origin` remote after implementation.
