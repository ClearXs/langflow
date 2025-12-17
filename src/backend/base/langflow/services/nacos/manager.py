"""Nacos configuration and service management."""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from lfx.log.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

from v2.nacos import (
    ClientConfigBuilder,
    ConfigParam,
    DeregisterInstanceParam,
    ListInstanceParam,
    NacosConfigService,
    NacosNamingService,
    RegisterInstanceParam,
)

# Global event loop for Nacos async operations (running in dedicated thread)
_nacos_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_nacos_loop():
    """Get or create dedicated event loop for Nacos operations."""
    global _nacos_loop
    if _nacos_loop is None or _nacos_loop.is_closed():
        with _loop_lock:
            if _nacos_loop is None or _nacos_loop.is_closed():
                _nacos_loop = asyncio.new_event_loop()

                # Start the loop in a dedicated thread
                def run_loop():
                    asyncio.set_event_loop(_nacos_loop)
                    _nacos_loop.run_forever()

                thread = threading.Thread(target=run_loop, daemon=True, name="nacos-event-loop")
                thread.start()
    return _nacos_loop


def _run_async(coro):
    """Safely run async coroutine in sync context.

    This helper uses a dedicated event loop running in a separate thread
    to avoid conflicts with the main FastAPI event loop.
    """
    try:
        # Try to get the current running loop
        asyncio.get_running_loop()
        # We're in an async context, use the dedicated Nacos loop
        nacos_loop = _get_nacos_loop()
        future = asyncio.run_coroutine_threadsafe(coro, nacos_loop)
        return future.result(timeout=30)  # 30 second timeout
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        return asyncio.run(coro)


class NacosConfigManager:
    """Nacos configuration manager with caching and watch capabilities using v2 API."""

    def __init__(
        self,
        server_addresses: str,
        namespace: str = "public",
        username: str | None = None,
        password: str | None = None,
        timeout: int = 3,
    ) -> None:
        """Initialize Nacos configuration manager.

        Args:
            server_addresses: Nacos server addresses (e.g., "localhost:8848")
            namespace: Nacos namespace ID
            username: Nacos username for authentication
            password: Nacos password for authentication
            timeout: Default timeout for operations in seconds
        """
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.timeout = timeout
        self._config_cache: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._watchers: dict[str, list] = {}
        self._config_client: NacosConfigService | None = None

        try:
            # Build client configuration using v2 ClientConfigBuilder
            self.client_config = (
                ClientConfigBuilder()
                .server_address(server_addresses)
                .namespace_id(namespace)
                .username(username)
                .password(password)
                .build()
            )
            logger.info(f"Nacos v2 config client config built: {server_addresses}, namespace: {namespace}")
        except Exception:
            logger.exception("Failed to build Nacos v2 client configuration")
            raise

    def _ensure_client(self) -> None:
        """Ensure async config client is initialized."""
        if self._config_client is None:
            self._config_client = _run_async(NacosConfigService.create_config_service(self.client_config))
            logger.info("Nacos v2 config client initialized")

    def get_config(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
        timeout: int | None = None,
    ) -> str | None:
        """Get configuration from Nacos using v2 API.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value
            timeout: Timeout in seconds (uses default if None)

        Returns:
            Configuration content as string, or None if not found
        """
        self._ensure_client()
        cache_key = f"{group}:{data_id}"

        # Try cache first if enabled
        if use_cache:
            with self._lock:
                if cache_key in self._config_cache:
                    logger.debug(f"Config cache hit: {cache_key}")
                    return self._config_cache[cache_key]

        # Fetch from Nacos using v2 async API
        try:
            config = _run_async(
                self._config_client.get_config(
                    ConfigParam(data_id=data_id, group=group, timeout_ms=(timeout or self.timeout) * 1000)
                )
            )

            # Update cache
            if config and use_cache:
                with self._lock:
                    self._config_cache[cache_key] = config

            logger.info(f"Config fetched from Nacos v2: {cache_key}")
            return config
        except Exception:
            logger.exception(f"Failed to get config: {cache_key}")
            return None

    def get_config_as_json(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
        timeout: int | None = None,
    ) -> dict[str, Any] | None:
        """Get configuration from Nacos and parse as JSON.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value
            timeout: Timeout in seconds

        Returns:
            Parsed JSON configuration, or None if not found or invalid JSON
        """
        config = self.get_config(data_id, group, use_cache, timeout)
        if config is None:
            return None

        try:
            return json.loads(config)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse config as JSON: {group}:{data_id}")
            return None

    def publish_config(
        self,
        data_id: str,
        content: str,
        group: str = "DEFAULT_GROUP",
        timeout: int | None = None,
    ) -> bool:
        """Publish configuration to Nacos using v2 API.

        Args:
            data_id: Configuration data ID
            content: Configuration content
            group: Configuration group
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        self._ensure_client()

        try:
            result = _run_async(
                self._config_client.publish_config(ConfigParam(data_id=data_id, group=group, content=content))
            )

            # Update cache
            if result:
                cache_key = f"{group}:{data_id}"
                with self._lock:
                    self._config_cache[cache_key] = content
                logger.info(f"Config published to Nacos v2: {cache_key}")

            return result
        except Exception:
            logger.exception(f"Failed to publish config: {group}:{data_id}")
            return False

    def remove_config(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        timeout: int | None = None,
    ) -> bool:
        """Remove configuration from Nacos using v2 API.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        self._ensure_client()

        try:
            result = _run_async(self._config_client.remove_config(ConfigParam(data_id=data_id, group=group)))

            # Clear cache
            if result:
                cache_key = f"{group}:{data_id}"
                with self._lock:
                    self._config_cache.pop(cache_key, None)
                logger.info(f"Config removed from Nacos v2: {cache_key}")

            return result
        except Exception:
            logger.exception(f"Failed to remove config: {group}:{data_id}")
            return False

    def add_config_watcher(
        self,
        data_id: str,
        callback: Callable[[dict[str, Any]], None],
        group: str = "DEFAULT_GROUP",
    ) -> None:
        """Add a configuration watcher using v2 API.

        Args:
            data_id: Configuration data ID
            callback: Callback function to be called when config changes
            group: Configuration group
        """
        self._ensure_client()
        cache_key = f"{group}:{data_id}"

        async def async_config_listener(tenant: str, listener_data_id: str, listener_group: str, content: str) -> None:
            """Async config listener for v2 API."""
            try:
                # Update cache
                with self._lock:
                    self._config_cache[cache_key] = content

                logger.info(f"Config changed: {cache_key}")

                # Call user callback with consistent format
                args = {"content": content}
                callback(args)
            except Exception:
                logger.exception(f"Error in config watcher callback: {cache_key}")

        try:
            # Use v2 async API to add listener
            _run_async(self._config_client.add_listener(data_id, group, async_config_listener))
            with self._lock:
                if cache_key not in self._watchers:
                    self._watchers[cache_key] = []
                self._watchers[cache_key].append(async_config_listener)
            logger.info(f"Config watcher added using v2 API: {cache_key}")
        except Exception:
            logger.exception(f"Failed to add config watcher: {cache_key}")

    def remove_config_watcher(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        remove_all: bool = True,
    ) -> None:
        """Remove configuration watcher(s) using v2 API.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            remove_all: If True, remove all watchers for this config
        """
        self._ensure_client()
        cache_key = f"{group}:{data_id}"

        try:
            with self._lock:
                watchers = self._watchers.get(cache_key, [])
                if not watchers:
                    return

                if remove_all:
                    for watcher in watchers:
                        _run_async(self._config_client.remove_listener(data_id, group, watcher))
                    self._watchers.pop(cache_key, None)
                    logger.info(f"All config watchers removed using v2 API: {cache_key}")
                elif watchers:
                    watcher = watchers.pop()
                    _run_async(self._config_client.remove_listener(data_id, group, watcher))
                    logger.info(f"Config watcher removed using v2 API: {cache_key}")
        except Exception:
            logger.exception(f"Failed to remove config watcher: {cache_key}")

    def clear_cache(self, data_id: str | None = None, group: str = "DEFAULT_GROUP") -> None:
        """Clear configuration cache.

        Args:
            data_id: If specified, clear only this config's cache. If None, clear all.
            group: Configuration group (only used if data_id is specified)
        """
        with self._lock:
            if data_id is not None:
                cache_key = f"{group}:{data_id}"
                self._config_cache.pop(cache_key, None)
                logger.debug(f"Config cache cleared: {cache_key}")
            else:
                self._config_cache.clear()
                logger.debug("All config cache cleared")


class NacosServiceManager:
    """Nacos service registration and discovery manager using v2 API."""

    def __init__(
        self,
        server_addresses: str,
        service_name: str,
        ip: str,
        port: int,
        namespace: str = "public",
        username: str | None = None,
        password: str | None = None,
        cluster_name: str = "DEFAULT",
        group_name: str = "DEFAULT_GROUP",
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
        ephemeral: bool = True,
    ) -> None:
        """Initialize Nacos service manager.

        Args:
            server_addresses: Nacos server addresses
            service_name: Service name to register
            ip: Service IP address
            port: Service port
            namespace: Nacos namespace ID
            username: Nacos username
            password: Nacos password
            cluster_name: Cluster name
            group_name: Service group name
            weight: Service instance weight (0.0-1.0)
            metadata: Service metadata
            ephemeral: Whether this is an ephemeral instance
        """
        self.server_addresses = server_addresses
        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.namespace = namespace
        self.cluster_name = cluster_name
        self.group_name = group_name
        self.weight = weight
        self.metadata = metadata or {}
        self.ephemeral = ephemeral
        self._registered = False
        self._naming_client: NacosNamingService | None = None

        try:
            # Build client configuration using v2 ClientConfigBuilder
            self.client_config = (
                ClientConfigBuilder()
                .server_address(server_addresses)
                .namespace_id(namespace)
                .username(username)
                .password(password)
                .build()
            )
            logger.info(f"Nacos v2 naming client config built: {server_addresses}, namespace: {namespace}")
        except Exception:
            logger.exception("Failed to build Nacos v2 naming client configuration")
            raise

    def _ensure_client(self) -> None:
        """Ensure async naming client is initialized."""
        if self._naming_client is None:
            self._naming_client = _run_async(NacosNamingService.create_naming_service(self.client_config))
            logger.info("Nacos v2 naming client initialized")

    def register(self) -> bool:
        """Register service instance to Nacos using v2 API.

        Returns:
            True if successful, False otherwise
        """
        if self._registered:
            logger.warning(f"Service {self.service_name} already registered")
            return True

        self._ensure_client()

        try:
            # Use v2 async API to register service instance
            result = _run_async(
                self._naming_client.register_instance(
                    request=RegisterInstanceParam(
                        service_name=self.service_name,
                        group_name=self.group_name,
                        ip=self.ip,
                        port=self.port,
                        cluster_name=self.cluster_name,
                        weight=self.weight,
                        metadata=self.metadata,
                        enabled=True,
                        healthy=True,
                        ephemeral=self.ephemeral,
                    )
                )
            )

            if result:
                self._registered = True
                logger.info(
                    f"Service registered using v2 API: {self.service_name} at {self.ip}:{self.port} "
                    f"(namespace: {self.namespace}, group: {self.group_name})"
                )
            else:
                logger.error(f"Failed to register service: {self.service_name}")

            return result
        except Exception as e:
            logger.exception(f"Failed to register service: {self.service_name} {e}")
            return False

    def deregister(self) -> bool:
        """Deregister service instance from Nacos using v2 API.

        Returns:
            True if successful, False otherwise
        """
        if not self._registered:
            logger.warning(f"Service {self.service_name} not registered")
            return True

        self._ensure_client()

        try:
            # Use v2 async API to deregister service instance
            result = _run_async(
                self._naming_client.deregister_instance(
                    request=DeregisterInstanceParam(
                        service_name=self.service_name,
                        group_name=self.group_name,
                        ip=self.ip,
                        port=self.port,
                        cluster_name=self.cluster_name,
                        ephemeral=self.ephemeral,
                    )
                )
            )

            if result:
                self._registered = False
                logger.info(f"Service deregistered using v2 API: {self.service_name}")
            else:
                logger.error(f"Failed to deregister service: {self.service_name}")

            return result
        except Exception:
            logger.exception(f"Failed to deregister service: {self.service_name}")
            return False

    # Heartbeat is automatically handled by v2 Nacos SDK, no manual heartbeat method needed

    def discover_instances(
        self,
        service_name: str | None = None,
        healthy_only: bool = True,
        group_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Discover service instances using v2 API.

        Args:
            service_name: Service name to discover (uses self.service_name if None)
            healthy_only: Only return healthy instances
            group_name: Service group name (uses self.group_name if None)

        Returns:
            List of service instance information
        """
        self._ensure_client()
        service_name = service_name or self.service_name
        group_name = group_name or self.group_name

        try:
            # Use v2 async API to list instances
            instances = _run_async(
                self._naming_client.list_instances(
                    ListInstanceParam(service_name=service_name, group_name=group_name, healthy_only=healthy_only)
                )
            )
            logger.debug(f"Discovered {len(instances)} instances for {service_name} using v2 API")
            return instances
        except Exception:
            logger.exception(f"Failed to discover instances: {service_name}")
            return []

    def list_services(
        self,
        group_name: str | None = None,
        page_no: int = 1,
        page_size: int = 100,
    ) -> list[str]:
        """List all services in Nacos using v2 API.

        Args:
            group_name: Service group name (uses self.group_name if None)
            page_no: Page number for pagination (default: 1)
            page_size: Page size for pagination (default: 100)

        Returns:
            List of service names
        """
        self._ensure_client()
        group_name = group_name or self.group_name

        try:
            from v2.nacos.naming.model.naming_param import ListServiceParam

            # Use v2 async API to list services
            service_list = _run_async(
                self._naming_client.list_services(
                    ListServiceParam(
                        namespace_id=self.namespace,
                        group_name=group_name,
                        page_no=page_no,
                        page_size=page_size,
                    )
                )
            )

            # Extract service names from the response
            # The response has 'services' field, not 'doms'
            services = service_list.services if hasattr(service_list, "services") else []
            logger.debug(
                f"Listed {len(services)} services from Nacos using v2 API "
                f"(namespace: {self.namespace}, group: {group_name})"
            )
            return services
        except Exception:
            logger.exception("Failed to list services from Nacos")
            return []

    def subscribe(
        self,
        callback: Callable[[list[dict[str, Any]]], None],
        service_name: str | None = None,
        group_name: str | None = None,
    ) -> None:
        """Subscribe to service changes.

        Args:
            callback: Callback function to be called when service instances change
            service_name: Service name to subscribe (uses self.service_name if None)
            group_name: Service group name (uses self.group_name if None)
        """
        service_name = service_name or self.service_name
        group_name = group_name or self.group_name

        def wrapper(instances: list[dict[str, Any]]) -> None:
            """Wrapper for user callback."""
            logger.info(f"Service instances changed: {service_name}, count: {len(instances)}")
            try:
                callback(instances)
            except Exception:
                logger.exception(f"Error in service subscription callback: {service_name}")

        try:
            self.client.subscribe(
                service_name=service_name,
                callback=wrapper,
                group_name=group_name,
            )
            logger.info(f"Subscribed to service: {service_name}")
        except Exception:
            logger.exception(f"Failed to subscribe to service: {service_name}")

    def unsubscribe(
        self,
        service_name: str | None = None,
        group_name: str | None = None,
    ) -> None:
        """Unsubscribe from service changes.

        Args:
            service_name: Service name to unsubscribe (uses self.service_name if None)
            group_name: Service group name (uses self.group_name if None)
        """
        service_name = service_name or self.service_name
        group_name = group_name or self.group_name

        try:
            self.client.unsubscribe(service_name=service_name, group_name=group_name)
            logger.info(f"Unsubscribed from service: {service_name}")
        except Exception:
            logger.exception(f"Failed to unsubscribe from service: {service_name}")

    @contextmanager
    def service_context(self):
        """Context manager for automatic service registration and deregistration.

        Usage:
            with service_manager.service_context():
                # Your service code here
                pass
        """
        try:
            self.register()
            yield self
        finally:
            self.deregister()

    def __enter__(self):
        """Support with statement."""
        self.register()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support with statement."""
        self.deregister()
