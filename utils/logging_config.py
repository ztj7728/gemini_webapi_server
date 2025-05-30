"""
Logging Configuration
=====================

Centralized logging configuration for the OpenAI-compatible API service.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    format_type: str = "standard"
) -> logging.Logger:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("standard" or "json")
    
    Returns:
        Configured logger instance
    """
    # Get log level from environment or parameter
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure log format
    if format_type == "json":
        # JSON format for production
        log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    else:
        # Standard format for development
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout
    )
    
    # Get application logger
    logger = logging.getLogger("openai_api")
    
    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {level}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(f"openai_api.{name}")