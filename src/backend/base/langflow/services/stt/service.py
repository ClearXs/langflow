"""Speech-to-text service."""

from langflow.services.base import Service
from langflow.services.settings.service import SettingsService


class STTService(Service):
    """Speech-to-text service.

    TODO: Implement service logic from SurfSense migration.
    """

    name = "ls_lt_lt"

    def __init__(self, settings_service: SettingsService):
        """Initialize STTService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()
