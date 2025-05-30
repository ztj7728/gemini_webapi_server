"""
Server Startup Script
=====================

Startup script for the OpenAI-compatible API server with proper configuration validation.
"""

import asyncio
import sys
from pathlib import Path

import uvicorn

from config import config
from utils.logging_config import setup_logging


def validate_environment():
    """Validate environment configuration before starting."""
    logger = setup_logging()
    
    logger.info("Validating environment configuration...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        logger.error(".env file not found. Please create one with SECURE_1PSID and SECURE_1PSIDTS")
        return False
    
    # Validate required configuration
    if not config.validate():
        logger.error("Missing required configuration:")
        if not config.SECURE_1PSID:
            logger.error("  - SECURE_1PSID not set")
        if not config.SECURE_1PSIDTS:
            logger.error("  - SECURE_1PSIDTS not set")
        logger.error("Please run get_certificate.py to obtain credentials")
        return False
    
    # Log configuration summary
    logger.info("Configuration summary:")
    for key, value in config.get_summary().items():
        logger.info(f"  {key}: {value}")
    
    return True


def main():
    """Main entry point."""
    if not validate_environment():
        sys.exit(1)
    
    logger = setup_logging()
    logger.info("Starting OpenAI-Compatible API Server...")
    
    # Start the server
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()