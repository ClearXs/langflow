"""Data task service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class DataTaskFeignClient:
    """Data task service Feign client."""

    SERVICE_NAME = "data-task"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def trigger_process_alarm(
        self,
        langflow_flow_id: str,
        trigger_condition: str,
        error_message: str,
        extra_data: dict | None = None,
    ) -> bool:
        """Trigger process alarm notification.

        Args:
            langflow_flow_id: Langflow flow ID
            trigger_condition: Alarm condition ("PROCESS_BUILD_FAILURE" or "PROCESS_EXECUTION_FAILURE")
            error_message: Error message description
            extra_data: Additional metadata (optional)

        Returns:
            True if alarm sent successfully, False otherwise

        Note:
            This method never raises exceptions - all errors are logged only.
        """
        try:
            from datetime import datetime, timezone

            # Prepare request body
            # Note: triggerTime should be in milliseconds timestamp for Java Date type
            request_body = {
                "langflowFlowId": langflow_flow_id,
                "triggerCondition": trigger_condition,
                "errorMessage": error_message,
                "triggerTime": int(datetime.now(timezone.utc).timestamp() * 1000),
            }

            if extra_data:
                request_body["extraData"] = extra_data

            logger.info(
                f"[DataTaskClient] Triggering alarm for flow {langflow_flow_id}, condition: {trigger_condition}"
            )
            logger.debug(f"[DataTaskClient] Request body: {request_body}")

            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/alarm-trigger/process-event",
                json=request_body,
            )

            response_data = response.json()

            # Handle R<Boolean> response structure
            if isinstance(response_data, dict):
                success = response_data.get("success", False)
                if success:
                    logger.info(f"[DataTaskClient] Alarm notification sent successfully for flow {langflow_flow_id}")
                    return True
                logger.warning(
                    f"[DataTaskClient] Alarm notification failed: {response_data.get('msg', 'Unknown error')}"
                )
            else:
                logger.warning(f"[DataTaskClient] Unexpected alarm response format: {response_data}")

            return False  # noqa: TRY300

        except Exception as e:  # noqa: BLE001
            # Never raise exceptions - just log the error
            logger.exception(f"[DataTaskClient] Failed to send alarm notification for flow {langflow_flow_id}: {e}")
            return False
