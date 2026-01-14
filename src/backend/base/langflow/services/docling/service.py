"""Document processing and conversion."""

from langflow.services.base import Service
from langflow.services.settings.service import SettingsService


class DoclingService(Service):
    """Document processing and conversion.

    TODO: Implement service logic from SurfSense migration.
    """

    name = "ldocling"

    def __init__(self, settings_service: SettingsService):
        """Initialize DoclingService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()
