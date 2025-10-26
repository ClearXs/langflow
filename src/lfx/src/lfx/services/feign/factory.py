"""Feign service factory."""

from langflow.services.deps import get_nacos_service

from lfx.services.factory import ServiceFactory
from lfx.services.feign.service import FeignService


class FeignServiceFactory(ServiceFactory):
    """Factory for creating FeignService instances."""

    def __init__(self):
        super().__init__()
        self.service_class = FeignService

    def create(self, settings_service=None):  # noqa: ARG002
        """Create FeignService instance.

        Args:
            settings_service: Not used, for compatibility

        Returns:
            FeignService instance
        """
        nacos_service = get_nacos_service()
        return FeignService(nacos_service=nacos_service)
