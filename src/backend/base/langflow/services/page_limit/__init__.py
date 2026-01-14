"""Page quota management service."""

from .factory import PageLimitServiceFactory
from .service import PageLimitService

__all__ = ["PageLimitService", "PageLimitServiceFactory"]
