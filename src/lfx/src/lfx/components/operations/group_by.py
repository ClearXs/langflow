import asyncio
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLGroupByComponent(Component):
    display_name = i18n.t("components.operations.group_by.display_name")
    description = i18n.t("components.operations.group_by.description")
    icon = "layers"
    name = "ETLGroupBy"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.operations.group_by.data_input.display_name"),
            info=i18n.t("components.operations.group_by.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="group_by_columns",
            display_name=i18n.t("components.operations.group_by.group_by_columns.display_name"),
            info=i18n.t("components.operations.group_by.group_by_columns.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.operations.group_by.group_by_columns.field_name"),
                    "type": "str",
                    "formatter": "dropdown",
                    "options": [],  # 动态填充
                    "required": True,
                    "description": i18n.t("components.operations.group_by.group_by_columns.field_name_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.operations.group_by.group_by_columns.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        TableInput(
            name="aggregations",
            display_name=i18n.t("components.operations.group_by.aggregations.display_name"),
            info=i18n.t("components.operations.group_by.aggregations.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.operations.group_by.aggregations.field_name"),
                    "type": "str",
                    "formatter": "dropdown",
                    "options": [],  # 动态填充
                    "required": True,
                    "description": i18n.t("components.operations.group_by.aggregations.field_name_desc"),
                },
                {
                    "name": "agg_function",
                    "display_name": i18n.t("components.operations.group_by.aggregations.agg_function"),
                    "type": "str",
                    "formatter": "dropdown",
                    "options": [
                        i18n.t("components.operations.group_by.aggregations.functions.sum"),
                        i18n.t("components.operations.group_by.aggregations.functions.count"),
                        i18n.t("components.operations.group_by.aggregations.functions.count_distinct"),
                        i18n.t("components.operations.group_by.aggregations.functions.avg"),
                        i18n.t("components.operations.group_by.aggregations.functions.min"),
                        i18n.t("components.operations.group_by.aggregations.functions.max"),
                        i18n.t("components.operations.group_by.aggregations.functions.median"),
                        i18n.t("components.operations.group_by.aggregations.functions.std"),
                        i18n.t("components.operations.group_by.aggregations.functions.first"),
                        i18n.t("components.operations.group_by.aggregations.functions.last"),
                    ],
                    "options_metadata": [
                        {
                            "value": "sum",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.sum"),
                        },
                        {
                            "value": "count",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.count"),
                        },
                        {
                            "value": "count_distinct",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.count_distinct"),
                        },
                        {
                            "value": "avg",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.avg"),
                        },
                        {
                            "value": "min",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.min"),
                        },
                        {
                            "value": "max",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.max"),
                        },
                        {
                            "value": "median",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.median"),
                        },
                        {
                            "value": "std",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.std"),
                        },
                        {
                            "value": "first",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.first"),
                        },
                        {
                            "value": "last",
                            "label": i18n.t("components.operations.group_by.aggregations.functions.last"),
                        },
                    ],
                    "required": True,
                    "description": i18n.t("components.operations.group_by.aggregations.agg_function_desc"),
                },
                {
                    "name": "alias",
                    "display_name": i18n.t("components.operations.group_by.aggregations.alias"),
                    "type": "str",
                    "description": i18n.t("components.operations.group_by.aggregations.alias_desc"),
                },
            ],
            value=[],
            required=False,  # 修改为非必需 - 允许只分组不聚合
            advanced=False,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.operations.group_by.aggregations.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="drop_na",
            display_name=i18n.t("components.operations.group_by.drop_na.display_name"),
            info=i18n.t("components.operations.group_by.drop_na.info"),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="sort_results",
            display_name=i18n.t("components.operations.group_by.sort_results.display_name"),
            info=i18n.t("components.operations.group_by.sort_results.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.operations.group_by.outputs.data.display_name"),
            method="group_data",
        ),
        Output(
            name="preview_data",
            display_name=i18n.t("components.operations.group_by.outputs.preview_data.display_name"),
            method="get_preview_data",
        ),
        Output(
            name="group_stats",
            display_name=i18n.t("components.operations.group_by.outputs.group_stats.display_name"),
            method="get_group_stats",
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
        logger.info(f"[GroupBy] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button clicks for field analysis
        if action == "analyze_fields" and field_name in ["group_by_columns", "aggregations"]:
            logger.info(f"[GroupBy] Field analysis triggered for {field_name}")

            try:
                # Try to get graph_data and node_id from build_config
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        # PlaceholderGraph - no data available
                        logger.warning("[GroupBy] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[GroupBy] No graph data available")
                    self.status = i18n.t("components.operations.group_by.errors.no_graph_data")
                    return build_config

                field_names = []

                # Primary strategy: Try to execute upstream node to get actual data
                # Enhanced with retry mechanism for "has not been built yet" errors
                max_retries = 2
                upstream_data = None

                for attempt in range(max_retries):
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        if upstream_data:
                            # Extract field names from upstream data
                            field_names = self._extract_field_names(upstream_data)
                            logger.info(
                                f"[GroupBy] Extracted {len(field_names)} fields from upstream data (attempt {attempt + 1})"
                            )
                            break
                        logger.warning(f"[GroupBy] No data returned from upstream node (attempt {attempt + 1})")

                    except ValueError as e:
                        error_msg = str(e)
                        if "has not been built yet" in error_msg and attempt < max_retries - 1:
                            logger.warning(
                                f"[GroupBy] Upstream node not built, retrying... (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(0.2)  # Brief delay before retry
                            continue
                        # Fallback strategy: Extract from upstream node configuration
                        logger.warning(
                            f"[GroupBy] Upstream execution failed after {attempt + 1} attempts: {e}. Trying static analysis..."
                        )
                        break
                    except Exception as e:
                        logger.warning(
                            f"[GroupBy] Unexpected error during upstream execution: {e}. Falling back to static analysis..."
                        )
                        break

                # If we couldn't get data from execution, try static analysis
                if not upstream_data:
                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        fields = find_and_extract_upstream_fields(graph_data, node_id, "data_input", "GroupBy")

                        if fields:
                            field_names = [field["name"] for field in fields]
                            logger.info(f"[GroupBy] Extracted {len(field_names)} fields from static config")
                        else:
                            logger.warning("[GroupBy] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[GroupBy] Static analysis also failed")

                # Update configuration based on which table triggered the action
                if not field_names:
                    logger.warning("[GroupBy] Could not extract fields from any strategy")
                    self.status = i18n.t("components.operations.group_by.warnings.field_load_failed")
                    return build_config
                if field_name == "group_by_columns":
                    # Update dropdown options for field_name column
                    build_config["group_by_columns"]["table_schema"][0]["options"] = field_names

                    # Auto-populate with all fields (users can remove unwanted ones)
                    build_config["group_by_columns"]["value"] = [{"field_name": name} for name in field_names]
                    logger.info(f"[GroupBy] Auto-populated {len(field_names)} group by columns")

                    self.status = i18n.t(
                        "components.operations.group_by.status.analysis_success", count=len(field_names)
                    )

                elif field_name == "aggregations":
                    # Get existing values (保留用户已配置的聚合)
                    existing_values = build_config.get("aggregations", {}).get("value", [])

                    # Only update dropdown options for field_name, not the values
                    build_config["aggregations"]["table_schema"][0]["options"] = field_names

                    # If no existing configurations, pre-populate with count for all fields
                    if not existing_values or len(existing_values) == 0:
                        build_config["aggregations"]["value"] = [
                            {
                                "field_name": name,
                                "agg_function": i18n.t("components.operations.group_by.aggregations.functions.count"),
                                "alias": f"{name}_count",
                            }
                            for name in field_names
                        ]
                        logger.info(f"[GroupBy] Initial populate {len(field_names)} aggregation configurations")
                    else:
                        # Keep existing configurations, just update options
                        logger.info(
                            f"[GroupBy] Preserved {len(existing_values)} existing aggregations, "
                            f"updated {len(field_names)} field options"
                        )

                    self.status = i18n.t(
                        "components.operations.group_by.status.analysis_success", count=len(field_names)
                    )

            except ValueError as e:
                # Handle expected errors (no upstream node, etc.)
                error_msg = str(e)
                logger.warning(f"[GroupBy] Field analysis warning: {error_msg}")
                self.status = i18n.t("components.operations.group_by.errors.analysis_failed", error=error_msg)
            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[GroupBy] Field analysis failed with unexpected error")
                self.status = i18n.t("components.operations.group_by.errors.graph_not_available")

        logger.debug(f"[GroupBy] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """Extract field names from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field names
        """
        try:
            if not data_list:
                return []

            # Get first record to extract field names
            first_record = data_list[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[GroupBy] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[GroupBy] Expected dict, got {type(data_dict)}")
                return []

            field_names = list(data_dict.keys())
            logger.debug(f"[GroupBy] Extracted {len(field_names)} field names: {field_names}")
            return field_names

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[GroupBy] Failed to extract field names")
            return []

    def group_data(self) -> list[Data]:
        """Group data with optional aggregations (sum/count/avg/min/max/count_distinct).

        If no aggregations are specified, returns unique combinations of group by columns (like SQL DISTINCT).
        """
        try:
            self.status = i18n.t("components.operations.group_by.status.grouping")

            # Validate inputs
            if not self.data_input:
                raise ValueError(i18n.t("components.operations.group_by.errors.no_data"))

            if not self.group_by_columns:
                raise ValueError(i18n.t("components.operations.group_by.errors.no_group_columns"))

            # Convert to DataFrame
            df = self._convert_to_dataframe(self.data_input)

            # Extract group by columns - use all rows in the table
            group_cols = [col["field_name"] for col in self.group_by_columns if col.get("field_name")]

            if not group_cols:
                raise ValueError(i18n.t("components.operations.group_by.errors.no_group_columns_in_table"))

            # Validate group columns exist in dataframe
            missing_cols = [col for col in group_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    i18n.t("components.operations.group_by.errors.missing_columns", columns=", ".join(missing_cols))
                )

            # Check if aggregations are provided
            if not self.aggregations or len(self.aggregations) == 0:
                # No aggregations - just return unique combinations (like DISTINCT)
                logger.info("[GroupBy] No aggregations specified - returning unique group combinations")
                grouped_df = df[group_cols].drop_duplicates().reset_index(drop=True)

                # Sort if requested
                if self.sort_results:
                    grouped_df = grouped_df.sort_values(by=group_cols)

                # Convert back to Data objects
                result_data = []
                for _, row in grouped_df.iterrows():
                    row_dict = row.to_dict()
                    result_data.append(Data(data=row_dict))

                self.status = i18n.t("components.operations.group_by.status.success", groups=len(result_data))
                logger.info(f"[GroupBy] Successfully created {len(result_data)} unique groups (no aggregation)")
                return result_data

            # Build aggregation dictionary
            agg_dict = {}
            alias_mapping = {}

            for agg in self.aggregations:
                field_name = agg.get("field_name")
                agg_function = agg.get("agg_function", "").lower()
                alias = agg.get("alias", "").strip()

                if not field_name or not agg_function:
                    continue

                # Validate field exists
                if field_name not in df.columns:
                    logger.warning(f"[GroupBy] Field '{field_name}' not found in data, skipping")
                    continue

                # Map i18n function names to pandas/internal function names
                func_mapping = {
                    i18n.t("components.operations.group_by.aggregations.functions.sum"): "sum",
                    i18n.t("components.operations.group_by.aggregations.functions.count"): "count",
                    i18n.t("components.operations.group_by.aggregations.functions.count_distinct"): "count_distinct",
                    i18n.t("components.operations.group_by.aggregations.functions.avg"): "mean",
                    i18n.t("components.operations.group_by.aggregations.functions.min"): "min",
                    i18n.t("components.operations.group_by.aggregations.functions.max"): "max",
                    i18n.t("components.operations.group_by.aggregations.functions.median"): "median",
                    i18n.t("components.operations.group_by.aggregations.functions.std"): "std",
                    i18n.t("components.operations.group_by.aggregations.functions.first"): "first",
                    i18n.t("components.operations.group_by.aggregations.functions.last"): "last",
                    # Also support direct English values for backward compatibility
                    "sum": "sum",
                    "count": "count",
                    "count_distinct": "count_distinct",
                    "avg": "mean",
                    "mean": "mean",
                    "min": "min",
                    "max": "max",
                    "std": "std",
                    "median": "median",
                    "first": "first",
                    "last": "last",
                }

                pandas_func = func_mapping.get(agg_function, "count")

                # Handle count_distinct specially (use nunique in pandas)
                if pandas_func == "count_distinct":
                    pandas_func = "nunique"

                # Default alias if not provided
                if not alias:
                    alias = f"{field_name}_{pandas_func}"

                if field_name not in agg_dict:
                    agg_dict[field_name] = []

                agg_dict[field_name].append(pandas_func)
                alias_mapping[(field_name, pandas_func)] = alias

            if not agg_dict:
                # No valid aggregations - fall back to unique combinations
                logger.warning("[GroupBy] No valid aggregations configured - returning unique group combinations")
                grouped_df = df[group_cols].drop_duplicates().reset_index(drop=True)
            else:
                # Perform grouping with aggregations
                grouped_df = df.groupby(group_cols, dropna=self.drop_na).agg(agg_dict).reset_index()

                # Flatten column names and apply aliases
                if isinstance(grouped_df.columns, pd.MultiIndex):
                    new_cols = []
                    for col in grouped_df.columns:
                        if col[1]:  # If there's an aggregation function
                            alias = alias_mapping.get((col[0], col[1]), f"{col[0]}_{col[1]}")
                            new_cols.append(alias)
                        else:
                            new_cols.append(col[0])
                    grouped_df.columns = new_cols

            # Sort if requested
            if self.sort_results and group_cols:
                grouped_df = grouped_df.sort_values(by=group_cols)

            # Convert back to Data objects
            result_data = []
            for _, row in grouped_df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            self.status = i18n.t("components.operations.group_by.status.success", groups=len(result_data))
            logger.info(f"[GroupBy] Successfully created {len(result_data)} groups")
            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.group_by.errors.group_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[GroupBy] Grouping failed: {e}")
            raise ValueError(error_msg) from e

    def _convert_to_dataframe(self, data_list: list[Data]) -> pd.DataFrame:
        """Convert list of Data objects to pandas DataFrame.

        Args:
            data_list: List of Data objects

        Returns:
            pandas DataFrame
        """
        records = []
        for data_obj in data_list:
            if hasattr(data_obj, "data") and isinstance(data_obj.data, dict):
                records.append(data_obj.data)
            elif isinstance(data_obj, dict):
                records.append(data_obj)

        if not records:
            logger.warning("[GroupBy] No valid records found in data_list")
            return pd.DataFrame()

        return pd.DataFrame(records)

    def get_preview_data(self) -> list[Data]:
        """Get preview data (first 100 rows).

        Returns:
            First 100 rows of grouped data
        """
        try:
            grouped_data = self.group_data()
            preview = grouped_data[:100]
            logger.info(f"[GroupBy] Returning preview with {len(preview)} rows (max 100)")
            return preview
        except Exception as e:
            logger.error(f"[GroupBy] Failed to get preview data: {e}")
            raise

    def get_group_stats(self) -> Data:
        """Get statistics about the grouping operation.

        Returns:
            Data object containing grouping statistics
        """
        try:
            grouped = self.group_data()

            stats = {
                "group_by_columns": [col.get("field_name", "") for col in self.group_by_columns],
                "aggregations": [
                    f"{agg.get('field_name', '')}_{agg.get('agg_function', '')}" for agg in self.aggregations
                ],
                "total_groups": len(grouped),
                "input_records": len(self.data_input) if self.data_input else 0,
            }

            logger.info(f"[GroupBy] Stats: {stats}")
            return Data(data=stats)

        except Exception as e:
            logger.error(f"[GroupBy] Failed to get group stats: {e}")
            # Return empty stats rather than failing
            return Data(
                data={
                    "group_by_columns": [],
                    "aggregations": [],
                    "total_groups": 0,
                    "input_records": 0,
                    "error": str(e),
                }
            )
