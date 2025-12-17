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

    async def execute_immediately(self, model_id: int, external_params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute quality model check immediately.

        Calls the /quality-model/execute-immediately endpoint to trigger
        manual execution of a quality model.

        Args:
            model_id: Quality model ID to execute
            external_params: Optional external parameters (e.g., {"folderId": 123})

        Returns:
            Execution result dictionary with keys:
                - success (bool): True if execution succeeded
                - message (str): Result message from API
                - data (dict): Full quality check result data from QualityModelExecutionResultVO

        Raises:
            ValueError: API call failed or returned error

        Example:
            client = QualityModelFeignClient(feign_service)
            result = await client.execute_immediately(model_id=123, external_params={"folderId": 456})
            if result["success"]:
                print(f"Execution succeeded: {result['message']}")
                print(f"Quality check data: {result['data']}")
            else:
                print(f"Execution failed: {result['message']}")
        """
        try:
            logger.info(f"[QualityModelClient] Executing quality model immediately: {model_id}, external_params={external_params}")

            # Build DTO request body: {"modelId": xxx, "externalParams": {...}}
            request_body: dict[str, Any] = {"modelId": model_id}
            if external_params:
                request_body["externalParams"] = external_params

            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/quality-model/execute-immediately",
                json=request_body,  # Send complete DTO as request body
            )

            result = response.json()

            # Handle Spring Boot R<QualityModelExecutionResultVO> response wrapper
            if isinstance(result, dict) and "code" in result:
                code = result.get("code")
                success = result.get("success", False)
                message = result.get("msg", "Unknown response")
                data = result.get("data")  # Extract quality check result data

                # Check both code=200 AND success=true as per requirements
                if code == 200 and success:
                    logger.info(f"[QualityModelClient] Quality model {model_id} executed successfully: {message}")
                    # Return both metadata and full quality check data
                    return {"success": True, "message": message, "data": data}
                logger.warning(
                    f"[QualityModelClient] Quality model {model_id} execution failed - "
                    f"code: {code}, success: {success}, msg: {message}"
                )
                return {"success": False, "message": message, "data": data}
            # Unexpected response format
            msg = f"Unexpected response format from execute-immediately API: {result}"
            logger.error(f"[QualityModelClient] {msg}")
            raise ValueError(msg)

        except Exception as e:
            error_msg = f"Failed to execute quality model {model_id}: {e}"
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


async def execute_quality_model_immediately(model_id: int) -> dict[str, Any]:
    """Execute quality model immediately (convenience function).

    Args:
        model_id: Quality model ID to execute

    Returns:
        Execution result dictionary with keys:
            - success (bool): True if execution succeeded
            - message (str): Result message from API

    Raises:
        ValueError: API call failed

    Example:
        result = await execute_quality_model_immediately(model_id=123)
        if result["success"]:
            print("Quality check passed!")
        else:
            print(f"Quality check failed: {result['message']}")
    """
    from lfx.services.deps import get_feign_service

    feign_service = get_feign_service()
    client = QualityModelFeignClient(feign_service)
    return await client.execute_immediately(model_id)
