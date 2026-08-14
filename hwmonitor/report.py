"""Create self-contained HTML hardware reports with CID-embedded charts."""

from __future__ import annotations

import html
import io
import json
import math
from collections.abc import Mapping, Sequence
from email.message import EmailMessage

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_report_message(
    *,
    sender: str,
    recipients: Sequence[str],
    current_record: Mapping[str, object],
    history: Sequence[Mapping[str, object]],
    display_labels: Mapping[str, str],
) -> EmailMessage:
    """Build a multipart message with temperature and CPU/GPU/RAM usage charts."""
    temperature_chart = _render_chart(
        history,
        _temperature_series(current_record, display_labels),
        "Temperature trend (C)",
    )
    resource_chart = _render_chart(
        history,
        [
            ("cpu_usage_percent", "CPU usage"),
            ("gpu_usage_percent", "GPU usage"),
            ("ram_used_percent", "RAM usage"),
        ],
        "CPU, GPU and RAM usage trend (%)",
    )

    message = EmailMessage()
    message["Subject"] = f"Hardware monitor report - {current_record['timestamp']}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content("This message contains an HTML hardware monitoring report.")
    message.add_alternative(_build_html(current_record, display_labels), subtype="html")
    html_part = message.get_payload()[-1]
    html_part.add_related(temperature_chart, maintype="image", subtype="png", cid="<temperature-trend>", filename="temperature-trend.png")
    html_part.add_related(resource_chart, maintype="image", subtype="png", cid="<resource-trend>", filename="resource-trend.png")
    return message


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


def _build_html(record: Mapping[str, object], display_labels: Mapping[str, str]) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(record[key]))}</td></tr>"
        for key, label in display_labels.items()
        if key in record
    )
    partitions = json.loads(str(record["partitions_json"]))
    partition_rows = "".join(
        f"<tr><th>{html.escape(letter)}</th><td>Free {values.get('free_gb', 'N/A')} GB / Used {values.get('used_percent', 'N/A')}%</td></tr>"
        for letter, values in sorted(partitions.items())
    )
    return f"""<!doctype html><html><body style="font-family:Segoe UI,Arial,sans-serif">
<h2>Hardware monitor report</h2><p>Sample time: {html.escape(str(record['timestamp']))}</p>
<table border="1" cellpadding="7" cellspacing="0" style="border-collapse:collapse">{rows}{partition_rows}</table>
<h2>Today&apos;s trend</h2><h3>Temperature</h3><img src="cid:temperature-trend" alt="Temperature trend">
<h3>CPU, GPU and RAM usage</h3><img src="cid:resource-trend" alt="CPU, GPU and RAM usage trend">
</body></html>"""


def _render_chart(history: Sequence[Mapping[str, object]], series: Sequence[tuple[str, str]], title: str) -> bytes:
    figure, axis = plt.subplots(figsize=(9, 3.8), constrained_layout=True)
    timestamps = [str(row["timestamp"])[11:16] for row in history]
    for key, label in series:
        axis.plot(timestamps, _chart_values(history, key), marker="o", linewidth=1.8, label=label)
    axis.set_title(title)
    axis.set_xlabel("Time")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.autofmt_xdate()
    output = io.BytesIO()
    figure.savefig(output, format="png", dpi=130)
    plt.close(figure)
    return output.getvalue()
