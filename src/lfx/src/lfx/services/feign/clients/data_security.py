"""Data security service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class DataSecurityFeignClient:
    """Data security service Feign client."""

    SERVICE_NAME = "data-security"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def get_protection_rules(
        self,
        rule_type: str,  # "ENCRYPTION" or "MASKING"
    ) -> list[dict]:
        """Get protection rules list.

        Args:
            rule_type: Rule type ENCRYPTION or MASKING

        Returns:
            List of rules containing id, ruleName, ruleType and other fields
        """
        try:
            logger.info(f"[DataSecurityClient] Getting {rule_type} rules from service: {self.SERVICE_NAME}")

            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/protection-rule/getList",
                params={"ruleType": rule_type},
            )

            # Parse response data
            response_data = response.json()
            logger.debug(f"[DataSecurityClient] Raw response data: {response_data}")

            # Handle R<List<ProtectionRuleVO>> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    rules = response_data["data"]
                    # Only return enabled rules (status == 1)
                    enabled_rules = [r for r in rules if r.get("status") == 1]
                    logger.info(
                        f"[DataSecurityClient] Got {len(enabled_rules)} enabled {rule_type} rules "
                        f"from {len(rules)} total rules"
                    )
                    return enabled_rules
                # If no data field, return the whole response if it's a list
                if isinstance(response_data, list):
                    enabled_rules = [r for r in response_data if r.get("status") == 1]
                    logger.info(f"[DataSecurityClient] Got {len(enabled_rules)} enabled {rule_type} rules")
                    return enabled_rules
                logger.warning(f"[DataSecurityClient] Unexpected response format: {response_data}")
                return []
            if isinstance(response_data, list):
                enabled_rules = [r for r in response_data if r.get("status") == 1]
                logger.info(f"[DataSecurityClient] Got {len(enabled_rules)} enabled {rule_type} rules")
                return enabled_rules
            logger.warning(f"[DataSecurityClient] Unexpected response type: {type(response_data)}")
            return []

        except ValueError as e:
            # Special handling for Nacos service not found
            if "No healthy instances found" in str(e):
                logger.warning(
                    f"[DataSecurityClient] Service {self.SERVICE_NAME} not found in Nacos. "
                    "This might be normal if the service is not deployed."
                )
                return []
            error_msg = f"Failed to get {rule_type} rules: {e}"
            logger.exception(f"[DataSecurityClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to get {rule_type} rules: {e}"
            logger.exception(f"[DataSecurityClient] {error_msg}")
            raise ValueError(error_msg) from e

    async def test_rule_batch(self, rule_id: int, input_values: list[str]) -> list[str]:
        """Batch test rule execution.

        Args:
            rule_id: Rule ID
            input_values: List of input values

        Returns:
            List of processed values (maintaining order)
        """
        try:
            logger.info(f"[DataSecurityClient] Testing rule {rule_id} with {len(input_values)} values")

            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/protection-rule/testRuleBatch",
                params={"id": rule_id},
                json=input_values,
            )

            response_data = response.json()
            logger.debug(f"[DataSecurityClient] Batch test raw response: {response_data}")

            # Handle R<List<String>> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    outputs = response_data["data"]
                    if isinstance(outputs, list):
                        logger.info(
                            f"[DataSecurityClient] Successfully processed {len(outputs)} values with rule {rule_id}"
                        )
                        return outputs
                    logger.warning(
                        f"[DataSecurityClient] Expected list in response data, got {type(outputs)}: {outputs}"
                    )
                    return []
                # If no data field, check if the response itself is a list
                if isinstance(response_data, list):
                    logger.info(
                        f"[DataSecurityClient] Successfully processed {len(response_data)} values with rule {rule_id}"
                    )
                    return response_data
                logger.warning(f"[DataSecurityClient] Unexpected response format: {response_data}")
                return []
            if isinstance(response_data, list):
                logger.info(
                    f"[DataSecurityClient] Successfully processed {len(response_data)} values with rule {rule_id}"
                )
                return response_data
            logger.warning(f"[DataSecurityClient] Unexpected response type: {type(response_data)}")
            return []

        except ValueError as e:
            # Special handling for Nacos service not found
            if "No healthy instances found" in str(e):
                error_msg = f"Data security service not available for rule {rule_id} test"
                logger.error(f"[DataSecurityClient] {error_msg}")
                raise ValueError(error_msg) from e
            error_msg = f"Failed to test rule {rule_id}: {e}"
            logger.exception(f"[DataSecurityClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to test rule {rule_id}: {e}"
            logger.exception(f"[DataSecurityClient] {error_msg}")
            raise ValueError(error_msg) from e


# ============= Convenience Functions =============


def get_data_security_client(feign_service) -> DataSecurityFeignClient:
    """Get data security Feign client.

    Args:
        feign_service: Feign service instance

    Returns:
        DataSecurityFeignClient instance
    """
    return DataSecurityFeignClient(feign_service)
