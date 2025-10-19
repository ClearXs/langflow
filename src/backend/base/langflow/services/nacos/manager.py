"""Nacos configuration and service management."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable


try:
    import nacos
except ImportError:
    nacos = None  # type: ignore[assignment]
    logger.warning("nacos-sdk-python not installed. Nacos features will be disabled.")


class NacosConfigManager:
    """Nacos configuration manager with caching and watch capabilities."""

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
        if nacos is None:
            msg = "nacos-sdk-python is not installed. Install it with: pip install nacos-sdk-python"
            raise ImportError(msg)

        self.server_addresses = server_addresses
        self.namespace = namespace
        self.timeout = timeout
        self._config_cache: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._watchers: dict[str, list] = {}

        try:
            self.client = nacos.NacosClient(
                server_addresses=server_addresses,
                namespace=namespace,
                username=username,
                password=password,
            )
            logger.info(f"Nacos client initialized: {server_addresses}, namespace: {namespace}")
        except Exception:
            logger.exception("Failed to initialize Nacos client")
            raise

    def get_config(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
        timeout: int | None = None,
    ) -> str | None:
        """Get configuration from Nacos.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value
            timeout: Timeout in seconds (uses default if None)

        Returns:
            Configuration content as string, or None if not found
        """
        cache_key = f"{group}:{data_id}"

        # Try cache first if enabled
        if use_cache:
            with self._lock:
                if cache_key in self._config_cache:
                    logger.debug(f"Config cache hit: {cache_key}")
                    return self._config_cache[cache_key]

        # Fetch from Nacos
        try:
            timeout = timeout or self.timeout
            config = self.client.get_config(data_id, group, timeout)

            # Update cache
            with self._lock:
                self._config_cache[cache_key] = config

            logger.info(f"Config fetched from Nacos: {cache_key}")
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
        """Publish configuration to Nacos.

        Args:
            data_id: Configuration data ID
            content: Configuration content
            group: Configuration group
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = timeout or self.timeout
            result = self.client.publish_config(data_id, group, content, timeout=timeout)

            # Update cache
            if result:
                cache_key = f"{group}:{data_id}"
                with self._lock:
                    self._config_cache[cache_key] = content
                logger.info(f"Config published to Nacos: {cache_key}")

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
        """Remove configuration from Nacos.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = timeout or self.timeout
            result = self.client.remove_config(data_id, group, timeout=timeout)

            # Clear cache
            if result:
                cache_key = f"{group}:{data_id}"
                with self._lock:
                    self._config_cache.pop(cache_key, None)
                logger.info(f"Config removed from Nacos: {cache_key}")

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
        """Add a configuration watcher.

        Args:
            data_id: Configuration data ID
            callback: Callback function to be called when config changes
            group: Configuration group
        """
        cache_key = f"{group}:{data_id}"

        def wrapper(args: dict[str, Any]) -> None:
            """Wrapper to update cache and call user callback."""
            content = args.get("content")
            with self._lock:
                self._config_cache[cache_key] = content

            logger.info(f"Config changed: {cache_key}")

            try:
                callback(args)
            except Exception:
                logger.exception(f"Error in config watcher callback: {cache_key}")

        try:
            self.client.add_config_watcher(data_id, group, wrapper)
            with self._lock:
                if cache_key not in self._watchers:
                    self._watchers[cache_key] = []
                self._watchers[cache_key].append(wrapper)
            logger.info(f"Config watcher added: {cache_key}")
        except Exception:
            logger.exception(f"Failed to add config watcher: {cache_key}")

    def remove_config_watcher(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        remove_all: bool = True,
    ) -> None:
        """Remove configuration watcher(s).

        Args:
            data_id: Configuration data ID
            group: Configuration group
            remove_all: If True, remove all watchers for this config
        """
        cache_key = f"{group}:{data_id}"

        try:
            with self._lock:
                watchers = self._watchers.get(cache_key, [])
                if not watchers:
                    return

                if remove_all:
                    for watcher in watchers:
                        self.client.remove_config_watcher(data_id, group, watcher)
                    self._watchers.pop(cache_key, None)
                    logger.info(f"All config watchers removed: {cache_key}")
                elif watchers:
                    watcher = watchers.pop()
                    self.client.remove_config_watcher(data_id, group, watcher)
                    logger.info(f"Config watcher removed: {cache_key}")
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
    """Nacos service registration and discovery manager."""

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
        if nacos is None:
            msg = "nacos-sdk-python is not installed. Install it with: pip install nacos-sdk-python"
            raise ImportError(msg)

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

        try:
            self.client = nacos.NacosClient(
                server_addresses=server_addresses,
                namespace=namespace,
                username=username,
                password=password,
            )
            logger.info(f"Nacos service client initialized: {server_addresses}")
        except Exception:
            logger.exception("Failed to initialize Nacos service client")
            raise

    def register(self) -> bool:
        """Register service instance to Nacos.

        Returns:
            True if successful, False otherwise
        """
        if self._registered:
            logger.warning(f"Service {self.service_name} already registered")
            return True

        try:
            self.client.add_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
                cluster_name=self.cluster_name,
                weight=self.weight,
                metadata=self.metadata,
                enable=True,
                healthy=True,
                ephemeral=self.ephemeral,
                group_name=self.group_name,
            )
            self._registered = True
            logger.info(
                f"Service registered: {self.service_name} at {self.ip}:{self.port} "
                f"(namespace: {self.namespace}, group: {self.group_name})"
            )
            return True
        except Exception:
            logger.exception(f"Failed to register service: {self.service_name}")
            return False

    def deregister(self) -> bool:
        """Deregister service instance from Nacos.

        Returns:
            True if successful, False otherwise
        """
        if not self._registered:
            logger.warning(f"Service {self.service_name} not registered")
            return True

        try:
            self.client.remove_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
                cluster_name=self.cluster_name,
                group_name=self.group_name,
            )
            self._registered = False
            logger.info(f"Service deregistered: {self.service_name}")
            return True
        except Exception:
            logger.exception(f"Failed to deregister service: {self.service_name}")
            return False

    def heartbeat(self) -> bool:
        """Send heartbeat to Nacos (for non-ephemeral instances).

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.send_heartbeat(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
                cluster_name=self.cluster_name,
                weight=self.weight,
                metadata=self.metadata,
                group_name=self.group_name,
            )
            logger.debug(f"Heartbeat sent for service: {self.service_name}")
            return True
        except Exception:
            logger.exception(f"Failed to send heartbeat: {self.service_name}")
            return False

    def discover_instances(
        self,
        service_name: str | None = None,
        healthy_only: bool = True,
        group_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Discover service instances.

        Args:
            service_name: Service name to discover (uses self.service_name if None)
            healthy_only: Only return healthy instances
            group_name: Service group name (uses self.group_name if None)

        Returns:
            List of service instance information
        """
        service_name = service_name or self.service_name
        group_name = group_name or self.group_name

        try:
            instances = self.client.list_naming_instance(
                service_name=service_name,
                healthy_only=healthy_only,
                group_name=group_name,
            )
            logger.debug(f"Discovered {len(instances.get('hosts', []))} instances for {service_name}")
            return instances.get("hosts", [])
        except Exception:
            logger.exception(f"Failed to discover instances: {service_name}")
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
