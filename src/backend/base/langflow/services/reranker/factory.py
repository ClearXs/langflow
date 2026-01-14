"""RerankerService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import RerankerService


class RerankerServiceFactory(ServiceFactory):
    """Factory for creating RerankerService instances."""

    def __init__(self):
        super().__init__(RerankerService)

    def create(self, settings_service: SettingsService):
        """Create a new RerankerService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            RerankerService instance
        """
        return RerankerService(settings_service)
