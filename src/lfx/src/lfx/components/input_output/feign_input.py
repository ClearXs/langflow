import json
from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    DropdownInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
    Output,
    TableInput,
)
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFeignInputComponent(Component):
    display_name = i18n.t("components.input_output.feign_input.display_name")
    description = i18n.t("components.input_output.feign_input.description")
    icon = "network"
    name = "ETLFeignInput"
    include_universal_input = True

    inputs = [
        DropdownInput(
            name="service_name",
            display_name=i18n.t("components.input_output.feign_input.service_name.display_name"),
            info=i18n.t("components.input_output.feign_input.service_name.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        MessageTextInput(
            name="api_path",
            display_name=i18n.t("components.input_output.feign_input.api_path.display_name"),
            info=i18n.t("components.input_output.feign_input.api_path.info"),
            required=True,
            placeholder="/resource-file/download/",
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t("components.input_output.feign_input.method.display_name"),
            info=i18n.t("components.input_output.feign_input.method.info"),
            options=["GET", "POST"],
            value="GET",
        ),
        MessageTextInput(
            name="group_name",
            display_name=i18n.t("components.input_output.feign_input.group_name.display_name"),
            info=i18n.t("components.input_output.feign_input.group_name.info"),
            value="DEFAULT_GROUP",
            advanced=True,
        ),
        TableInput(
            name="headers",
            display_name=i18n.t("components.input_output.feign_input.headers.display_name"),
            info=i18n.t("components.input_output.feign_input.headers.info"),
            table_schema=[
                {"name": "key", "display_name": "Header Name", "type": "str"},
                {"name": "value", "display_name": "Header Value", "type": "str"},
            ],
            value=[],
            advanced=True,
        ),
        MultilineInput(
            name="request_body",
            display_name=i18n.t("components.input_output.feign_input.request_body.display_name"),
            info=i18n.t("components.input_output.feign_input.request_body.info"),
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.input_output.feign_input.timeout.display_name"),
            info=i18n.t("components.input_output.feign_input.timeout.info"),
            value=120,
            advanced=True,
        ),
        IntInput(
            name="retry_count",
            display_name=i18n.t("components.input_output.feign_input.retry_count.display_name"),
            info=i18n.t("components.input_output.feign_input.retry_count.info"),
            value=3,
            advanced=True,
        ),
        MessageTextInput(
            name="data_path",
            display_name=i18n.t("components.input_output.feign_input.data_path.display_name"),
            info=i18n.t("components.input_output.feign_input.data_path.info"),
            placeholder="$.data or data.items",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.feign_input.outputs.data.display_name"),
            method="fetch_data",
        ),
        Output(
            name="response_info",
            display_name=i18n.t("components.input_output.feign_input.outputs.response_info.display_name"),
            method="get_response_info",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,  # noqa: ARG002
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates for service name dropdown.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[FeignInput] update_build_config called - field_name: {field_name}, action: {action}")

        if field_name == "service_name":
            logger.info("[FeignInput] Load services triggered by refresh button")

            try:
                from langflow.services.deps import get_nacos_service

                nacos_service = get_nacos_service()

                if not nacos_service or not nacos_service.enabled:
                    logger.warning("[FeignInput] Nacos service is not available or not enabled")
                    self.status = i18n.t("components.input_output.feign_input.errors.nacos_not_enabled")
                    return build_config

                self.status = i18n.t("components.input_output.feign_input.status.loading_services")

                service_names = await self._discover_available_services(nacos_service)

                if not service_names:
                    logger.warning("[FeignInput] No services found")
                    self.status = i18n.t("components.input_output.feign_input.status.no_services_found")
                    return build_config

                build_config["service_name"]["options"] = sorted(service_names)

                logger.info(f"[FeignInput] Loaded {len(service_names)} services")
                self.status = i18n.t(
                    "components.input_output.feign_input.status.services_loaded", count=len(service_names)
                )

            except Exception:  # noqa: BLE001
                logger.exception("[FeignInput] Failed to load services")
                self.status = i18n.t("components.input_output.feign_input.errors.load_failed")

        return build_config

    async def _discover_available_services(self, nacos_service) -> list[str]:
        """Discover available services from Nacos.

        Two-tier strategy:
        1. Try to get all services from Nacos via list_services API
        2. Fallback to probing common service names

        Args:
            nacos_service: NacosService instance

        Returns:
            List of available service names
        """
        # Tier 1: Use Nacos list_services API to get all registered services
        try:
            all_services = nacos_service.list_services(
                group_name=self.group_name or "DEFAULT_GROUP",
                page_no=1,
                page_size=500,  # Get up to 500 services
            )

            if all_services:
                logger.info(f"[FeignInput] Found {len(all_services)} services from Nacos list_services API")

                # Filter out only healthy services (services with at least one healthy instance)
                available_services = []
                for service_name in all_services:
                    try:
                        instances = nacos_service.discover_instances(
                            service_name=service_name,
                            healthy_only=True,
                            group_name=self.group_name or "DEFAULT_GROUP",
                        )
                        if instances:
                            available_services.append(service_name)
                    except Exception:  # noqa: BLE001
                        continue

                if available_services:
                    logger.info(f"[FeignInput] Filtered to {len(available_services)} services with healthy instances")
                    return available_services
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[FeignInput] Could not list services from Nacos: {e}")

        # Tier 2: Fallback to probing common service names (for compatibility)
        logger.info("[FeignInput] Probing common service names as fallback")
        common_services = [
            "data-construction",
            "data-security",
            "data-stream",
            "data-task",
            "data-governance",
            "langflow",
        ]

        available_services = []
        for service_name in common_services:
            try:
                instances = nacos_service.discover_instances(
                    service_name=service_name,
                    healthy_only=True,
                    group_name=self.group_name or "DEFAULT_GROUP",
                )
                if instances:
                    available_services.append(service_name)
                    logger.debug(f"[FeignInput] Found service: {service_name} with {len(instances)} instances")
            except Exception:  # noqa: BLE001
                continue

        return available_services

    async def fetch_data(self) -> list[Data]:
        """Fetch data from microservice using FeignService."""
        try:
            self.status = i18n.t("components.input_output.feign_input.status.fetching")

            if not self.service_name:
                error_msg = i18n.t("components.input_output.feign_input.errors.no_service_name")
                raise ValueError(error_msg)

            if not self.api_path:
                error_msg = i18n.t("components.input_output.feign_input.errors.no_api_path")
                raise ValueError(error_msg)

            from lfx.services.deps import get_feign_service

            feign_service = get_feign_service()

            if feign_service is None:
                error_msg = i18n.t("components.input_output.feign_input.errors.feign_service_unavailable")
                raise ValueError(error_msg)

            headers = self._build_headers()

            # Retry loop
            response = None
            for attempt in range(self.retry_count):
                try:
                    if self.method == "GET":
                        response = await feign_service.get(
                            service_name=self.service_name,
                            path=self.api_path,
                            headers=headers,
                            group_name=self.group_name or "DEFAULT_GROUP",
                            timeout=float(self.timeout),
                        )
                    else:  # POST
                        body = json.loads(self.request_body) if self.request_body else None
                        response = await feign_service.post(
                            service_name=self.service_name,
                            path=self.api_path,
                            json=body,
                            headers=headers,
                            group_name=self.group_name or "DEFAULT_GROUP",
                            timeout=float(self.timeout),
                        )
                    break

                except Exception as e:
                    if attempt == self.retry_count - 1:
                        raise
                    logger.warning(f"[FeignInput] Retry {attempt + 1}/{self.retry_count} failed: {e}")

            if response is None:
                error_msg = i18n.t("components.input_output.feign_input.errors.fetch_failed", error="No response")
                raise ValueError(error_msg)

            # Parse response
            response_data = response.json()

            # Extract data using path if provided
            if self.data_path:
                response_data = self._extract_data_path(response_data)

            # Convert to Data objects
            result_data = []
            if isinstance(response_data, list):
                result_data = [Data(data=item) for item in response_data]
            elif isinstance(response_data, dict):
                result_data = [Data(data=response_data)]

        except Exception as e:
            error_msg = i18n.t("components.input_output.feign_input.errors.fetch_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
        else:
            self.status = i18n.t("components.input_output.feign_input.status.success", records=len(result_data))
            return result_data

    def _build_headers(self) -> dict:
        """Build request headers from TableInput."""
        headers = {}

        if self.headers:
            for header in self.headers:
                headers[header["key"]] = header["value"]

        return headers

    def _extract_data_path(self, data: Any) -> Any:
        """Extract data using simple JSONPath-like notation."""
        if not self.data_path:
            return data

        path_parts = self.data_path.strip("$.").split(".")
        current = data

        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part, current)
            else:
                break

        return current

    async def get_response_info(self) -> Data:
        """Get response information."""
        info = {
            "service_name": self.service_name,
            "api_path": self.api_path,
            "method": self.method,
            "group_name": self.group_name,
            "timeout": self.timeout,
        }
        return Data(data=info)
