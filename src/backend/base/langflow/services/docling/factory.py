"""DoclingService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import DoclingService


class DoclingServiceFactory(ServiceFactory):
    """Factory for creating DoclingService instances."""

    def __init__(self):
        super().__init__(DoclingService)

    def create(self, settings_service: SettingsService):
        """Create a new DoclingService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            DoclingService instance
        """
        return DoclingService(settings_service)
