"""
Authentication Service
======================

Handles Bearer token authentication for the OpenAI-compatible API.
For MVP, uses a simple in-memory store with configurable API keys.
"""

import hashlib
import logging
import os
import secrets
from typing import Dict, Optional, Set

from models.openai_models import UserContext

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling API key authentication."""
    
    def __init__(self):
        self.api_keys: Dict[str, UserContext] = {}
        self._initialize_default_keys()
    
    def _initialize_default_keys(self):
        """Initialize default API keys from environment or create demo keys."""
        # Check for environment-provided API keys
        env_api_keys = os.getenv("API_KEYS", "")
        
        if env_api_keys:
            # Parse comma-separated API keys from environment
            for key in env_api_keys.split(","):
                key = key.strip()
                if key and key.startswith("sk-"):
                    self._add_api_key(key, f"user_{hashlib.md5(key.encode()).hexdigest()[:8]}")
        else:
            # Create default demo API keys for development
            demo_keys = [
                "sk-demo1234567890abcdef1234567890abcdef1234567890abcdef",
                "sk-test1234567890abcdef1234567890abcdef1234567890abcdef"
            ]
            
            for key in demo_keys:
                self._add_api_key(key, f"demo_user_{hashlib.md5(key.encode()).hexdigest()[:8]}")
        
        logger.info(f"Initialized {len(self.api_keys)} API keys")
        
        # Log the demo keys for development (remove in production)
        if not env_api_keys:
            logger.info("Demo API keys for testing:")
            for key in self.api_keys.keys():
                logger.info(f"  {key}")
    
    def _add_api_key(self, api_key: str, user_id: str, permissions: Optional[list] = None):
        """Add an API key to the store."""
        if permissions is None:
            permissions = ["chat.completions", "models.list"]
        
        # Hash the API key for storage (in production, store only hashes)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        user_context = UserContext(
            user_id=user_id,
            api_key_id=key_hash[:16],
            permissions=permissions
        )
        
        # For MVP, store the actual key (in production, store only hash)
        self.api_keys[api_key] = user_context
    
    async def authenticate(self, token: str) -> Optional[UserContext]:
        """Authenticate a Bearer token and return user context."""
        try:
            # Validate token format
            if not token or not token.startswith("sk-"):
                logger.warning(f"Invalid token format: {token[:10]}...")
                return None
            
            # Check if token exists in our store
            user_context = self.api_keys.get(token)
            if user_context:
                logger.debug(f"Authenticated user: {user_context.user_id}")
                return user_context
            
            logger.warning(f"Unknown API key: {token[:10]}...")
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
    
    def generate_api_key(self, user_id: str, permissions: Optional[list] = None) -> str:
        """Generate a new API key for a user."""
        # Generate a secure random API key
        random_part = secrets.token_urlsafe(32)
        api_key = f"sk-{random_part}"
        
        self._add_api_key(api_key, user_id, permissions)
        
        logger.info(f"Generated new API key for user: {user_id}")
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self.api_keys:
            user_context = self.api_keys[api_key]
            del self.api_keys[api_key]
            logger.info(f"Revoked API key for user: {user_context.user_id}")
            return True
        return False
    
    def list_api_keys(self) -> Dict[str, str]:
        """List all API keys and their associated users (for admin purposes)."""
        return {
            key: context.user_id 
            for key, context in self.api_keys.items()
        }
    
    def validate_permission(self, user_context: UserContext, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in user_context.permissions