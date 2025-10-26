"""Quality model service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class QualityModelFeignClient:
    """Quality model service Feign client for data-governance microservice."""

    SERVICE_NAME = "data-governance"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def get_quality_model_list(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Get quality model list.

        Args:
            query: Optional query parameters (e.g., name filter, status filter)

        Returns:
            List of quality model dictionaries

        Raises:
            ValueError: API call failed

        Example:
            client = QualityModelFeignClient(feign_service)
            models = await client.get_quality_model_list()
            # Returns: [{"id": 1, "name": "Model A", "status": 1}, ...]
        """
        try:
            params = query or {}

            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/quality-model/getList",
                params=params,
            )

            result = response.json()

            # Handle Spring Boot R<T> response wrapper
            if isinstance(result, dict):
                if "code" in result:
                    if result.get("code") != 200:
                        error_msg = result.get("msg", "Unknown error")
                        msg = f"Quality model API returned error: {error_msg}"
                        raise ValueError(msg)
                    # Extract data from R<List<QualityModelVO>>
                    data = result.get("data", [])
                else:
                    # Direct data response
                    data = result
            elif isinstance(result, list):
                data = result
            else:
                msg = f"Unexpected response type: {type(result)}"
                raise ValueError(msg)

            logger.info(f"[QualityModelClient] Successfully retrieved {len(data)} quality models")
            return data

        except Exception as e:
            error_msg = f"Failed to get quality model list: {e}"
            logger.exception(f"[QualityModelClient] {error_msg}")
            raise ValueError(error_msg) from e

    async def get_quality_model_detail(self, model_id: int) -> dict[str, Any]:
        """Get quality model detail.

        Args:
            model_id: Quality model ID

        Returns:
            Quality model detail dictionary

        Raises:
            ValueError: API call failed
        """
        try:
            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/quality-model/detail",
                params={"id": model_id},
            )

            result = response.json()

            # Handle Spring Boot R<T> response wrapper
            if isinstance(result, dict) and "code" in result:
                if result.get("code") != 200:
                    error_msg = result.get("msg", "Unknown error")
                    msg = f"Quality model API returned error: {error_msg}"
                    raise ValueError(msg)
                data = result.get("data", {})
            else:
                data = result

            logger.info(f"[QualityModelClient] Successfully retrieved quality model detail: {model_id}")
            return data

        except Exception as e:
            error_msg = f"Failed to get quality model detail for ID {model_id}: {e}"
            logger.exception(f"[QualityModelClient] {error_msg}")
            raise ValueError(error_msg) from e


# ============= Convenience Functions =============


async def get_quality_model_list(query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Get quality model list (convenience function).

    Args:
        query: Optional query parameters

    Returns:
        List of quality model dictionaries

    Raises:
        ValueError: API call failed

    Example:
        models = await get_quality_model_list()
        for model in models:
            print(f"Model: {model['name']}, ID: {model['id']}")
    """
    from lfx.services.deps import get_feign_service

    feign_service = get_feign_service()
    client = QualityModelFeignClient(feign_service)
    return await client.get_quality_model_list(query)


async def get_quality_model_detail(model_id: int) -> dict[str, Any]:
    """Get quality model detail (convenience function).

    Args:
        model_id: Quality model ID

    Returns:
        Quality model detail dictionary

    Raises:
        ValueError: API call failed
    """
    from lfx.services.deps import get_feign_service

    feign_service = get_feign_service()
    client = QualityModelFeignClient(feign_service)
    return await client.get_quality_model_detail(model_id)
