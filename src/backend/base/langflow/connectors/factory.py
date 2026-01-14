"""ConnectorService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import ConnectorService


class ConnectorServiceFactory(ServiceFactory):
    """Factory for creating ConnectorService instances."""

    def __init__(self):
        super().__init__(ConnectorService)

    def create(self, settings_service: SettingsService):
        """Create a new ConnectorService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            ConnectorService instance
        """
        return ConnectorService(settings_service)
