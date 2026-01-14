"""LLM service factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import LLMService


class LLMServiceFactory(ServiceFactory):
    """Factory for creating LLMService instances."""

    def __init__(self):
        super().__init__(LLMService)

    def create(self, settings_service: SettingsService):
        """Create a new LLMService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            LLMService instance
        """
        return LLMService(settings_service)
