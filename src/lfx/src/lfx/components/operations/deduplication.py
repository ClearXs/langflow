"""ETL Deduplication Component - Remove or merge duplicate records based on grouping fields

数据去重合并组件：根据指定字段删除或合并重复数据
支持排序控制保留记录、预览功能和统计信息输出
"""

from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, Output, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLDeduplicationComponent(Component):
    """数据去重合并组件 - 根据分组字段删除或合并重复记录"""

    display_name = i18n.t("components.operations.deduplication.display_name")
    description = i18n.t("components.operations.deduplication.description")
    icon = "filter"
    name = "ETLDeduplication"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.operations.deduplication.data_input.display_name"),
            info=i18n.t("components.operations.deduplication.data_input.info"),
            is_list=True,
            required=True,
        ),
        # 比较字段配置 - 使用TableInput
        TableInput(
            name="group_by_fields",
            display_name=i18n.t("components.operations.deduplication.group_by_fields.display_name"),
            info=i18n.t("components.operations.deduplication.group_by_fields.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.operations.deduplication.group_by_fields.field_name"),
                    "type": "str",
                    "description": i18n.t("components.operations.deduplication.group_by_fields.field_name_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.operations.deduplication.group_by_fields.load_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        # 去重模式
        DropdownInput(
            name="dedup_mode",
            display_name=i18n.t("components.operations.deduplication.dedup_mode.display_name"),
            info=i18n.t("components.operations.deduplication.dedup_mode.info"),
            options=["delete", "merge"],
            options_metadata=[
                {"value": "delete", "label": i18n.t("components.operations.deduplication.dedup_mode.delete")},
                {"value": "merge", "label": i18n.t("components.operations.deduplication.dedup_mode.merge")},
            ],
            value="delete",
            required=True,
        ),
        # 排序字段（可选）
        DropdownInput(
            name="sort_field",
            display_name=i18n.t("components.operations.deduplication.sort_field.display_name"),
            info=i18n.t("components.operations.deduplication.sort_field.info"),
            options=[""],  # 动态加载
            refresh_button=True,
            real_time_refresh=True,
            required=False,
        ),
        # 排序方向
        DropdownInput(
            name="sort_order",
            display_name=i18n.t("components.operations.deduplication.sort_order.display_name"),
            info=i18n.t("components.operations.deduplication.sort_order.info"),
            options=["asc", "desc"],
            options_metadata=[
                {"value": "asc", "label": i18n.t("components.operations.deduplication.sort_order.asc")},
                {"value": "desc", "label": i18n.t("components.operations.deduplication.sort_order.desc")},
            ],
            value="asc",
            advanced=True,
        ),
        # 合并分隔符（仅merge模式使用）
        StrInput(
            name="merge_separator",
            display_name=i18n.t("components.operations.deduplication.merge_separator.display_name"),
            info=i18n.t("components.operations.deduplication.merge_separator.info"),
            value=",",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.operations.deduplication.outputs.data.display_name"),
            method="deduplicate",
        ),
        Output(
            name="preview",
            display_name=i18n.t("components.operations.deduplication.outputs.preview.display_name"),
            method="preview_data",
        ),
        Output(
            name="stats",
            display_name=i18n.t("components.operations.deduplication.outputs.stats.display_name"),
            method="get_dedup_stats",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates - load fields from upstream components.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[Deduplication] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle "Load Fields" button click (from group_by_fields table)
        if field_name == "group_by_fields" and action == "load_fields":
            logger.info("[Deduplication] Field loading triggered by action button")

            try:
                # Get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # Fallback to self.graph if not in build_config (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[Deduplication] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[Deduplication] No graph data available")
                    self.status = i18n.t("components.operations.deduplication.errors.no_upstream_data")
                    return build_config

                field_names = []

                # Primary strategy: Try to execute upstream node to get actual data
                try:
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                    )

                    if upstream_data:
                        # Extract field names from upstream data
                        field_names = self._extract_field_names(upstream_data)
                        logger.info(f"[Deduplication] Extracted {len(field_names)} fields from upstream data")
                    else:
                        logger.warning("[Deduplication] No data returned from upstream node")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configuration
                    logger.warning(f"[Deduplication] Upstream execution failed: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        field_names = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "Deduplication"
                        )

                        if field_names:
                            logger.info(f"[Deduplication] Extracted {len(field_names)} fields from static config")
                        else:
                            logger.warning("[Deduplication] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[Deduplication] Static analysis also failed")

                # Update build_config with results
                if field_names:
                    # Update group_by_fields table with field names
                    build_config["group_by_fields"]["value"] = [{"field_name": name} for name in field_names]

                    # Also update sort_field dropdown options
                    build_config["sort_field"]["options"] = [""] + field_names

                    logger.info(f"[Deduplication] Loaded {len(field_names)} fields from upstream")
                    self.status = i18n.t(
                        "components.operations.deduplication.status.fields_loaded", count=len(field_names)
                    )
                else:
                    self.status = i18n.t("components.operations.deduplication.warnings.field_load_failed")
                    logger.warning("[Deduplication] No fields could be extracted")

            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[Deduplication] Field loading failed with unexpected error")
                self.status = i18n.t("components.operations.deduplication.errors.no_upstream_data")

        # Handle sort_field refresh button
        if field_name == "sort_field" and not field_value:
            logger.info("[Deduplication] Sort field refresh triggered")

            try:
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # Fallback to self.graph if not in build_config
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data

                if graph_data:
                    field_names = []

                    # Primary strategy: Try to execute upstream node
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        if upstream_data:
                            field_names = self._extract_field_names(upstream_data)
                            logger.info(f"[Deduplication] Refreshed sort field with {len(field_names)} fields from upstream data")

                    except ValueError:
                        # Fallback strategy: Extract from static config
                        logger.warning("[Deduplication] Upstream execution failed for sort field. Trying static analysis...")

                        try:
                            from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                            field_names = find_and_extract_upstream_fields(
                                graph_data, node_id, "data_input", "Deduplication"
                            )
                            if field_names:
                                logger.info(f"[Deduplication] Refreshed sort field with {len(field_names)} fields from static config")

                        except Exception:  # noqa: BLE001
                            logger.exception("[Deduplication] Static analysis for sort field also failed")

                    # Update options
                    if field_names:
                        build_config["sort_field"]["options"] = [""] + field_names

            except Exception:  # noqa: BLE001
                # Broad exception needed to prevent refresh failures from breaking UI
                logger.exception("[Deduplication] Failed to refresh sort fields")

        logger.debug(f"[Deduplication] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """Extract field names from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field names extracted from the first record
        """
        try:
            if not data_list:
                return []

            # Get first record to extract field names
            first_record = data_list[0]
            if hasattr(first_record, "data") and isinstance(first_record.data, dict):
                return list(first_record.data.keys())
            if isinstance(first_record, dict):
                return list(first_record.keys())

            logger.warning(f"[Deduplication] Unexpected data type: {type(first_record)}")
            return []

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[Deduplication] Failed to extract field names")
            return []

    def deduplicate(self) -> list[Data]:
        """Remove or merge duplicate records based on grouping fields.

        Returns:
            List of deduplicated Data objects

        Raises:
            ValueError: If configuration is invalid or processing fails
        """
        try:
            self.status = i18n.t("components.operations.deduplication.status.deduplicating")

            # Validate inputs
            if not self.data_input:
                raise ValueError(i18n.t("components.operations.deduplication.errors.no_data"))

            if not self.group_by_fields:
                raise ValueError(i18n.t("components.operations.deduplication.errors.no_group_fields"))

            # Convert to DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            # Extract grouping field names
            group_columns = [field.get("field_name", "").strip() for field in self.group_by_fields]
            group_columns = [col for col in group_columns if col]  # Remove empty strings

            if not group_columns:
                raise ValueError(i18n.t("components.operations.deduplication.errors.empty_group_fields"))

            # Validate that all grouping fields exist in dataframe
            for col in group_columns:
                if col not in df.columns:
                    raise ValueError(i18n.t("components.operations.deduplication.errors.field_not_found", field=col))

            # Apply sorting if specified
            if self.sort_field and self.sort_field.strip() and self.sort_field in df.columns:
                ascending = self.sort_order == "asc"
                df = df.sort_values(by=self.sort_field, ascending=ascending)
                logger.debug(
                    f"[Deduplication] Sorted by {self.sort_field} ({'ascending' if ascending else 'descending'})"
                )

            # Execute deduplication based on mode
            if self.dedup_mode == "delete":
                # Delete mode: keep only first record per group
                result_df = df.drop_duplicates(subset=group_columns, keep="first")
                logger.info("[Deduplication] Delete mode: kept first record per group")
            else:
                # Merge mode: merge non-grouping fields with separator
                result_df = self._merge_duplicates(df, group_columns)
                logger.info("[Deduplication] Merge mode: merged non-grouping fields with separator")

            # Convert back to Data objects
            result_data = [Data(data=row.to_dict()) for _, row in result_df.iterrows()]

            # Success status with statistics
            removed_count = len(df) - len(result_df)
            self.status = i18n.t(
                "components.operations.deduplication.status.success", unique=len(result_df), duplicates=removed_count
            )

            logger.info(
                f"[Deduplication] Completed - Original: {len(df)}, Unique: {len(result_df)}, Removed: {removed_count}"
            )

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.deduplication.errors.dedup_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[Deduplication] Failed: {error_msg}")
            raise ValueError(error_msg) from e

    def _merge_duplicates(self, df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
        """Merge duplicate records by concatenating non-grouping fields with separator.

        Args:
            df: Input DataFrame
            group_columns: List of columns to group by

        Returns:
            DataFrame with merged duplicate records
        """
        # Get non-grouping columns
        non_group_columns = [col for col in df.columns if col not in group_columns]

        # Build aggregation dictionary
        agg_dict = {}

        # For grouping columns, take the first value
        for col in group_columns:
            agg_dict[col] = "first"

        # For non-grouping columns, join unique values with separator
        for col in non_group_columns:
            # Convert to string and join unique values
            agg_dict[col] = lambda x, sep=self.merge_separator: sep.join(x.astype(str).unique())

        # Group and aggregate
        result_df = df.groupby(group_columns, as_index=False).agg(agg_dict)

        logger.debug(
            f"[Deduplication] Merged {len(df)} records into {len(result_df)} records "
            f"using separator '{self.merge_separator}'"
        )

        return result_df

    def preview_data(self) -> list[Data]:
        """Preview first 100 rows of deduplicated data.

        Returns:
            List of first 100 deduplicated Data objects (or fewer if less than 100)

        Raises:
            ValueError: If deduplication fails
        """
        try:
            # Get full deduplicated result
            full_result = self.deduplicate()

            # Limit to first 100 rows
            preview_result = full_result[:100]

            self.status = i18n.t(
                "components.operations.deduplication.status.preview_ready",
                shown=len(preview_result),
                total=len(full_result),
            )

            logger.info(f"[Deduplication] Preview generated - showing {len(preview_result)} of {len(full_result)} rows")

            return preview_result

        except Exception as e:
            error_msg = i18n.t("components.operations.deduplication.errors.preview_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[Deduplication] Preview failed: {error_msg}")
            raise ValueError(error_msg) from e

    def get_dedup_stats(self) -> Data:
        """Get deduplication statistics.

        Returns:
            Data object containing statistics:
            - original_count: Number of input records
            - unique_count: Number of unique records after deduplication
            - duplicate_count: Number of removed/merged duplicates
            - deduplication_rate: Percentage of duplicates removed
            - group_by_fields: List of grouping field names
            - dedup_mode: Deduplication mode (delete/merge)
            - sort_field: Sort field used (if any)
            - sort_order: Sort order (asc/desc)
        """
        try:
            original_count = len(self.data_input) if self.data_input else 0
            deduplicated = self.deduplicate()
            unique_count = len(deduplicated)
            duplicate_count = original_count - unique_count

            stats = {
                "original_count": original_count,
                "unique_count": unique_count,
                "duplicate_count": duplicate_count,
                "deduplication_rate": round(duplicate_count / original_count * 100, 2) if original_count > 0 else 0,
                "group_by_fields": [
                    field.get("field_name", "") for field in self.group_by_fields if field.get("field_name")
                ]
                if self.group_by_fields
                else [],
                "dedup_mode": self.dedup_mode,
                "sort_field": self.sort_field if self.sort_field and self.sort_field.strip() else "None",
                "sort_order": self.sort_order,
            }

            logger.info(f"[Deduplication] Statistics generated: {stats}")

            return Data(data=stats)

        except Exception:  # noqa: BLE001
            # Broad exception needed to prevent stats failures from breaking flow
            logger.exception("[Deduplication] Failed to get statistics")
            return Data(data={"error": "Failed to generate statistics"})
