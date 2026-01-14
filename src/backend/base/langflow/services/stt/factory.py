"""STTService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import STTService


class STTServiceFactory(ServiceFactory):
    """Factory for creating STTService instances."""

    def __init__(self):
        super().__init__(STTService)

    def create(self, settings_service: SettingsService):
        """Create a new STTService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            STTService instance
        """
        return STTService(settings_service)
