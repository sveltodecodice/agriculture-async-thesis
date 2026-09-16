import logging
import sys
from typing import Optional

from common.constants import DEFAULT_DATE_FORMAT, DEFAULT_FORMAT


class LoggingUtils:
    """Helper class to configure and retrieve application loggers.

    Attributes:
        is_configured (bool): Class attribute tracking whether logging setup has run.
    """

    is_configured = False

    @classmethod
    def configure(
        cls,
        console_level: int = logging.INFO,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> None:
        """Configure standard stdout logging handlers for the application.

        Args:
            console_level (int, optional): Minimum logging level (e.g. logging.INFO).
                Defaults to logging.INFO.
            log_format (str, optional): Custom string format for log messages.
            date_format (str, optional): Custom string format for timestamps.
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

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Create or fetch a named logger instance.

        Args:
            name (str): The identifier for the logger (typically __name__).

        Returns:
            logging.Logger: Configured Python logger instance.
        """
        return logging.getLogger(name)
