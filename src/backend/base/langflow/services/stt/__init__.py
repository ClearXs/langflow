"""Speech-to-text service service."""

from .factory import STTServiceFactory
from .service import STTService

__all__ = ["STTService", "STTServiceFactory"]
