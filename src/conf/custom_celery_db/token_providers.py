from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple



class TokenProvider(ABC):
    """Abstract base class for token providers."""

    @abstractmethod
    def get_token(self) -> str:
        """Get a valid token, refreshing if necessary."""
        raise NotImplementedError("Subclasses must implement get_token()")

    @abstractmethod
    def is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        raise NotImplementedError("Subclasses must implement is_token_expired()")

    @abstractmethod
    def force_refresh(self) -> str:
        """Force a token refresh and return the new token."""
        raise NotImplementedError("Subclasses must implement force_refresh()")



class StaticTokenProvider(TokenProvider):
    """Simple token provider that returns a static token (for testing)."""
    
    def __init__(self, token: str):
        self.token = token
    
    def get_token(self) -> str:
        return self.token
    
    def is_token_expired(self) -> bool:
        return False
    
    def force_refresh(self) -> str:
        return self.token


