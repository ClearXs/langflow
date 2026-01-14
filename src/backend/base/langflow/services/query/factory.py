"""QueryService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import QueryService


class QueryServiceFactory(ServiceFactory):
    """Factory for creating QueryService instances."""

    def __init__(self):
        super().__init__(QueryService)

    def create(self, settings_service: SettingsService):
        """Create a new QueryService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            QueryService instance
        """
        return QueryService(settings_service)
