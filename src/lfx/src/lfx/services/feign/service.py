"""Feign service for microservice communication via Nacos."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from lfx.log.logger import logger
from lfx.services.base import Service

if TYPE_CHECKING:
    from langflow.services.nacos.service import NacosService


class FeignService(Service):
    """Feign service for HTTP communication with service discovery."""

    name = "feign_service"

    def __init__(self, nacos_service: NacosService):
        """Initialize Feign service.

        Args:
            nacos_service: Nacos service for service discovery
        """
        super().__init__()
        self.nacos_service = nacos_service
        self._instance_counters: dict[str, int] = {}  # Round-robin counters

    def _get_service_instance(self, service_name: str, group_name: str = "DEFAULT_GROUP") -> dict[str, Any]:
        """Get service instance via Nacos with round-robin load balancing.

        Args:
            service_name: Nacos service name
            group_name: Service group name

        Returns:
            Service instance info: {"ip": "...", "port": ..., ...}

        Raises:
            ValueError: No available service instances
        """
        # Service discovery
        instances = self.nacos_service.discover_instances(
            service_name=service_name,
            healthy_only=True,
            group_name=group_name,
        )

        if not instances:
            error_msg = f"No healthy instances found for service: {service_name}"
            logger.error(f"[FeignService] {error_msg}")
            raise ValueError(error_msg)

        # Round-robin load balancing
        if service_name not in self._instance_counters:
            self._instance_counters[service_name] = 0

        instance = instances[self._instance_counters[service_name] % len(instances)]
        self._instance_counters[service_name] += 1

        logger.debug(f"[FeignService] Selected instance for {service_name}: {instance['ip']}:{instance['port']}")
        return instance

    def _get_base_url(self, service_name: str, group_name: str = "DEFAULT_GROUP") -> str:
        """Get service base URL.

        Args:
            service_name: Service name
            group_name: Service group name

        Returns:
            Base URL (e.g., http://192.168.1.100:8080)
        """
        instance = self._get_service_instance(service_name, group_name)
        return f"http://{instance['ip']}:{instance['port']}"

    async def get(
        self,
        service_name: str,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        group_name: str = "DEFAULT_GROUP",
        timeout: float = 120.0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send GET request.

        Args:
            service_name: Target service name
            path: API path (e.g., /resource-file/download/123)
            params: Query parameters
            headers: HTTP headers (no auth needed for internal calls)
            group_name: Service group name
            timeout: Timeout in seconds
            **kwargs: Additional httpx parameters

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPError: HTTP error
            ValueError: Service discovery failed
        """
        base_url = self._get_base_url(service_name, group_name)
        url = f"{base_url}/{path.lstrip('/')}"

        logger.info(f"[FeignService] GET {url}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                url,
                params=params,
                headers=headers or {},
                **kwargs,
            )
            response.raise_for_status()
            return response

    async def post(
        self,
        service_name: str,
        path: str,
        data: Any = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        group_name: str = "DEFAULT_GROUP",
        timeout: float = 120.0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send POST request.

        Args:
            service_name: Target service name
            path: API path
            data: Form data
            json: JSON data
            headers: HTTP headers
            group_name: Service group name
            timeout: Timeout in seconds
            **kwargs: Additional httpx parameters

        Returns:
            HTTP response object
        """
        base_url = self._get_base_url(service_name, group_name)
        url = f"{base_url}/{path.lstrip('/')}"

        logger.info(f"[FeignService] POST {url}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                data=data,
                json=json,
                headers=headers or {},
                **kwargs,
            )
            response.raise_for_status()
            return response

    async def post_multipart(
        self,
        service_name: str,
        path: str,
        files: dict[str, Any],
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        group_name: str = "DEFAULT_GROUP",
        timeout: float = 300.0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send POST request with multipart/form-data.

        Args:
            service_name: Target service name
            path: API path
            files: Files dict for multipart upload (e.g., {"file": (filename, content, mime_type)})
            params: Query parameters
            headers: HTTP headers
            group_name: Service group name
            timeout: Timeout in seconds (default 5 minutes for file upload)
            **kwargs: Additional httpx parameters

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPStatusError: HTTP error occurred
            ValueError: Service discovery failed

        Example:
            files = {"file": ("report.csv", file_bytes, "text/csv")}
            response = await feign.post_multipart(
                service_name="data-construction",
                path="/resource-file/put-file",
                params={"folderId": 123},
                files=files
            )
        """
        base_url = self._get_base_url(service_name, group_name)
        url = f"{base_url}/{path.lstrip('/')}"

        logger.info(f"[FeignService] POST multipart to {url}, params={params}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, files=files, params=params, headers=headers or {}, **kwargs)
            response.raise_for_status()
            return response

    async def teardown(self) -> None:
        """Cleanup resources."""
        logger.debug("[FeignService] Teardown")
