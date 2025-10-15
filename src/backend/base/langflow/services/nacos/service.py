"""Nacos service integration for Langflow."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from langflow.services.base import Service
from langflow.services.nacos.manager import NacosConfigManager, NacosServiceManager
from lfx.log.logger import logger

if TYPE_CHECKING:
    from langflow.services.settings.service import SettingsService


class NacosService(Service):
    """Langflow service for Nacos integration."""

    name = "nacos_service"

    def __init__(self, settings_service: SettingsService):
        """Initialize Nacos service.

        Args:
            settings_service: Langflow settings service
        """
        super().__init__()
        self.settings_service = settings_service
        self.config_manager: NacosConfigManager | None = None
        self.service_manager: NacosServiceManager | None = None
        self._enabled = False

    def initialize(self, **kwargs: Any) -> None:
        """Initialize Nacos service based on settings and environment variables."""
        try:
            # Try to get Nacos settings from environment variables first, then from settings service
            nacos_enabled = os.getenv("LANGFLOW_NACOS_ENABLED", "").lower() == "true" or getattr(
                self.settings_service.settings, "nacos_enabled", False
            )

            if not nacos_enabled:
                logger.info("Nacos service is disabled")
                return

            # Get server addresses from environment or settings
            server_addresses = os.getenv("NACOS_SERVER_ADDRESSES") or getattr(
                self.settings_service.settings, "nacos_server_addresses", None
            )

            # If no server addresses configured, do not initialize
            if not server_addresses:
                logger.info(
                    "Nacos server addresses not configured, skipping initialization")
                return

            # Get other configuration from environment or settings
            namespace = os.getenv("NACOS_NAMESPACE") or getattr(
                self.settings_service.settings, "nacos_namespace", "public"
            )
            username = os.getenv("NACOS_USERNAME") or getattr(
                self.settings_service.settings, "nacos_username", None
            )
            password = os.getenv("NACOS_PASSWORD") or getattr(
                self.settings_service.settings, "nacos_password", None
            )

            # Initialize config manager
            logger.info(
                f"Initializing Nacos config manager: {server_addresses}, namespace: {namespace}")
            self.config_manager = NacosConfigManager(
                server_addresses=server_addresses,
                namespace=namespace,
                username=username,
                password=password,
            )

            # Initialize service manager if service registration is enabled
            service_registration_enabled = (
                os.getenv("LANGFLOW_NACOS_SERVICE_REGISTRATION_ENABLED",
                          "").lower() == "true"
                or getattr(self.settings_service.settings, "nacos_service_registration_enabled", False)
            )

            if service_registration_enabled:
                service_name = os.getenv("LANGFLOW_NACOS_SERVICE_NAME") or getattr(
                    self.settings_service.settings, "nacos_service_name", "langflow"
                )
                service_ip = os.getenv("LANGFLOW_NACOS_SERVICE_IP") or getattr(
                    self.settings_service.settings, "nacos_service_ip", "127.0.0.1"
                )
                service_port_str = os.getenv("LANGFLOW_NACOS_SERVICE_PORT")
                service_port = (
                    int(service_port_str)
                    if service_port_str
                    else getattr(self.settings_service.settings, "nacos_service_port", 7860)
                )

                # Try to get metadata from environment (JSON string)
                metadata_str = os.getenv("LANGFLOW_NACOS_SERVICE_METADATA")
                if metadata_str:
                    import json

                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Failed to parse LANGFLOW_NACOS_SERVICE_METADATA as JSON, using empty dict")
                        metadata = {}
                else:
                    metadata = getattr(
                        self.settings_service.settings, "nacos_service_metadata", {})

                logger.info(
                    f"Initializing Nacos service registration: {service_name} at {service_ip}:{service_port}"
                )
                self.service_manager = NacosServiceManager(
                    server_addresses=server_addresses,
                    service_name=service_name,
                    ip=service_ip,
                    port=service_port,
                    namespace=namespace,
                    username=username,
                    password=password,
                    metadata=metadata,
                )
                if self.service_manager.register():
                    logger.info(
                        f"Nacos service registered successfully: {service_name}")
                else:
                    logger.warning(
                        f"Failed to register Nacos service: {service_name}")

            self._enabled = True
            logger.info("Nacos service initialized successfully")

        except ImportError:
            logger.warning(
                "nacos-sdk-python not installed, Nacos features disabled")
        except Exception:
            logger.exception("Failed to initialize Nacos service")

    def teardown(self) -> None:
        """Cleanup Nacos service resources."""
        try:
            if self.service_manager and self.service_manager._registered:
                self.service_manager.deregister()
                logger.info("Nacos service deregistered")
        except Exception:
            logger.exception("Error during Nacos service teardown")

    def get_config(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
    ) -> str | None:
        """Get configuration from Nacos.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value

        Returns:
            Configuration content as string
        """
        if not self._enabled or self.config_manager is None:
            logger.warning("Nacos service is not enabled")
            return None

        return self.config_manager.get_config(data_id, group, use_cache)

    def get_config_as_json(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """Get configuration from Nacos as JSON.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value

        Returns:
            Parsed JSON configuration
        """
        if not self._enabled or self.config_manager is None:
            logger.warning("Nacos service is not enabled")
            return None

        return self.config_manager.get_config_as_json(data_id, group, use_cache)

    def publish_config(
        self,
        data_id: str,
        content: str,
        group: str = "DEFAULT_GROUP",
    ) -> bool:
        """Publish configuration to Nacos.

        Args:
            data_id: Configuration data ID
            content: Configuration content
            group: Configuration group

        Returns:
            True if successful
        """
        if not self._enabled or self.config_manager is None:
            logger.warning("Nacos service is not enabled")
            return False

        return self.config_manager.publish_config(data_id, content, group)

    def add_config_watcher(
        self,
        data_id: str,
        callback: Any,
        group: str = "DEFAULT_GROUP",
    ) -> None:
        """Add configuration watcher.

        Args:
            data_id: Configuration data ID
            callback: Callback function for config changes
            group: Configuration group
        """
        if not self._enabled or self.config_manager is None:
            logger.warning("Nacos service is not enabled")
            return

        self.config_manager.add_config_watcher(data_id, callback, group)

    def discover_instances(
        self,
        service_name: str,
        healthy_only: bool = True,
        group_name: str = "DEFAULT_GROUP",
    ) -> list[dict[str, Any]]:
        """Discover service instances.

        Args:
            service_name: Service name to discover
            healthy_only: Only return healthy instances
            group_name: Service group name

        Returns:
            List of service instances
        """
        if not self._enabled or self.config_manager is None:
            logger.warning("Nacos service is not enabled")
            return []

        if self.service_manager:
            return self.service_manager.discover_instances(service_name, healthy_only, group_name)
        return []

    @property
    def enabled(self) -> bool:
        """Check if Nacos service is enabled."""
        return self._enabled
