from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLQualityModelComponent(Component):
    display_name = i18n.t("components.quality.quality_model.display_name")
    description = i18n.t("components.quality.quality_model.description")
    icon = "shield-check"
    name = "ETLQualityModel"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.quality.quality_model.data_input.display_name"),
            info=i18n.t("components.quality.quality_model.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="quality_model_config",
            display_name=i18n.t("components.quality.quality_model.quality_model_config.display_name"),
            info=i18n.t("components.quality.quality_model.quality_model_config.info"),
            table_schema=[
                {
                    "name": "model_id",
                    "display_name": i18n.t("components.quality.quality_model.quality_model_config.model_id"),
                    "type": "int",
                    "description": i18n.t("components.quality.quality_model.quality_model_config.model_id_desc"),
                },
                {
                    "name": "model_name",
                    "display_name": i18n.t("components.quality.quality_model.quality_model_config.model_name"),
                    "type": "str",
                    "description": i18n.t("components.quality.quality_model.quality_model_config.model_name_desc"),
                },
                {
                    "name": "enabled",
                    "display_name": i18n.t("components.quality.quality_model.quality_model_config.enabled"),
                    "type": "bool",
                    "description": i18n.t("components.quality.quality_model.quality_model_config.enabled_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "load_models",
                        "label": i18n.t("components.quality.quality_model.quality_model_config.load_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="auto_evaluate",
            display_name=i18n.t("components.quality.quality_model.auto_evaluate.display_name"),
            info=i18n.t("components.quality.quality_model.auto_evaluate.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.quality.quality_model.outputs.data.display_name"),
            method="process_data",
        ),
        Output(
            name="quality_result",
            display_name=i18n.t("components.quality.quality_model.outputs.quality_result.display_name"),
            method="evaluate_quality",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates based on action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused in this implementation)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[QualityModel] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button clicks (from quality_model_config table)
        if field_name == "quality_model_config" and action == "load_models":
            logger.info("[QualityModel] Load models triggered by action button")

            try:
                # Import here to avoid circular dependencies
                from lfx.services.deps import get_feign_service
                from lfx.services.feign.clients.quality_model import QualityModelFeignClient

                # Get feign service
                feign_service = get_feign_service()
                client = QualityModelFeignClient(feign_service)

                # Update status
                self.status = i18n.t("components.quality.quality_model.status.loading_models")

                # Call API to get quality model list
                models = await client.get_quality_model_list()

                if not models:
                    logger.warning("[QualityModel] No quality models returned from API")
                    self.status = i18n.t("components.quality.quality_model.status.no_models_found")
                    return build_config

                # Transform API response to table format
                model_configs = self._transform_models_to_config(models)

                if model_configs:
                    # Update build_config with quality model configurations
                    build_config["quality_model_config"]["value"] = model_configs
                    logger.info(f"[QualityModel] Loaded {len(model_configs)} quality models")
                    self.status = i18n.t(
                        "components.quality.quality_model.status.models_loaded", count=len(model_configs)
                    )
                else:
                    logger.warning("[QualityModel] No quality models extracted from API response")
                    self.status = i18n.t("components.quality.quality_model.status.no_models_found")

            except ValueError as e:
                # Handle expected errors (API errors, etc.)
                error_msg = str(e)
                logger.warning(f"[QualityModel] Failed to load quality models: {error_msg}")
                self.status = i18n.t("components.quality.quality_model.errors.load_failed", error=error_msg)
            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[QualityModel] Load models failed with unexpected error")
                self.status = i18n.t("components.quality.quality_model.errors.graph_not_available")

        logger.debug(f"[QualityModel] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _transform_models_to_config(self, models: list[dict]) -> list[dict]:
        """Transform API response to table configuration format.

        Args:
            models: List of quality model dictionaries from API

        Returns:
            List of model configuration dictionaries for TableInput

        Example:
            API Response: [{"id": 1, "name": "Model A", "status": 1}, ...]
            Transformed: [{"model_id": 1, "model_name": "Model A", "enabled": False}, ...]
        """
        try:
            if not models:
                return []

            model_configs = []
            for model in models:
                # Extract fields from API response
                # Adjust field names based on actual API response structure
                model_id = model.get("id")
                model_name = model.get("name", "")

                if model_id is None:
                    logger.warning(f"[QualityModel] Model missing 'id' field: {model}")
                    continue

                model_config = {
                    "model_id": model_id,
                    "model_name": model_name,
                    "enabled": False,  # Default to disabled
                }
                model_configs.append(model_config)

            logger.debug(f"[QualityModel] Transformed {len(model_configs)} model configurations")
            return model_configs

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[QualityModel] Failed to transform model configurations")
            return []

    def process_data(self) -> list[Data]:
        """Process data through quality model (current version: pass-through).

        Returns:
            List of Data objects (currently unchanged from input)

        Raises:
            ValueError: Missing required inputs
        """
        try:
            if not self.data_input:
                raise ValueError(i18n.t("components.quality.quality_model.errors.no_data_input"))

            # Update status
            self.status = i18n.t("components.quality.quality_model.status.processing_data", count=len(self.data_input))

            # Current implementation: pass-through
            # Future: Apply quality model evaluation logic here
            result = self.data_input

            # Success status
            self.status = i18n.t("components.quality.quality_model.status.data_processed", count=len(result))

            return result

        except Exception as e:
            error_msg = i18n.t("components.quality.quality_model.errors.missing_config")
            self.status = error_msg
            logger.exception(f"[QualityModel] Process data failed: {e}")
            raise ValueError(error_msg) from e

    async def evaluate_quality(self) -> Data:
        """Evaluate data quality using quality models (RESERVED FOR FUTURE).

        This method is reserved for future implementation.
        It will call the quality model API to perform actual quality evaluation.

        Returns:
            Data object containing quality evaluation results

        Future Implementation:
            1. Extract enabled quality models from quality_model_config
            2. Call quality model API for each enabled model
            3. Aggregate quality results
            4. Return quality report as Data object
        """
        try:
            if not self.data_input or not self.quality_model_config:
                raise ValueError(i18n.t("components.quality.quality_model.errors.missing_config"))

            # Extract enabled models
            enabled_models = [m for m in self.quality_model_config if m.get("enabled", False)]

            if not enabled_models:
                logger.warning("[QualityModel] No quality models enabled")
                return Data(
                    data={
                        "status": "no_models_enabled",
                        "message": "No quality models are enabled for evaluation",
                        "total_records": len(self.data_input),
                    }
                )

            # TODO: Future implementation - call quality evaluation API
            # For now, return placeholder result
            logger.info("[QualityModel] Quality evaluation requested (reserved for future implementation)")

            result = Data(
                data={
                    "status": "reserved",
                    "message": "Quality evaluation feature is reserved for future implementation",
                    "total_records": len(self.data_input),
                    "enabled_models": [m.get("model_name") for m in enabled_models],
                }
            )

            self.status = i18n.t(
                "components.quality.quality_model.status.evaluation_complete", count=len(self.data_input)
            )

            return result

        except Exception as e:
            error_msg = i18n.t("components.quality.quality_model.errors.api_call_failed", error=str(e))
            self.status = error_msg
            logger.exception(f"[QualityModel] Evaluate quality failed: {e}")
            raise ValueError(error_msg) from e
