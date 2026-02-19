"""
Logging configuration for the Binance Futures Trading Bot.
Provides Rich console output and plain-text file logging.
"""

import logging
import os
import sys

from rich.logging import RichHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")


class PlainFormatter(logging.Formatter):
    """Plain formatter for file logging — production-readable."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Set up logging with Rich console handler and plain file handler.

    Args:
        console_level: Logging level for console output (default: INFO).
        file_level: Logging level for file output (default: DEBUG).

    Returns:
        logging.Logger: Configured root logger for the bot.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Console handler — Rich, INFO level
    console_handler = RichHandler(
        level=console_level,
        show_path=False,
        show_time=True,
        rich_tracebacks=False,
        markup=True,
    )
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

    # File handler — plain text, DEBUG level
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(PlainFormatter())
    logger.addHandler(file_handler)

    return logger


def get_logger(name=None):
    """
    Get a child logger under the trading_bot namespace.

    Args:
        name: Optional sub-logger name (e.g. 'client', 'orders').

    Returns:
        logging.Logger
    """
    if name:
        return logging.getLogger(f"trading_bot.{name}")
    return logging.getLogger("trading_bot")
