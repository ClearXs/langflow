"""Data governance service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class DataGovernanceFeignClient:
    """Data governance service Feign client."""

    SERVICE_NAME = "data-governance"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def create_gdb_datasource(
        self,
        datasource_id: int,
        database_name: str,
        resource_id: str,
    ) -> dict[str, Any]:
        """Create GDB datasource in data-governance system.

        Args:
            datasource_id: PostgreSQL datasource ID
            database_name: Target database name
            resource_id: GDB resource file ID

        Returns:
            Dictionary containing:
                - datasource_id (str): Created datasource ID
                - created_at (str): Creation timestamp
                - ... (other fields from API response)

        Raises:
            ValueError: Failed to create GDB datasource
        """
        try:
            logger.info(
                f"[DataGovernanceClient] Creating GDB datasource - "
                f"datasource_id={datasource_id}, database={database_name}, resource_id={resource_id}"
            )

            # Build request payload
            payload = {
                "datasourceId": datasource_id,
                "databaseName": database_name,
                "resourceId": resource_id,
            }

            logger.debug(f"[DataGovernanceClient] Request payload: {payload}")

            # Call data-governance API
            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/modeling-logical-table/auto-import-gdb",
                json=payload,
                timeout=300.0,  # 5 minutes timeout for GDB processing
            )

            response_data = response.json()
            logger.debug(f"[DataGovernanceClient] Raw response: {response_data}")

            # Handle R<T> response wrapper structure
            if isinstance(response_data, dict):
                # Check for error response
                success = response_data.get("success", True)
                code = response_data.get("code")
                msg = response_data.get("msg", "Unknown response")

                if not success:
                    error_msg = f"Create GDB datasource failed (code={code}): {msg}"
                    logger.error(f"[DataGovernanceClient] {error_msg}")
                    raise ValueError(error_msg)

                # Extract data field
                if "data" in response_data:
                    datasource_info = response_data["data"]
                    logger.info(
                        f"[DataGovernanceClient] Created GDB datasource successfully: "
                        f"datasource_id={datasource_info.get('datasource_id')}, "
                        f"name={datasource_info.get('name')}"
                    )
                    return datasource_info

                # If no data field but success=true, return the whole response
                logger.info(
                    f"[DataGovernanceClient] Created GDB datasource (no data field): {msg}"
                )
                return response_data

            # Unexpected response format
            msg = f"Unexpected response format: {response_data}"
            raise ValueError(msg)

        except ValueError:
            # Re-raise ValueError from error response
            raise
        except Exception as e:
            # Handle other exceptions
            error_msg = f"Failed to create GDB datasource: {e}"
            logger.exception(f"[DataGovernanceClient] {error_msg}")
            raise ValueError(error_msg) from e
