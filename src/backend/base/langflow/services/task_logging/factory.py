"""TaskLoggingService factory."""

from langflow.services.factory import ServiceFactory
from langflow.services.settings.service import SettingsService

from .service import TaskLoggingService


class TaskLoggingServiceFactory(ServiceFactory):
    """Factory for creating TaskLoggingService instances."""

    def __init__(self):
        super().__init__(TaskLoggingService)

    def create(self, settings_service: SettingsService):
        """Create a new TaskLoggingService instance.

        Args:
            settings_service: Settings service instance

        Returns:
            TaskLoggingService instance
        """
        return TaskLoggingService(settings_service)
