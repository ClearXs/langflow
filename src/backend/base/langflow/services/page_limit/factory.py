"""PageLimitService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import PageLimitService


class PageLimitServiceFactory(ServiceFactory):
    """Factory for creating PageLimitService instances."""

    def __init__(self):
        super().__init__(PageLimitService)

    def create(self, settings_service: SettingsService):
        """Create a new PageLimitService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            PageLimitService instance
        """
        return PageLimitService(settings_service)
