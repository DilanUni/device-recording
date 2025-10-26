import logging
from logging import Logger, FileHandler, StreamHandler, Formatter
from pathlib import Path
from typing import Optional, Final


class SystemLog:
    """
    SystemLog is a robust, professional logging utility for Python projects.
    
    Provides:
        - File logging to .log files
        - Optional console logging
        - Standard log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        - Professional, industry-standard formatting
        - Thread-safe and lightweight usage
    """

    DEFAULT_LOG_DIR: Final[str] = "logs"
    DEFAULT_LOG_FILE: Final[str] = "system.log"
    DEFAULT_LOG_FORMAT: Final[str] = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

    def __init__(self, name: str, log_file: Optional[str] = None, console: bool = True) -> None:
        """
        Initialize the logger.
        
        Args:
            name (str): Name of the logger, usually __name__ of the module
            log_file (Optional[str]): Path to the log file. Defaults to logs/system.log
            console (bool): Whether to also log to console. Default: True
        """
        self.logger: Logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels by default

        # Ensure logs directory exists
        log_path: Path
        if log_file is None:
            log_dir = Path(self.DEFAULT_LOG_DIR)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / self.DEFAULT_LOG_FILE
        else:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        # Prevent duplicate handlers
        if not self.logger.hasHandlers():
            # File handler
            file_handler: FileHandler = FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter: Formatter = Formatter(self.DEFAULT_LOG_FORMAT, self.DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # Console handler (optional)
            if console:
                console_handler: StreamHandler = StreamHandler()
                console_handler.setLevel(logging.INFO)
                console_formatter: Formatter = Formatter(self.DEFAULT_LOG_FORMAT, self.DATE_FORMAT)
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)

    def debug(self, message: str) -> None:
        """Log a message at DEBUG level."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log a message at INFO level."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log a message at WARNING level."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log a message at ERROR level."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log a message at CRITICAL level."""
        self.logger.critical(message)
