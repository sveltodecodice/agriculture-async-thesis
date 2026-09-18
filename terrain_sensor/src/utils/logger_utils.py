"""Centralized logging utility for terrain sensor service components."""

import logging
import sys
from typing import Optional

from common.constants import DEFAULT_DATE_FORMAT, DEFAULT_FORMAT


class LoggingUtils:
    """Manages application-wide logging configuration."""

    is_configured: bool = False

    @classmethod
    def configure(
        cls,
        console_level: int = logging.INFO,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> None:
        """Configures the root logging output stream and formatting.

        Args:
            console_level (int): Minimum logging level for console output.
            log_format (Optional[str]): Custom format string for log messages.
            date_format (Optional[str]): Custom date formatting string.
        """
        if cls.is_configured:
            return

        formatter = logging.Formatter(
            fmt=log_format or DEFAULT_FORMAT,
            datefmt=date_format or DEFAULT_DATE_FORMAT,
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(console_level)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)

        cls.is_configured = True
        root_logger.debug(
            "Logging configured: console_level=%s",
            logging.getLevelName(console_level),
        )

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Retrieves a named logger instance.

        Args:
            name (str): Module name or identifier for the logger.

        Returns:
            logging.Logger: Configured logger instance.
        """
        return logging.getLogger(name)
