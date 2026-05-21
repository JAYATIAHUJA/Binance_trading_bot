"""
Structured logging configuration for the trading bot.
Logs to both console (colored) and file (JSON-structured).
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON for machine-readable log files."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_obj["extra"] = record.extra
        return json.dumps(log_obj)


class ColoredConsoleFormatter(logging.Formatter):
    """Human-friendly colored output for the terminal."""

    COLORS = {
        "DEBUG": "\033[90m",    # grey
        "INFO": "\033[36m",     # cyan
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[41m", # red bg
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.utcfromtimestamp(record.created).strftime("%H:%M:%S")
        prefix = f"{color}{self.BOLD}[{record.levelname[0]}]{self.RESET}"
        return f"\033[90m{ts}\033[0m {prefix} {record.getMessage()}"


def setup_logger(name: str = "trading_bot", log_file: str = "trading_bot.log") -> logging.Logger:
    """
    Create and configure a logger with:
    - JSON file handler (all levels DEBUG+)
    - Colored console handler (INFO+)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # already configured

    # --- File handler (JSON, DEBUG+) ---
    log_path = LOG_DIR / log_file
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())

    # --- Console handler (colored, INFO+) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredConsoleFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
