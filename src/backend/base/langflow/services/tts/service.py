"""Text-to-speech service."""

from langflow.services.base import Service
from langflow.services.settings.service import SettingsService


class TTSService(Service):
    """Text-to-speech service.

    TODO: Implement service logic from SurfSense migration.
    """

    name = "lt_lt_ls"

    def __init__(self, settings_service: SettingsService):
        """Initialize TTSService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()
