from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    TableInput,
)
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFeignOutputComponent(Component):
    display_name = i18n.t("components.input_output.feign_output.display_name")
    description = i18n.t("components.input_output.feign_output.description")
    icon = "send"
    name = "ETLFeignOutput"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.feign_output.data_input.display_name"),
            info=i18n.t("components.input_output.feign_output.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="service_name",
            display_name=i18n.t("components.input_output.feign_output.service_name.display_name"),
            info=i18n.t("components.input_output.feign_output.service_name.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        MessageTextInput(
            name="api_path",
            display_name=i18n.t("components.input_output.feign_output.api_path.display_name"),
            info=i18n.t("components.input_output.feign_output.api_path.info"),
            required=True,
            placeholder="/resource-file/upload/",
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t("components.input_output.feign_output.method.display_name"),
            info=i18n.t("components.input_output.feign_output.method.info"),
            options=["POST", "PUT", "PATCH"],
            value="POST",
        ),
        MessageTextInput(
            name="group_name",
            display_name=i18n.t("components.input_output.feign_output.group_name.display_name"),
            info=i18n.t("components.input_output.feign_output.group_name.info"),
            value="DEFAULT_GROUP",
            advanced=True,
        ),
        TableInput(
            name="headers",
            display_name=i18n.t("components.input_output.feign_output.headers.display_name"),
            info=i18n.t("components.input_output.feign_output.headers.info"),
            table_schema=[
                {"name": "key", "display_name": "Header Name", "type": "str"},
                {"name": "value", "display_name": "Header Value", "type": "str"},
            ],
            value=[],
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.feign_output.batch_size.display_name"),
            info=i18n.t("components.input_output.feign_output.batch_size.info"),
            value=100,
            advanced=True,
        ),
        BoolInput(
            name="send_as_batch",
            display_name=i18n.t("components.input_output.feign_output.send_as_batch.display_name"),
            info=i18n.t("components.input_output.feign_output.send_as_batch.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.input_output.feign_output.timeout.display_name"),
            info=i18n.t("components.input_output.feign_output.timeout.info"),
            value=120,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.input_output.feign_output.outputs.result.display_name"),
            method="send_to_service",
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
        logger.info(f"[FeignOutput] update_build_config called - field_name: {field_name}, action: {action}")

        if field_name == "service_name":
            logger.info("[FeignOutput] Load services triggered by refresh button")

            try:
                from langflow.services.deps import get_nacos_service

                nacos_service = get_nacos_service()

                if not nacos_service or not nacos_service.enabled:
                    logger.warning("[FeignOutput] Nacos service is not available or not enabled")
                    self.status = i18n.t("components.input_output.feign_output.errors.nacos_not_enabled")
                    return build_config

                self.status = i18n.t("components.input_output.feign_output.status.loading_services")

                service_names = await self._discover_available_services(nacos_service)

                if not service_names:
                    logger.warning("[FeignOutput] No services found")
                    self.status = i18n.t("components.input_output.feign_output.status.no_services_found")
                    return build_config

                build_config["service_name"]["options"] = sorted(service_names)

                logger.info(f"[FeignOutput] Loaded {len(service_names)} services")
                self.status = i18n.t(
                    "components.input_output.feign_output.status.services_loaded", count=len(service_names)
                )

            except Exception:  # noqa: BLE001
                logger.exception("[FeignOutput] Failed to load services")
                self.status = i18n.t("components.input_output.feign_output.errors.load_failed")

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
                logger.info(f"[FeignOutput] Found {len(all_services)} services from Nacos list_services API")

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
                    logger.info(f"[FeignOutput] Filtered to {len(available_services)} services with healthy instances")
                    return available_services
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[FeignOutput] Could not list services from Nacos: {e}")

        # Tier 2: Fallback to probing common service names (for compatibility)
        logger.info("[FeignOutput] Probing common service names as fallback")
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
                    logger.debug(f"[FeignOutput] Found service: {service_name} with {len(instances)} instances")
            except Exception:  # noqa: BLE001
                continue

        return available_services

    async def send_to_service(self) -> Data:
        """Send data to microservice using FeignService."""
        try:
            self.status = i18n.t("components.input_output.feign_output.status.sending")

            if not self.data_input:
                error_msg = i18n.t("components.input_output.feign_output.errors.no_data")
                raise ValueError(error_msg)

            if not self.service_name:
                error_msg = i18n.t("components.input_output.feign_output.errors.no_service_name")
                raise ValueError(error_msg)

            if not self.api_path:
                error_msg = i18n.t("components.input_output.feign_output.errors.no_api_path")
                raise ValueError(error_msg)

            from lfx.services.deps import get_feign_service

            feign_service = get_feign_service()

            if feign_service is None:
                error_msg = i18n.t("components.input_output.feign_output.errors.feign_service_unavailable")
                raise ValueError(error_msg)

            # Prepare headers
            headers = {h["key"]: h["value"] for h in self.headers} if self.headers else {}
            headers.setdefault("Content-Type", "application/json")

            # Extract data from Data objects
            data_list = [d.data if hasattr(d, "data") else d for d in self.data_input]

            success_count = 0
            error_count = 0

            # Send data
            if self.send_as_batch:
                # Batch mode: send in batches
                for i in range(0, len(data_list), self.batch_size):
                    batch = data_list[i : i + self.batch_size]
                    try:
                        # TODO: Support PUT/PATCH when FeignService adds these methods
                        response = await feign_service.post(
                            service_name=self.service_name,
                            path=self.api_path,
                            json=batch,
                            headers=headers,
                            group_name=self.group_name or "DEFAULT_GROUP",
                            timeout=float(self.timeout),
                        )
                        if response.status_code in [200, 201, 204]:
                            success_count += len(batch)
                        else:
                            error_count += len(batch)
                            logger.warning(f"[FeignOutput] Batch request failed with status {response.status_code}")
                    except Exception as e:  # noqa: BLE001
                        error_count += len(batch)
                        logger.exception(f"[FeignOutput] Batch request exception: {e}")
            else:
                # Individual mode: send one by one
                for item in data_list:
                    try:
                        # TODO: Support PUT/PATCH when FeignService adds these methods
                        response = await feign_service.post(
                            service_name=self.service_name,
                            path=self.api_path,
                            json=item,
                            headers=headers,
                            group_name=self.group_name or "DEFAULT_GROUP",
                            timeout=float(self.timeout),
                        )
                        if response.status_code in [200, 201, 204]:
                            success_count += 1
                        else:
                            error_count += 1
                            logger.warning(
                                f"[FeignOutput] Individual request failed with status {response.status_code}"
                            )
                    except Exception as e:  # noqa: BLE001
                        error_count += 1
                        logger.exception(f"[FeignOutput] Individual request exception: {e}")

            # Return result statistics
            result_info = {
                "service_name": self.service_name,
                "api_path": self.api_path,
                "success_count": success_count,
                "error_count": error_count,
                "method": self.method,
            }

            self.status = i18n.t(
                "components.input_output.feign_output.status.success", success=success_count, errors=error_count
            )

            return Data(data=result_info)

        except Exception as e:
            error_msg = i18n.t("components.input_output.feign_output.errors.send_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
