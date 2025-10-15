"""Nacos configuration and service discovery utilities for LFX."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from typing import Any, Callable

from lfx.log.logger import logger

try:
    import nacos
    NACOS_AVAILABLE = True
except ImportError:
    NACOS_AVAILABLE = False
    logger.warning(
        "nacos-sdk-python not installed. Nacos features will be disabled.")


class LFXNacosConfig:
    """Lightweight Nacos configuration manager for LFX."""

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
            username: Nacos username
            password: Nacos password
            timeout: Default timeout for operations
        """
        if not NACOS_AVAILABLE:
            msg = "nacos-sdk-python is not installed. Install with: uv add nacos-sdk-python"
            raise ImportError(msg)

        self.server_addresses = server_addresses
        self.namespace = namespace
        self.timeout = timeout
        self._cache: dict[str, Any] = {}
        self._lock = threading.RLock()

        try:
            self.client = nacos.NacosClient(
                server_addresses=server_addresses,
                namespace=namespace,
                username=username,
                password=password,
            )
            logger.info(f"LFX Nacos client initialized: {server_addresses}")
        except Exception:
            logger.exception("Failed to initialize Nacos client")
            raise

    def get(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
    ) -> str | None:
        """Get configuration value.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value

        Returns:
            Configuration content
        """
        cache_key = f"{group}:{data_id}"

        if use_cache:
            with self._lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]

        try:
            config = self.client.get_config(data_id, group, self.timeout)
            with self._lock:
                self._cache[cache_key] = config
            return config
        except Exception:
            logger.exception(f"Failed to get config: {cache_key}")
            return None

    def get_json(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """Get configuration as JSON.

        Args:
            data_id: Configuration data ID
            group: Configuration group
            use_cache: Whether to use cached value

        Returns:
            Parsed JSON configuration
        """
        config = self.get(data_id, group, use_cache)
        if config is None:
            return None

        try:
            return json.loads(config)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse JSON config: {group}:{data_id}")
            return None

    def set(
        self,
        data_id: str,
        content: str,
        group: str = "DEFAULT_GROUP",
    ) -> bool:
        """Set configuration value.

        Args:
            data_id: Configuration data ID
            content: Configuration content
            group: Configuration group

        Returns:
            True if successful
        """
        try:
            result = self.client.publish_config(
                data_id, group, content, timeout=self.timeout)
            if result:
                cache_key = f"{group}:{data_id}"
                with self._lock:
                    self._cache[cache_key] = content
            return result
        except Exception:
            logger.exception(f"Failed to set config: {group}:{data_id}")
            return False

    def watch(
        self,
        data_id: str,
        callback: Callable[[dict[str, Any]], None],
        group: str = "DEFAULT_GROUP",
    ) -> None:
        """Watch configuration changes.

        Args:
            data_id: Configuration data ID
            callback: Callback function for config changes
            group: Configuration group
        """
        cache_key = f"{group}:{data_id}"

        def wrapper(args: dict[str, Any]) -> None:
            content = args.get("content")
            with self._lock:
                self._cache[cache_key] = content
            logger.info(f"Config changed: {cache_key}")
            try:
                callback(args)
            except Exception:
                logger.exception(f"Error in config watcher: {cache_key}")

        try:
            self.client.add_config_watcher(data_id, group, wrapper)
        except Exception:
            logger.exception(f"Failed to add watcher: {cache_key}")

    def clear_cache(self, data_id: str | None = None, group: str = "DEFAULT_GROUP") -> None:
        """Clear configuration cache.

        Args:
            data_id: Specific config to clear (clears all if None)
            group: Configuration group
        """
        with self._lock:
            if data_id:
                self._cache.pop(f"{group}:{data_id}", None)
            else:
                self._cache.clear()


class LFXNacosService:
    """Lightweight Nacos service registration and discovery for LFX."""

    def __init__(
        self,
        server_addresses: str,
        service_name: str,
        ip: str,
        port: int,
        namespace: str = "public",
        username: str | None = None,
        password: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Nacos service manager.

        Args:
            server_addresses: Nacos server addresses
            service_name: Service name
            ip: Service IP
            port: Service port
            namespace: Nacos namespace
            username: Nacos username
            password: Nacos password
            metadata: Service metadata
        """
        if not NACOS_AVAILABLE:
            msg = "nacos-sdk-python is not installed. Install with: uv add nacos-sdk-python"
            raise ImportError(msg)

        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.metadata = metadata or {}
        self._registered = False

        try:
            self.client = nacos.NacosClient(
                server_addresses=server_addresses,
                namespace=namespace,
                username=username,
                password=password,
            )
            logger.info(
                f"LFX Nacos service client initialized for {service_name}")
        except Exception:
            logger.exception("Failed to initialize Nacos service client")
            raise

    def register(self) -> bool:
        """Register service instance.

        Returns:
            True if successful
        """
        if self._registered:
            return True

        try:
            self.client.add_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
                weight=1.0,
                metadata=self.metadata,
                enable=True,
                healthy=True,
                ephemeral=True,
            )
            self._registered = True
            logger.info(
                f"LFX service registered: {self.service_name} at {self.ip}:{self.port}")
            return True
        except Exception:
            logger.exception(
                f"Failed to register service: {self.service_name}")
            return False

    def deregister(self) -> bool:
        """Deregister service instance.

        Returns:
            True if successful
        """
        if not self._registered:
            return True

        try:
            self.client.remove_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
            )
            self._registered = False
            logger.info(f"LFX service deregistered: {self.service_name}")
            return True
        except Exception:
            logger.exception(
                f"Failed to deregister service: {self.service_name}")
            return False

    def discover(
        self,
        service_name: str | None = None,
        healthy_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Discover service instances.

        Args:
            service_name: Service name (uses self.service_name if None)
            healthy_only: Only return healthy instances

        Returns:
            List of service instances
        """
        service_name = service_name or self.service_name

        try:
            result = self.client.list_naming_instance(
                service_name=service_name,
                healthy_only=healthy_only,
            )
            return result.get("hosts", [])
        except Exception:
            logger.exception(f"Failed to discover instances: {service_name}")
            return []

    @contextmanager
    def lifecycle(self):
        """Context manager for service lifecycle.

        Usage:
            with service.lifecycle():
                # Service is registered
                pass
            # Service is deregistered
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


def create_nacos_config(
    server_addresses: str | None = None,
    namespace: str | None = None,
    username: str | None = None,
    password: str | None = None,
    enabled: bool | None = None,
) -> LFXNacosConfig | None:
    """Create Nacos configuration manager from environment or parameters.

    Priority: parameters > environment variables > defaults

    Args:
        server_addresses: Nacos server addresses (reads from NACOS_SERVER_ADDRESSES if None)
        namespace: Nacos namespace (reads from NACOS_NAMESPACE if None, default: "public")
        username: Nacos username (reads from NACOS_USERNAME if None)
        password: Nacos password (reads from NACOS_PASSWORD if None)
        enabled: Whether Nacos is enabled (reads from NACOS_ENABLED if None)

    Returns:
        LFXNacosConfig instance or None if:
        - Nacos SDK is not installed
        - Nacos is disabled (NACOS_ENABLED=false)
        - Server addresses are not configured
        - Failed to create instance

    Environment Variables:
        NACOS_ENABLED: Enable/disable Nacos (true/false)
        NACOS_SERVER_ADDRESSES: Nacos server addresses (required)
        NACOS_NAMESPACE: Nacos namespace (optional, default: public)
        NACOS_USERNAME: Nacos username (optional)
        NACOS_PASSWORD: Nacos password (optional)

    Example:
        # From environment variables
        config = create_nacos_config()

        # With explicit parameters
        config = create_nacos_config(
            server_addresses="localhost:8848",
            namespace="lfx-dev"
        )

        # Check if available
        if config:
            settings = config.get_json("app-settings")
        else:
            # Use defaults
            settings = {"default": "config"}
    """
    import os

    # Check if Nacos SDK is available
    if not NACOS_AVAILABLE:
        logger.debug("Nacos SDK not installed")
        return None

    # Check if enabled (parameter > env > default: True)
    if enabled is None:
        enabled_env = os.getenv("NACOS_ENABLED", "").lower()
        enabled = enabled_env != "false"  # Disabled only if explicitly set to false

    if not enabled:
        logger.info("Nacos is disabled")
        return None

    # Get configuration from parameters or environment
    server_addresses = server_addresses or os.getenv("NACOS_SERVER_ADDRESSES")

    # If no server addresses configured, return None
    if not server_addresses:
        logger.info(
            "Nacos server addresses not configured, skipping initialization")
        return None

    namespace = namespace or os.getenv("NACOS_NAMESPACE", "public")
    username = username or os.getenv("NACOS_USERNAME")
    password = password or os.getenv("NACOS_PASSWORD")

    try:
        logger.info(
            f"Creating LFX Nacos config: {server_addresses}, namespace: {namespace}")
        return LFXNacosConfig(
            server_addresses=server_addresses,
            namespace=namespace,
            username=username,
            password=password,
        )
    except Exception:
        logger.exception("Failed to create Nacos config")
        return None


def create_nacos_service(
    service_name: str | None = None,
    ip: str | None = None,
    port: int | None = None,
    server_addresses: str | None = None,
    namespace: str | None = None,
    username: str | None = None,
    password: str | None = None,
    metadata: dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> LFXNacosService | None:
    """Create Nacos service manager from environment or parameters.

    Priority: parameters > environment variables > defaults

    Args:
        service_name: Service name (reads from NACOS_SERVICE_NAME if None, default: "lfx-service")
        ip: Service IP (reads from NACOS_SERVICE_IP if None, default: "127.0.0.1")
        port: Service port (reads from NACOS_SERVICE_PORT if None, default: 8000)
        server_addresses: Nacos server addresses (reads from NACOS_SERVER_ADDRESSES if None)
        namespace: Nacos namespace (reads from NACOS_NAMESPACE if None, default: "public")
        username: Nacos username (reads from NACOS_USERNAME if None)
        password: Nacos password (reads from NACOS_PASSWORD if None)
        metadata: Service metadata (reads from NACOS_SERVICE_METADATA if None)
        enabled: Whether Nacos is enabled (reads from NACOS_ENABLED if None)

    Returns:
        LFXNacosService instance or None if:
        - Nacos SDK is not installed
        - Nacos is disabled (NACOS_ENABLED=false)
        - Server addresses are not configured
        - Failed to create instance

    Environment Variables:
        NACOS_ENABLED: Enable/disable Nacos (true/false)
        NACOS_SERVER_ADDRESSES: Nacos server addresses (required)
        NACOS_NAMESPACE: Nacos namespace (optional, default: public)
        NACOS_USERNAME: Nacos username (optional)
        NACOS_PASSWORD: Nacos password (optional)
        NACOS_SERVICE_NAME: Service name (optional, default: lfx-service)
        NACOS_SERVICE_IP: Service IP (optional, default: 127.0.0.1)
        NACOS_SERVICE_PORT: Service port (optional, default: 8000)
        NACOS_SERVICE_METADATA: Service metadata as JSON string (optional)

    Example:
        # From environment variables
        service = create_nacos_service()

        # With explicit parameters
        service = create_nacos_service(
            service_name="lfx-executor",
            ip="192.168.1.100",
            port=8000
        )

        # Use with context manager
        if service:
            with service:
                # Service is registered
                pass
            # Service is automatically deregistered
    """
    import json
    import os

    # Check if Nacos SDK is available
    if not NACOS_AVAILABLE:
        logger.debug("Nacos SDK not installed")
        return None

    # Check if enabled (parameter > env > default: True)
    if enabled is None:
        enabled_env = os.getenv("NACOS_ENABLED", "").lower()
        enabled = enabled_env != "false"  # Disabled only if explicitly set to false

    if not enabled:
        logger.info("Nacos is disabled")
        return None

    # Get configuration from parameters or environment
    server_addresses = server_addresses or os.getenv("NACOS_SERVER_ADDRESSES")

    # If no server addresses configured, return None
    if not server_addresses:
        logger.info(
            "Nacos server addresses not configured, skipping service registration")
        return None

    namespace = namespace or os.getenv("NACOS_NAMESPACE", "public")
    username = username or os.getenv("NACOS_USERNAME")
    password = password or os.getenv("NACOS_PASSWORD")

    # Service configuration
    service_name = service_name or os.getenv(
        "NACOS_SERVICE_NAME", "lfx-service")
    ip = ip or os.getenv("NACOS_SERVICE_IP", "127.0.0.1")

    # Handle port
    if port is None:
        port_env = os.getenv("NACOS_SERVICE_PORT")
        port = int(port_env) if port_env else 8000

    # Handle metadata (from JSON string if in environment)
    if metadata is None:
        metadata_env = os.getenv("NACOS_SERVICE_METADATA")
        if metadata_env:
            try:
                metadata = json.loads(metadata_env)
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse NACOS_SERVICE_METADATA as JSON, using empty dict")
                metadata = {}
        else:
            metadata = {}

    try:
        logger.info(
            f"Creating LFX Nacos service: {service_name} at {ip}:{port}")
        return LFXNacosService(
            server_addresses=server_addresses,
            service_name=service_name,
            ip=ip,
            port=port,
            namespace=namespace,
            username=username,
            password=password,
            metadata=metadata,
        )
    except Exception:
        logger.exception("Failed to create Nacos service")
        return None
