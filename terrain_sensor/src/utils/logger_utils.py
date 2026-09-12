import logging
import sys
from typing import Optional

from common.constants import DEFAULT_DATE_FORMAT, DEFAULT_FORMAT


class LoggingUtils:
    """
    Centralized application logging configuration.

    Call LoggingUtils.configure() once at application startup.

    Then, from any module:

        logger = LoggingUtils.get_logger(__name__)

    or simply:

        logger = logging.getLogger(__name__)
    """

    is_configured = False

    @classmethod
    def configure(
        cls,
        console_level: int = logging.INFO,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> None:
        """
        Configure the application's logging system.

        This method should normally be called only once.

        Args:

            console_level:
                Minimum logging level displayed in the terminal.

            log_format:
                Optional custom logging format.

            date_format:
                Optional custom datetime format.

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

        logging.getLogger(__name__).debug(
            "Logging configured: file=%s, console_level=%s, file_level=%s",
            logging.getLevelName(console_level),
        )

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Retrieve a logger.

        Usually called with:

            logger = LoggingUtils.get_logger(__name__)
        """
        return logging.getLogger(name)

    @classmethod
    def logger_is_configured(cls) -> bool:
        """
        Return whether logging has already been configured.
        """
        return cls.is_configured
