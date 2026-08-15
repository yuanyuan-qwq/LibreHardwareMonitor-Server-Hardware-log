"""Write timestamped errors to a local daily UTF-8 log."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path


def configure_error_logger(directory: str | Path, day: date) -> logging.Logger:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("hwmonitor")
    logger.handlers.clear()
    logger.setLevel(logging.ERROR)
    handler = logging.FileHandler(path / f"error_{day:%Y%m%d}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
