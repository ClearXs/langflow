from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema import Data


class ETLQualityModelComponent(Component):
    display_name = i18n.t("components.quality.quality_model.display_name")
    description = i18n.t("components.quality.quality_model.description")
    icon = "shield-check"
    name = "ETLQualityModel"
    include_universal_input = True  # Enable universal input for Quality Model

    inputs = [
        DropdownInput(
            name="quality_model_id",
            display_name=i18n.t("components.quality.quality_model.quality_model_id.display_name"),
            info=i18n.t("components.quality.quality_model.quality_model_id.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
    ]

    outputs = [
        Output(
            name="execution_result",
            display_name=i18n.t("components.quality.quality_model.outputs.execution_result.display_name"),
            method="execute_quality_check",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates for quality model dropdown.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused in this implementation)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[QualityModel] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle refresh button click on quality_model_id dropdown
        if field_name == "quality_model_id":
            logger.info("[QualityModel] Load models triggered by refresh button")

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

                # Filter and transform manual execution mode models to dropdown options
                # manual_models = self._filter_manual_models(models)
                manual_models = models

                if manual_models:
                    # Transform to dropdown options (simple string array for display)
                    # and store metadata separately for ID lookup
                    dropdown_options, options_metadata = self._transform_models_to_dropdown_options(manual_models)

                    # Update build_config with quality model options
                    build_config["quality_model_id"]["options"] = dropdown_options
                    build_config["quality_model_id"]["options_metadata"] = options_metadata

                    # Store metadata in component instance for later use during execution
                    self._options_metadata = options_metadata

                    logger.info(f"[QualityModel] Loaded {len(dropdown_options)} manual execution quality models")
                    self.status = i18n.t(
                        "components.quality.quality_model.status.models_loaded", count=len(dropdown_options)
                    )
                else:
                    logger.warning("[QualityModel] No manual execution mode quality models found")
                    self.status = i18n.t("components.quality.quality_model.errors.no_manual_models")
                    build_config["quality_model_id"]["options"] = []
                    build_config["quality_model_id"]["options_metadata"] = []

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

    def _filter_manual_models(self, models: list[dict]) -> list[dict]:
        """Filter quality models to only include manual execution mode.

        Args:
            models: List of quality model dictionaries from API

        Returns:
            List of models with executeMode='manual'

        Example:
            Input: [
                {"id": 1, "name": "Model A", "executeMode": "manual"},
                {"id": 2, "name": "Model B", "executeMode": "periodic"},
                {"id": 3, "name": "Model C", "executeMode": "manual"}
            ]
            Output: [
                {"id": 1, "name": "Model A", "executeMode": "manual"},
                {"id": 3, "name": "Model C", "executeMode": "manual"}
            ]
        """
        try:
            if not models:
                return []

            manual_models = []
            for model in models:
                execute_mode = model.get("executeMode", "").lower()

                # Only include models with executeMode='manual'
                if execute_mode == "manual":
                    manual_models.append(model)
                else:
                    logger.debug(
                        f"[QualityModel] Skipping model '{model.get('name')}' "
                        f"with executeMode='{execute_mode}' (not 'manual')"
                    )

            logger.info(f"[QualityModel] Filtered {len(manual_models)} manual models out of {len(models)} total models")
            return manual_models

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[QualityModel] Failed to filter manual execution models")
            return []

    def _transform_models_to_dropdown_options(self, models: list[dict]) -> tuple[list[str], list[dict]]:
        """Transform API models to dropdown options format.

        Langflow DropdownInput uses simple string arrays for options,
        with optional metadata stored separately for ID lookups.

        Args:
            models: List of quality model dictionaries from API

        Returns:
            Tuple of (options, options_metadata) where:
                - options: List of display strings (model names)
                - options_metadata: List of dicts with full model info for ID lookup

        Example:
            Input: [{"id": 1, "name": "Model A"}, {"id": 2, "name": "Model B"}]
            Output: (
                ["Model A", "Model B"],
                [
                    {"id": 1, "name": "Model A", "display_name": "Model A"},
                    {"id": 2, "name": "Model B", "display_name": "Model B"}
                ]
            )
        """
        try:
            if not models:
                return [], []

            dropdown_options = []
            options_metadata = []

            for model in models:
                model_id = model.get("id")
                model_name = model.get("name", "")

                if model_id is None:
                    logger.warning(f"[QualityModel] Model missing 'id' field: {model}")
                    continue

                # Display name for dropdown
                display_name = model_name or f"Model {model_id}"

                # Add to simple string array (for frontend dropdown)
                dropdown_options.append(display_name)

                # Add to metadata (for ID lookup during execution)
                options_metadata.append(
                    {
                        "id": model_id,
                        "name": model_name,
                        "display_name": display_name,
                        "execute_mode": model.get("executeMode", "manual"),
                    }
                )

            logger.debug(f"[QualityModel] Transformed {len(dropdown_options)} dropdown options")
            return dropdown_options, options_metadata

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[QualityModel] Failed to transform dropdown options")
            return [], []

    async def _get_model_id_from_display_name(self, display_name: str) -> int | None:
        """Get actual model ID from selected display name.

        Args:
            display_name: The display name selected by user from dropdown

        Returns:
            Model ID (int) or None if not found

        Note:
            This method fetches the model list from API and searches for matching name.
            It's reliable but makes an API call during execution.
        """
        # First, try to parse as numeric ID (edge case where display name is already an ID)
        try:
            model_id = int(display_name)
            logger.debug(f"[QualityModel] Display name '{display_name}' parsed as numeric ID: {model_id}")
            return model_id
        except (ValueError, TypeError):
            pass

        # Check if we have cached metadata from build_config
        if hasattr(self, "_options_metadata") and self._options_metadata:
            for metadata in self._options_metadata:
                if metadata.get("display_name") == display_name:
                    model_id = metadata.get("id")
                    logger.debug(f"[QualityModel] Found model ID {model_id} from cached metadata for '{display_name}'")
                    return model_id

        # Fetch fresh model list from API and search
        logger.info(f"[QualityModel] Fetching model list from API to find ID for '{display_name}'")
        try:
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.quality_model import QualityModelFeignClient

            feign_service = get_feign_service()
            client = QualityModelFeignClient(feign_service)
            models = await client.get_quality_model_list()

            logger.debug(f"[QualityModel] Fetched {len(models)} models from API")

            # Search for exact name match
            for model in models:
                model_name = model.get("name", "")
                model_id = model.get("id")

                logger.debug(f"[QualityModel] Checking model: id={model_id}, name='{model_name}'")

                if model_name == display_name:
                    logger.info(f"[QualityModel] Found exact match: model ID {model_id} for '{display_name}'")
                    return model_id

            # If no exact match, log all available models for debugging
            logger.warning(f"[QualityModel] No exact match found for '{display_name}'")
            logger.warning(f"[QualityModel] Available models: {[(m.get('id'), m.get('name')) for m in models[:5]]}")

        except Exception as e:
            logger.error(f"[QualityModel] Failed to fetch models for ID lookup: {e}")

        logger.error(f"[QualityModel] Cannot find model ID for display name: {display_name}")
        return None

    async def execute_quality_check(self) -> Data:
        """Execute quality model check immediately.

        This method executes the selected quality model check via API.
        No data input is required - the quality model operates on its configured data source.

        Returns:
            Data object containing execution result with keys:
                - success (bool): Whether execution succeeded
                - message (str): Result message from API
                - model_id (int): ID of executed quality model
                - model_name (str): Name of executed quality model

        Raises:
            ValueError: Missing model selection or execution failed
        """
        try:
            # Validate quality model selection
            if not self.quality_model_id:
                error_msg = i18n.t("components.quality.quality_model.errors.no_model_selected")
                self.status = error_msg
                raise ValueError(error_msg)

            logger.info(f"[QualityModel] execute_quality_check called with quality_model_id='{self.quality_model_id}'")

            # Get actual model ID from display name
            # quality_model_id contains the display name selected from dropdown
            model_id = await self._get_model_id_from_display_name(self.quality_model_id)

            if model_id is None:
                error_msg = i18n.t(
                    "components.quality.quality_model.errors.model_id_not_found", name=self.quality_model_id
                )
                self.status = error_msg
                raise ValueError(error_msg)

            # Import Feign client
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.quality_model import QualityModelFeignClient

            # Get feign service
            feign_service = get_feign_service()
            client = QualityModelFeignClient(feign_service)

            # Update status - executing quality check
            self.status = i18n.t("components.quality.quality_model.status.executing_model", model_id=model_id)
            logger.info(f"[QualityModel] Executing quality model check for model ID: {model_id}")

            # Call execute_immediately API with numeric model ID
            result = await client.execute_immediately(model_id)

            # Check execution result
            if not result.get("success", False):
                # Quality check failed
                error_message = result.get("message", "Unknown error")
                error_msg = i18n.t("components.quality.quality_model.errors.execution_failed", error=error_message)
                self.status = error_msg
                logger.error(f"[QualityModel] Quality check failed: {error_message}")
                raise ValueError(error_msg)

            # Quality check succeeded - update status and return result
            success_message = result.get("message", "Execution successful")
            self.status = i18n.t("components.quality.quality_model.status.execution_success", message=success_message)
            logger.info(f"[QualityModel] Quality check passed: {success_message}")

            # Return execution result as Data object
            return Data(
                data={
                    "success": True,
                    "message": success_message,
                    "model_id": model_id,
                    "model_name": self.quality_model_id,
                }
            )

        except ValueError:
            # Re-raise ValueError (expected errors with user-friendly messages)
            raise
        except Exception as e:
            # Handle unexpected errors
            error_msg = i18n.t("components.quality.quality_model.errors.api_call_failed", error=str(e))
            self.status = error_msg
            logger.exception(f"[QualityModel] Execute quality check failed with unexpected error: {e}")
            raise ValueError(error_msg) from e
