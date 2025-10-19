from lfx.services.settings.service import SettingsService

from langflow.services.factory import ServiceFactory
from langflow.services.nacos.service import NacosService


class NacosServiceFactory(ServiceFactory):
    def __init__(self) -> None:
        super().__init__(NacosService)

    def create(self, settings_service: SettingsService):
        return NacosService(settings_service)
