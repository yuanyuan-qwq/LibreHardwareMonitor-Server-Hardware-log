"""Send a prepared report through SMTP over implicit TLS."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


def send_gmail_report(
    message: EmailMessage,
    *,
    host: str,
    port: int,
    username: str,
    app_password: str,
    timeout_seconds: int,
) -> None:
    with smtplib.SMTP_SSL(host, port, timeout=timeout_seconds) as server:
        server.login(username, app_password)
        server.send_message(message)
