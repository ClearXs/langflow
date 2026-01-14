"""Vercel AI streaming protocol."""

from langflow.services.base import Service
from langflow.services.settings.service import SettingsService


class VercelStreamingService(Service):
    """Vercel AI streaming protocol.

    TODO: Implement service logic from SurfSense migration.
    """

    name = "lvercel_lstreaming"

    def __init__(self, settings_service: SettingsService):
        """Initialize VercelStreamingService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()
