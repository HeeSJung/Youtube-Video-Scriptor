"""
Logging configuration and custom exceptions for YouTube Scene Extractor

This module provides structured logging setup and custom exception classes
for better error handling and debugging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Custom Exception Classes


class YouTubeSceneExtractorError(Exception):
    """Base exception for all YouTube Scene Extractor errors"""

    pass


class InvalidURLError(YouTubeSceneExtractorError):
    """Raised when a YouTube URL is invalid or cannot be parsed"""

    pass


class VideoNotFoundError(YouTubeSceneExtractorError):
    """Raised when a YouTube video cannot be found or accessed"""

    pass


class VideoTooLongError(YouTubeSceneExtractorError):
    """Raised when a video exceeds the maximum allowed duration"""

    pass


class CaptionNotAvailableError(YouTubeSceneExtractorError):
    """Raised when captions are not available for a video"""

    pass


class SceneDetectionError(YouTubeSceneExtractorError):
    """Raised when scene detection fails"""

    pass


class TranscriptExtractionError(YouTubeSceneExtractorError):
    """Raised when transcript extraction fails"""

    pass


class OutputGenerationError(YouTubeSceneExtractorError):
    """Raised when output file generation fails"""

    pass


class ConfigurationError(YouTubeSceneExtractorError):
    """Raised when configuration is invalid"""

    pass


# Logging Configuration


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        """Format log record with colors"""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logger(
    name: str = "youtube_scene_extractor",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_colors: bool = True,
) -> logging.Logger:
    """
    Set up structured logging with console and optional file output

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for persistent logging
        enable_colors: Enable colored output for console (default: True)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger("my_module", level=logging.DEBUG)
        >>> logger.info("Processing started")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format: [2025-10-22 10:30:45] INFO - Message
    console_format = "[%(asctime)s] %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    if enable_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(console_format, datefmt=date_format)
    else:
        console_formatter = logging.Formatter(console_format, datefmt=date_format)

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets all levels

        # Detailed format for file: [2025-10-22 10:30:45] INFO [module.function:42] - Message
        file_format = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] - %(message)s"
        file_formatter = logging.Formatter(file_format, datefmt=date_format)

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name

    This function returns a logger that inherits from the root logger's configuration.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing video")
    """
    return logging.getLogger(f"youtube_scene_extractor.{name}")


def configure_default_logger(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Configure the default logger for the application

    This sets up the root logger with console and optional file output.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file

    Example:
        >>> configure_default_logger(level=logging.DEBUG, log_file="logs/app.log")
    """
    log_path = Path(log_file) if log_file else None
    setup_logger("youtube_scene_extractor", level=level, log_file=log_path)


# Progress logging helpers


class ProgressLogger:
    """Helper class for logging progress with consistent formatting"""

    def __init__(self, logger: logging.Logger, total_steps: int, task_name: str = "Processing"):
        """
        Initialize progress logger

        Args:
            logger: Logger instance to use
            total_steps: Total number of steps in the process
            task_name: Name of the task being processed
        """
        self.logger = logger
        self.total_steps = total_steps
        self.current_step = 0
        self.task_name = task_name
        self.start_time = datetime.now()

    def step(self, message: str = ""):
        """
        Log progress for a single step

        Args:
            message: Optional message to include with progress
        """
        self.current_step += 1
        percentage = (self.current_step / self.total_steps) * 100

        progress_msg = (
            f"{self.task_name}: [{self.current_step}/{self.total_steps}] ({percentage:.1f}%)"
        )
        if message:
            progress_msg += f" - {message}"

        self.logger.info(progress_msg)

    def complete(self, message: str = ""):
        """
        Log completion of the process

        Args:
            message: Optional completion message
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        complete_msg = f"{self.task_name} completed in {elapsed:.2f}s"
        if message:
            complete_msg += f" - {message}"

        self.logger.info(complete_msg)


# Default logger instance
default_logger = setup_logger()
