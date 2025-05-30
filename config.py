"""
Configuration Management
========================

Centralized configuration for the OpenAI-compatible API service.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Gemini Configuration
    SECURE_1PSID: Optional[str] = os.getenv("SECURE_1PSID")
    SECURE_1PSIDTS: Optional[str] = os.getenv("SECURE_1PSIDTS")
    PROXY: Optional[str] = os.getenv("PROXY")
    
    # Authentication Configuration
    API_KEYS: str = os.getenv("API_KEYS", "")
    
    # Rate Limiting Configuration
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", "10"))
    
    # CORS Configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.SECURE_1PSID or not cls.SECURE_1PSIDTS:
            return False
        return True
    
    @classmethod
    def get_summary(cls) -> dict:
        """Get configuration summary (without sensitive data)."""
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "log_level": cls.LOG_LEVEL,
            "proxy_enabled": bool(cls.PROXY and cls.PROXY != "None"),
            "rate_limit_per_minute": cls.RATE_LIMIT_PER_MINUTE,
            "cors_origins": cls.CORS_ORIGINS,
            "credentials_configured": bool(cls.SECURE_1PSID and cls.SECURE_1PSIDTS)
        }


# Global config instance
config = Config()