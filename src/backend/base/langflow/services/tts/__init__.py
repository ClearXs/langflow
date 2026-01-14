"""Text-to-speech service service."""

from .factory import TTSServiceFactory
from .service import TTSService

__all__ = ["TTSService", "TTSServiceFactory"]
