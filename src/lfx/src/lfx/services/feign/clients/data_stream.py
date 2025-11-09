"""Data stream service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class DataStreamFeignClient:
    """Data stream service Feign client."""

    SERVICE_NAME = "data-stream"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def get_flink_cluster_list(self) -> list[dict]:
        """Get Flink cluster list from registry.

        Returns:
            List of Flink cluster dictionaries

        Raises:
            ValueError: Failed to get cluster list
        """
        try:
            logger.info(f"[DataStreamClient] Attempting to get Flink cluster list from service: {self.SERVICE_NAME}")

            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/registry-cluster/getList",
            )

            # Parse response data
            response_data = response.json()
            logger.debug(f"[DataStreamClient] Raw response data: {response_data}")

            # Handle R<List<RegistryClusterVO>> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    cluster_list = response_data["data"]
                    logger.info(f"[DataStreamClient] Got {len(cluster_list)} Flink clusters from feign API")
                    return cluster_list if isinstance(cluster_list, list) else []
                # If no data field, return the whole response if it's a list
                if isinstance(response_data, list):
                    logger.info(f"[DataStreamClient] Got {len(response_data)} Flink clusters from feign API")
                    return response_data
                logger.warning(f"[DataStreamClient] Unexpected response format: {response_data}")
                return []
            if isinstance(response_data, list):
                logger.info(f"[DataStreamClient] Got {len(response_data)} Flink clusters from feign API")
                return response_data
            logger.warning(f"[DataStreamClient] Unexpected response type: {type(response_data)}")
            return []

        except ValueError as e:
            # Handle Nacos service not found
            if "No healthy instances found" in str(e):
                logger.warning(
                    f"[DataStreamClient] Service {self.SERVICE_NAME} not found in Nacos. "
                    "This might be normal if the service is not deployed."
                )
                return []
            error_msg = f"Failed to get Flink cluster list: {e}"
            logger.exception(f"[DataStreamClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to get Flink cluster list: {e}"
            logger.exception(f"[DataStreamClient] {error_msg}")
            raise ValueError(error_msg) from e
