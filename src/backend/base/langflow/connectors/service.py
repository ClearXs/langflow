"""Multi-source search connector."""

from langflow.services.base import Service
from langflow.services.settings.service import SettingsService


class ConnectorService(Service):
    """Multi-source search connector.

    TODO: Implement service logic from SurfSense migration.
    """

    name = "lconnector"

    def __init__(self, settings_service: SettingsService):
        """Initialize ConnectorService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()
