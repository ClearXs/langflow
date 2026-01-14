"""TTSService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import TTSService


class TTSServiceFactory(ServiceFactory):
    """Factory for creating TTSService instances."""

    def __init__(self):
        super().__init__(TTSService)

    def create(self, settings_service: SettingsService):
        """Create a new TTSService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            TTSService instance
        """
        return TTSService(settings_service)
