from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, FileInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLQualityModelComponent(Component):
    display_name = i18n.t("components.quality.quality_model.display_name")
    description = i18n.t("components.quality.quality_model.description")
    icon = "shield-check"
    name = "ETLQualityModel"
    include_universal_input = True  # Enable universal input for Quality Model

    # Version identifier to track code updates
    _component_version = "2.0_path_extraction"  # Updated to extract resource ID from paths

    inputs = [
        # File/Folder Selection Input (UI Browser)
        FileInput(
            name="folder_id_file",
            display_name=i18n.t("components.quality.quality_model.folder_id_file.display_name"),
            info=i18n.t("components.quality.quality_model.folder_id_file.info"),
            file_types=["folder"],  # Folder-only mode
            temp_file=False,  # Use FileTableInputComponent
            required=False,  # Optional since external_variable can replace it
            real_time_refresh=True,  # ✅ 添加实时刷新，确保 update_build_config 被调用
        ),
        # External Variable Input (Text Field)
        StrInput(
            name="folder_id_variable",
            display_name=i18n.t("components.quality.quality_model.folder_id_variable.display_name"),
            info=i18n.t("components.quality.quality_model.folder_id_variable.info"),
            placeholder="{folderIdVariable}",
            required=False,  # Optional since file selection can replace it
            resolve_variables=True,  # Enable automatic variable resolution
            real_time_refresh=True,  # ✅ 添加实时刷新
        ),
        DropdownInput(
            name="quality_model_id",
            display_name=i18n.t("components.quality.quality_model.quality_model_id.display_name"),
            info=i18n.t("components.quality.quality_model.quality_model_id.info"),
            options=[],
            required=True,
            refresh_button=True,
            real_time_refresh=True,  # ✅ 添加实时刷新
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

        # ============ 字段透传逻辑（始终执行）============
        # 注意：这需要在每次 update_build_config 被调用时都执行
        # 以确保 _output_fields 被正确设置到 build_config 中
        try:
            graph_data = build_config.get("_graph_data", {})
            node_id = build_config.get("_node_id")

            if graph_data and node_id:
                # 1. 尝试获取上游字段
                upstream_fields = await self._get_upstream_fields_with_retry(graph_data, node_id)

                # 2. 定义质量模型组件的输出字段（固定结构）
                quality_model_output_fields = [
                    {"name": "success", "type": "boolean"},
                    {"name": "message", "type": "string"},
                    {"name": "model_id", "type": "integer"},
                    {"name": "model_name", "type": "string"},
                    {"name": "folder_id", "type": "string"},
                    {"name": "quality_check_result", "type": "string"},  # JSON 字符串
                ]

                # 3. 合并上游字段和质量检查字段
                output_fields = upstream_fields + quality_model_output_fields

                # 4. 存储输出字段供下游使用（使用 DataOperations 的直接赋值模式）
                # 直接赋值列表，不使用包装结构（与 DataOperations 保持一致）
                build_config["_output_fields"] = output_fields

                logger.info(
                    f"[QualityModel] Set {len(output_fields)} output fields "
                    f"({len(upstream_fields)} from upstream + {len(quality_model_output_fields)} quality fields)"
                )
            else:
                # 没有 graph_data 或 node_id，使用回退方案
                fallback_fields = [
                    {"name": "success", "type": "boolean"},
                    {"name": "message", "type": "string"},
                    {"name": "model_id", "type": "integer"},
                    {"name": "model_name", "type": "string"},
                    {"name": "folder_id", "type": "string"},
                    {"name": "quality_check_result", "type": "string"},
                ]
                # 直接赋值（与 DataOperations 保持一致）
                build_config["_output_fields"] = fallback_fields
                logger.info("[QualityModel] Using fallback output fields (quality check fields only)")

        except Exception as e:
            logger.warning(f"[QualityModel] Failed to extract upstream fields: {e}")

            # 回退：如果无法获取上游字段，至少提供质量检查字段
            fallback_fields = [
                {"name": "success", "type": "boolean"},
                {"name": "message", "type": "string"},
                {"name": "model_id", "type": "integer"},
                {"name": "model_name", "type": "string"},
                {"name": "folder_id", "type": "string"},
                {"name": "quality_check_result", "type": "string"},
            ]
            # 直接赋值（与 DataOperations 保持一致）
            build_config["_output_fields"] = fallback_fields
            logger.info("[QualityModel] Using fallback output fields due to exception")

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

    async def _get_upstream_fields_with_retry(self, graph_data: dict, node_id: str) -> list[dict]:
        """获取上游字段，带重试机制处理 'has not been built yet' 错误

        Returns:
            List of field dicts with structure: [{"name": "field1", "type": "string"}, ...]
        """
        import asyncio

        max_retries = 2

        for attempt in range(max_retries):
            try:
                # 尝试执行上游节点获取实际数据
                upstream_data = await self.get_upstream_data(
                    input_name="upstream_data", graph_data=graph_data, sample_size=10, vertex_id=node_id
                )

                if upstream_data:
                    # 从实际数据中提取字段
                    if isinstance(upstream_data, list) and len(upstream_data) > 0:
                        first_item = upstream_data[0]
                        if hasattr(first_item, "data") and isinstance(first_item.data, dict):
                            from lfx.components.helpers.field_extraction import _infer_type_from_value

                            fields = [
                                {"name": key, "type": _infer_type_from_value(value)}
                                for key, value in first_item.data.items()
                            ]
                            logger.info(
                                f"[QualityModel] Extracted {len(fields)} fields from upstream data (attempt {attempt + 1})"
                            )
                            return fields

                logger.warning(f"[QualityModel] No data returned from upstream node (attempt {attempt + 1})")

            except ValueError as e:
                error_msg = str(e)
                if "has not been built yet" in error_msg and attempt < max_retries - 1:
                    logger.warning(
                        f"[QualityModel] Upstream node not built, retrying... (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(0.2)
                    continue
                logger.warning(f"[QualityModel] Upstream execution failed: {e}. Trying static analysis...")
                break
            except Exception as e:
                logger.warning(f"[QualityModel] Unexpected error: {e}. Falling back to static analysis...")
                break

        # 回退：静态字段提取
        try:
            from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

            fields = find_and_extract_upstream_fields(graph_data, node_id, "upstream_data", "ETLQualityModel")
            if fields:
                logger.info(f"[QualityModel] Extracted {len(fields)} fields from static config")
                return fields
        except Exception as e:
            logger.exception(f"[QualityModel] Static analysis failed: {e}")

        return []

    def _get_folder_id(self) -> str:
        """Extract folder_id from either file selection or external variable.

        Priority:
        1. folder_id_variable (if provided and not empty)
        2. folder_id_file from _parameters (if provided)
        3. folder_id_file from self attribute (fallback)
        4. Raise error if neither provided

        Returns:
            str: Folder ID (resource ID from file browser or resolved variable)

        Raises:
            ValueError: If neither input is provided

        Note:
            Uses the same extraction logic as CSV Input component.
            Checks _parameters first (where frontend stores values),
            then falls back to self attributes.
        """
        # Priority 1: File Variable - auto-resolved by Component._validate_inputs() with resolve_variables=True
        if hasattr(self, "folder_id_variable") and self.folder_id_variable:
            variable_value = self.folder_id_variable.strip()
            if variable_value:
                # Use base class helper method for variable resolution with fallback
                return self._resolve_variable_with_fallback(
                    variable_value,
                    "components.quality.quality_model.errors.variable_not_resolved"
                )

        # Priority 2: File selection from UI
        # Try to get folder_id from multiple sources (same logic as CSV Input)
        folder_id = None

        # Check if _parameters has the original folder_id_file structure
        folder_id_param = self._parameters.get("folder_id_file")
        if isinstance(folder_id_param, dict):
            # Extract from dict structure: {"file_path": "...", "value": "..."}
            folder_id = folder_id_param.get("file_path") or folder_id_param.get("value")
            logger.info(f"[QualityModel] Extracted folder_id from dict _parameters: {folder_id}")
        elif isinstance(folder_id_param, str):
            # It's a string - could be numeric ID or path
            if folder_id_param.isdigit():
                # Pure numeric ID
                folder_id = folder_id_param
                logger.info(f"[QualityModel] Using numeric string from _parameters as folder_id: {folder_id}")
            else:
                # It's a path - extract basename
                import os

                basename = os.path.basename(folder_id_param)
                if basename.isdigit():
                    # Basename is numeric (cached path like /path/to/1937069843168202754)
                    folder_id = basename
                    logger.info(f"[QualityModel] Extracted folder_id from cached path basename: {folder_id}")
                else:
                    # Basename is not numeric (real folder path)
                    # For quality model, we still try to use it as-is
                    folder_id = basename
                    logger.info(f"[QualityModel] Using basename from _parameters: {folder_id}")

        # Fallback to self.folder_id_file
        if not folder_id and hasattr(self, "folder_id_file") and self.folder_id_file:
            raw_value = self.folder_id_file
            if isinstance(raw_value, list) and len(raw_value) > 0:
                raw_value = raw_value[0]
            elif isinstance(raw_value, str):
                raw_value = raw_value
            else:
                raw_value = None

            if raw_value:
                # Apply same extraction logic
                if isinstance(raw_value, str):
                    if raw_value.isdigit():
                        folder_id = raw_value
                        logger.info(f"[QualityModel] Using numeric string from self.folder_id_file: {folder_id}")
                    else:
                        import os

                        basename = os.path.basename(raw_value)
                        folder_id = basename
                        logger.info(
                            f"[QualityModel] Extracted folder_id from self.folder_id_file: {folder_id} (from: {raw_value})"
                        )

        if folder_id:
            logger.info(f"[QualityModel] Final folder_id: {folder_id}")
            return folder_id

        # Neither provided - raise error
        error_msg = i18n.t("components.quality.quality_model.errors.no_folder_source")
        self.status = error_msg
        logger.error("[QualityModel] No folder source provided")
        raise ValueError(error_msg)

    async def execute_quality_check(self) -> Data:
        """Execute quality model check immediately.

        This method executes the selected quality model check via API with folder_id.

        Returns:
            Data object containing execution result with keys:
                - success (bool): Whether execution succeeded
                - message (str): Result message from API
                - model_id (int): ID of executed quality model
                - model_name (str): Name of executed quality model
                - folder_id (str): Folder ID used for execution
                - quality_check_result (dict, optional): Full quality check result data from
                  QualityModelExecutionResultVO, containing detailed check results, rule
                  execution status, data quality metrics, and validation results

        Raises:
            ValueError: Missing model selection, folder source, or execution failed
        """
        logger.info(f"[QualityModel] Component version: {getattr(self, '_component_version', 'unknown')}")
        logger.info(f"[QualityModel] _parameters keys: {list(self._parameters.keys())}")

        try:
            # Get folder_id from either external variable or file selection
            folder_id = self._get_folder_id()

            # Validate quality model selection
            if not self.quality_model_id:
                error_msg = i18n.t("components.quality.quality_model.errors.no_model_selected")
                self.status = error_msg
                raise ValueError(error_msg)

            logger.info(
                f"[QualityModel] execute_quality_check called with quality_model_id='{self.quality_model_id}', folder_id='{folder_id}'"
            )

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
            self.status = i18n.t(
                "components.quality.quality_model.status.executing_model", model_id=model_id, folder_id=folder_id
            )
            logger.info(f"[QualityModel] Executing quality model check for model ID: {model_id} on folder: {folder_id}")

            # Prepare external parameters with folderId
            # Note: folder_id should already be a numeric string extracted from path
            logger.info(f"[QualityModel] folder_id type: {type(folder_id)}, value: '{folder_id}'")

            try:
                folder_id_int = int(folder_id)
            except ValueError as e:
                error_msg = f"Failed to convert folder_id '{folder_id}' to integer: {e}. This suggests the path extraction failed."
                logger.error(f"[QualityModel] {error_msg}")
                raise ValueError(error_msg) from e

            external_params = {"folderId": folder_id_int}
            logger.info(f"[QualityModel] External parameters: {external_params}")

            # Call execute_immediately API with model ID and external parameters
            result = await client.execute_immediately(model_id, external_params=external_params)

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
            quality_check_data = result.get("data")  # Get full quality check result data from API

            self.status = i18n.t("components.quality.quality_model.status.execution_success", message=success_message)
            logger.info(f"[QualityModel] Quality check passed: {success_message}")

            # Return execution result as Data object with full API response data
            # Include both metadata and the complete quality check results for downstream components
            return_data = {
                "success": True,
                "message": success_message,
                "model_id": model_id,
                "model_name": self.quality_model_id,
                "folder_id": folder_id,
            }

            # Include full quality check result data if available
            if quality_check_data is not None:
                return_data["quality_check_result"] = quality_check_data
                logger.info("[QualityModel] Returning quality check result data to downstream components")
            else:
                logger.warning("[QualityModel] No quality check result data returned from API")

            return Data(data=return_data)

        except ValueError:
            # Re-raise ValueError (expected errors with user-friendly messages)
            raise
        except Exception as e:
            # Handle unexpected errors
            error_msg = i18n.t("components.quality.quality_model.errors.api_call_failed", error=str(e))
            self.status = error_msg
            logger.exception(f"[QualityModel] Execute quality check failed with unexpected error: {e}")
            raise ValueError(error_msg) from e
