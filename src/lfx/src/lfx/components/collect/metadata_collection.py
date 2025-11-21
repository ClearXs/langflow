"""Metadata collection component."""

from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema import Data


class ETLMetadataCollectionComponent(Component):
    """Execute metadata collection task."""

    display_name = i18n.t("components.collect.metadata_collection.display_name")
    description = i18n.t("components.collect.metadata_collection.description")
    icon = "package"
    name = "ETLMetadataCollection"
    include_universal_input = True

    inputs = [
        DropdownInput(
            name="metadata_task_id",
            display_name=i18n.t("components.collect.metadata_collection.metadata_task_id.display_name"),
            info=i18n.t("components.collect.metadata_collection.metadata_task_id.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
    ]

    outputs = [
        Output(
            name="execution_result",
            display_name=i18n.t("components.collect.metadata_collection.outputs.execution_result.display_name"),
            method="execute_metadata_collection",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates for metadata task dropdown.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused in this implementation)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[MetadataCollection] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle refresh button click on metadata_task_id dropdown
        if field_name == "metadata_task_id":
            logger.info("[MetadataCollection] Load tasks triggered by refresh button")

            try:
                # Import here to avoid circular dependencies
                from lfx.services.deps import get_feign_service
                from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

                # Get feign service
                feign_service = get_feign_service()
                client = DataConstructionFeignClient(feign_service)

                # Update status
                self.status = i18n.t("components.collect.metadata_collection.status.loading_tasks")

                # Call API to get metadata task list
                tasks = await client.get_metadata_task_list()

                if not tasks:
                    logger.warning("[MetadataCollection] No metadata tasks returned from API")
                    self.status = i18n.t("components.collect.metadata_collection.errors.no_tasks_found")
                    return build_config

                # Transform to dropdown options
                dropdown_options, options_metadata = self._transform_tasks_to_dropdown_options(tasks)

                if dropdown_options:
                    # Update build_config with metadata task options
                    # Note: options contains task IDs (actual values)
                    # options_metadata contains full metadata with value/label structure for frontend
                    build_config["metadata_task_id"]["options"] = dropdown_options
                    build_config["metadata_task_id"]["options_metadata"] = options_metadata

                    # Store metadata in component instance for later use during execution
                    self._options_metadata = options_metadata

                    logger.info(f"[MetadataCollection] Loaded {len(dropdown_options)} metadata tasks")
                    logger.debug(f"[MetadataCollection] Set options: {dropdown_options}")
                    logger.debug(f"[MetadataCollection] Set options_metadata with {len(options_metadata)} entries")
                    self.status = i18n.t(
                        "components.collect.metadata_collection.status.tasks_loaded", count=len(dropdown_options)
                    )
                else:
                    logger.warning("[MetadataCollection] No metadata tasks found")
                    self.status = i18n.t("components.collect.metadata_collection.errors.no_tasks_found")
                    build_config["metadata_task_id"]["options"] = []
                    build_config["metadata_task_id"]["options_metadata"] = []

            except ValueError as e:
                # Handle expected errors (API errors, etc.)
                error_msg = str(e)
                logger.warning(f"[MetadataCollection] Failed to load metadata tasks: {error_msg}")
                self.status = i18n.t("components.collect.metadata_collection.errors.load_failed", error=error_msg)
            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[MetadataCollection] Load tasks failed with unexpected error")
                self.status = i18n.t("components.collect.metadata_collection.errors.graph_not_available")

        logger.debug(f"[MetadataCollection] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _transform_tasks_to_dropdown_options(self, tasks: list[dict]) -> tuple[list[str], list[dict]]:
        """Transform API tasks to dropdown options format.

        Args:
            tasks: List of metadata task dictionaries from API

        Returns:
            Tuple of (options, options_metadata) where:
                - options: List of task IDs (actual values for backend)
                - options_metadata: List of dicts with value/label structure for frontend display
        """
        try:
            if not tasks:
                return [], []

            dropdown_options = []
            options_metadata = []

            for task in tasks:
                task_id = task.get("id")
                task_name = task.get("taskName", "")

                if task_id is None:
                    logger.warning(f"[MetadataCollection] Task missing 'id' field: {task}")
                    continue

                # Display name for dropdown
                display_name = task_name or f"Task {task_id}"

                # Add task ID to options (actual value)
                dropdown_options.append(str(task_id))

                # Add to metadata with value/label structure (for frontend display)
                # IMPORTANT: Only include value, label, and fields in excludeKeys (icon, status, org_id, api_endpoint)
                # All other fields will be displayed in dropdown, so use _ prefix for internal data
                options_metadata.append(
                    {
                        "value": str(task_id),  # Required for matching, but should not be displayed
                        "label": display_name,  # ✅ Main display text in dropdown
                        # Use underscore prefix for all internal fields to prevent display
                        "_id": task_id,
                        "_name": task_name,
                        "_datasource_ids": task.get("datasourceIds", ""),
                        "_datasource_names": task.get("datasourceNames", []),
                        "_schedule_type": task.get("scheduleType", ""),
                        "_description": task.get("description", ""),
                        "_status": str(task.get("status", "")),  # Use _ prefix to hide from display
                    }
                )

            logger.debug(f"[MetadataCollection] Transformed {len(dropdown_options)} dropdown options")
            return dropdown_options, options_metadata

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[MetadataCollection] Failed to transform dropdown options")
            return [], []

    async def _get_task_id_from_display_name(self, task_id_or_name: str) -> int | None:
        """Get actual task ID from selected value.

        Args:
            task_id_or_name: The value selected by user (should be task ID)

        Returns:
            Task ID (int) or None if not found
        """
        # First, try to parse as numeric ID (should be the normal case now)
        try:
            task_id = int(task_id_or_name)
            logger.debug(f"[MetadataCollection] Parsed task ID: {task_id}")
            return task_id
        except (ValueError, TypeError):
            # If not a number, might be an old-style display name, try to look it up
            logger.warning(f"[MetadataCollection] Value '{task_id_or_name}' is not a numeric ID, trying name lookup")

        # Check if we have cached metadata from build_config
        if hasattr(self, "_options_metadata") and self._options_metadata:
            for metadata in self._options_metadata:
                # Try to match by value (ID) or label (display name)
                if metadata.get("value") == task_id_or_name or metadata.get("label") == task_id_or_name:
                    task_id = metadata.get("_id") or metadata.get("id")  # Support both new and old format
                    logger.debug(
                        f"[MetadataCollection] Found task ID {task_id} from cached metadata for '{task_id_or_name}'"
                    )
                    return int(task_id) if task_id else None

        # Fetch fresh task list from API and search
        logger.info(f"[MetadataCollection] Fetching task list from API to find ID for '{task_id_or_name}'")
        try:
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)
            tasks = await client.get_metadata_task_list()

            logger.debug(f"[MetadataCollection] Fetched {len(tasks)} tasks from API")

            # Search for exact match (by ID or name)
            for task in tasks:
                task_id_str = str(task.get("id", ""))
                task_name = task.get("taskName", "")

                if task_id_str == task_id_or_name or task_name == task_id_or_name:
                    task_id = task.get("id")
                    logger.info(f"[MetadataCollection] Found task ID {task_id} for '{task_id_or_name}'")
                    return int(task_id) if task_id else None

            # If no exact match, log all available tasks for debugging
            logger.warning(f"[MetadataCollection] No match found for '{task_id_or_name}'")
            logger.warning(
                f"[MetadataCollection] Available tasks: {[(t.get('id'), t.get('taskName')) for t in tasks[:5]]}"
            )

        except Exception as e:
            logger.error(f"[MetadataCollection] Failed to fetch tasks for ID lookup: {e}")

        logger.error(f"[MetadataCollection] Cannot find task ID for: {task_id_or_name}")
        return None

    async def execute_metadata_collection(self) -> Data:
        """Execute metadata collection task immediately.

        This method executes the selected metadata collection task via API.

        Returns:
            Data object containing execution result with keys:
                - success (bool): Whether execution succeeded
                - message (str): Result message from API
                - task_id (int): ID of executed task
                - task_name (str): Name of executed task

        Raises:
            ValueError: Missing task selection or execution failed
        """
        try:
            # Validate metadata task selection
            if not self.metadata_task_id:
                error_msg = i18n.t("components.collect.metadata_collection.errors.no_task_selected")
                self.status = error_msg
                raise ValueError(error_msg)

            logger.info(f"[MetadataCollection] execute_metadata_collection called with task='{self.metadata_task_id}'")

            # Get actual task ID from display name
            task_id = await self._get_task_id_from_display_name(self.metadata_task_id)

            if task_id is None:
                error_msg = i18n.t(
                    "components.collect.metadata_collection.errors.task_id_not_found", name=self.metadata_task_id
                )
                self.status = error_msg
                raise ValueError(error_msg)

            # Import Feign client
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            # Get feign service
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            # Update status - executing metadata collection
            self.status = i18n.t("components.collect.metadata_collection.status.executing_task", task_id=task_id)
            logger.info(f"[MetadataCollection] Executing metadata collection task ID: {task_id}")

            # Call execute_immediately API
            result = await client.execute_metadata_task_immediately(task_id)

            # Check execution result
            if not result.get("success", False):
                # Execution failed
                error_message = result.get("message", "Unknown error")
                error_msg = i18n.t(
                    "components.collect.metadata_collection.errors.execution_failed", error=error_message
                )
                self.status = error_msg
                logger.error(f"[MetadataCollection] Metadata collection failed: {error_message}")
                raise ValueError(error_msg)

            # Execution succeeded - update status and return result
            success_message = result.get("message", "Execution successful")
            self.status = i18n.t(
                "components.collect.metadata_collection.status.execution_success", message=success_message
            )
            logger.info(f"[MetadataCollection] Metadata collection succeeded: {success_message}")

            # Return execution result as Data object
            return Data(
                data={
                    "success": True,
                    "message": success_message,
                    "task_id": task_id,
                    "task_name": self.metadata_task_id,
                }
            )

        except ValueError:
            # Re-raise ValueError (expected errors with user-friendly messages)
            raise
        except Exception as e:
            # Handle unexpected errors
            error_msg = i18n.t("components.collect.metadata_collection.errors.api_call_failed", error=str(e))
            self.status = error_msg
            logger.exception(f"[MetadataCollection] Execute metadata collection failed with unexpected error: {e}")
            raise ValueError(error_msg) from e
