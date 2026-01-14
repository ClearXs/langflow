"""VercelStreamingService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import VercelStreamingService


class VercelStreamingServiceFactory(ServiceFactory):
    """Factory for creating VercelStreamingService instances."""

    def __init__(self):
        super().__init__(VercelStreamingService)

    def create(self, settings_service: SettingsService):
        """Create a new VercelStreamingService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            VercelStreamingService instance
        """
        return VercelStreamingService(settings_service)
