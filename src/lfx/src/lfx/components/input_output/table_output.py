import asyncio
from typing import Any

import i18n
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.base.datasource.manager import DataSourceManager
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, MessageTextInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Update options for field mappings
UPDATE_OPTIONS = [
    i18n.t("components.input_output.table_output.field_mappings.update_options.sync_update"),
    i18n.t("components.input_output.table_output.field_mappings.update_options.insert_only"),
    i18n.t("components.input_output.table_output.field_mappings.update_options.update_when_has_value"),
    i18n.t("components.input_output.table_output.field_mappings.update_options.update_when_not_empty"),
    i18n.t("components.input_output.table_output.field_mappings.update_options.cumulative_update"),
    i18n.t("components.input_output.table_output.field_mappings.update_options.prohibit_update"),
]


def _format_i18n(key: str, **kwargs) -> str:
    """Format i18n text with parameter substitution."""
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


class ETLTableOutputComponent(Component):
    display_name = i18n.t("components.input_output.table_output.display_name")
    description = i18n.t("components.input_output.table_output.description")
    icon = "database"
    name = "ETLTableOutput"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_manager = DataSourceManager()

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.table_output.data_input.display_name"),
            info=i18n.t("components.input_output.table_output.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.table_output.datasource_selector.display_name"),
            info=i18n.t("components.input_output.table_output.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],
            real_time_refresh=True,
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        DropdownInput(
            name="table_selector",
            display_name=i18n.t("components.input_output.table_output.table_selector.display_name"),
            info=i18n.t("components.input_output.table_output.table_selector.info"),
            required=True,
            refresh_button=True,
            options=[],
            real_time_refresh=True,
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.input_output.table_output.field_mappings.display_name"),
            info=i18n.t("components.input_output.table_output.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.source_field"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "target_field",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.target_field"),
                    "type": "str",
                    "options": [],  # Will be populated dynamically
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.data_type"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "update_option",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.update_option"),
                    "type": "str",
                    "options": UPDATE_OPTIONS,
                    "formatter": "text",
                },
                {
                    "name": "is_key_field",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.is_key_field"),
                    "type": "bool",
                    "formatter": "boolean",
                    "description": i18n.t("components.input_output.table_output.field_mappings.is_key_field_desc"),
                },
                {
                    "name": "null_value",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.null_value"),
                    "type": "str",
                    "description": i18n.t("components.input_output.table_output.field_mappings.null_value_desc"),
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "analyze_schema",
                        "label": i18n.t("components.input_output.table_output.field_mappings.analyze_schema_button"),
                        "icon": "Search",
                        "position": "top",
                    },
                    {
                        "name": "auto_map_fields",
                        "label": i18n.t("components.input_output.table_output.field_mappings.auto_map_button"),
                        "icon": "Link",
                        "position": "top",
                    },
                ],
            },
            advanced=False,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.table_output.preview_table.display_name"),
            info=i18n.t("components.input_output.table_output.preview_table.info"),
            table_schema=[],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "preview_target_data",
                        "label": i18n.t("components.input_output.table_output.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        DropdownInput(
            name="write_mode",
            display_name=i18n.t("components.input_output.table_output.write_mode.display_name"),
            info=i18n.t("components.input_output.table_output.write_mode.info"),
            options=["batch_insert", "upsert", "replace", "append"],
            value="upsert",
        ),
        BoolInput(
            name="clear_table_first",
            display_name=i18n.t("components.input_output.table_output.clear_table_first.display_name"),
            info=i18n.t("components.input_output.table_output.clear_table_first.info"),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="auto_create_table",
            display_name=i18n.t("components.input_output.table_output.auto_create_table.display_name"),
            info=i18n.t("components.input_output.table_output.auto_create_table.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.table_output.batch_size.display_name"),
            info=i18n.t("components.input_output.table_output.batch_size.info"),
            value=1000,
            range_spec={"min": 1, "max": 100000},
            advanced=True,
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t("components.input_output.table_output.enable_transaction.display_name"),
            info=i18n.t("components.input_output.table_output.enable_transaction.info"),
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="isolation_level",
            display_name=i18n.t("components.input_output.table_output.isolation_level.display_name"),
            info=i18n.t("components.input_output.table_output.isolation_level.info"),
            options=["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "DEFAULT"],
            value="DEFAULT",
            advanced=True,
        ),
        MessageTextInput(
            name="escape_char",
            display_name=i18n.t("components.input_output.table_output.escape_char.display_name"),
            info=i18n.t("components.input_output.table_output.escape_char.info"),
            value="",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.input_output.table_output.outputs.result.display_name"),
            method="write_to_table",
        ),
        Output(
            name="row_count",
            display_name=i18n.t("components.input_output.table_output.outputs.row_count.display_name"),
            method="get_row_count",
        ),
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates based on field changes and action button clicks."""
        logger.info(
            f"[TableOutput] update_build_config called - field_name: {field_name}, "
            f"field_value: {field_value}, action: {action}"
        )

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        # 1. Load datasources on initial load or refresh
        if field_name is None or (field_name == "datasource_selector" and (not field_value or action == "refresh")):
            logger.debug(f"[TableOutput] Loading datasources (field_name={field_name}, field_value={field_value})")
            try:
                # 加载统一的数据源列表（内置 + 公共）
                all_datasources = self._load_unified_datasources()

                # 构建显示选项和元数据
                options = []
                options_metadata = []

                for ds in all_datasources:
                    options.append(ds["display_name"])
                    # 使用 options_metadata 存储完整信息
                    options_metadata.append(
                        {
                            "id": ds["id"],
                            "name": ds["name"],
                            "type": ds["type"],
                            "source": ds["source"],
                            "display_name": ds["display_name"],
                            "raw_data": ds.get("raw_data"),  # 公共数据源的原始数据
                        }
                    )

                build_config["datasource_selector"]["options"] = options
                build_config["datasource_selector"]["options_metadata"] = options_metadata
                logger.debug(f"[TableOutput] Set datasource_selector options: {options}")
                logger.debug(f"[TableOutput] Set options_metadata with {len(options_metadata)} entries")

            except Exception as e:
                logger.error(f"[TableOutput] Error loading unified datasources: {e}")
                import traceback

                logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
                # 设置错误选项
                build_config["datasource_selector"]["options"] = ["加载失败"]
                build_config["datasource_selector"]["options_metadata"] = []

        # 2. When datasource is selected OR table_selector refresh button clicked, load tables
        should_load_tables = False
        target_datasource = None

        logger.debug(
            f"[TableOutput] Checking table loading conditions - field_name={field_name}, "
            f"field_value={field_value}, action={action}"
        )

        # Case 1: Datasource just selected
        if field_name == "datasource_selector" and field_value:
            should_load_tables = True
            target_datasource = field_value
            logger.debug(f"[TableOutput] Datasource selected: {target_datasource}")

        # Case 2: Table selector refresh button clicked
        elif field_name == "table_selector" and action == "refresh":
            logger.debug("[TableOutput] Detected table_selector refresh action")
            # Get current datasource from build_config
            target_datasource = build_config.get("datasource_selector", {}).get("value")
            logger.debug(f"[TableOutput] Current datasource from build_config: {target_datasource}")
            if target_datasource:
                should_load_tables = True
                logger.debug(f"[TableOutput] Table selector refresh clicked, using datasource: {target_datasource}")
            else:
                logger.warning("[TableOutput] Cannot refresh tables: no datasource selected")
                self.status = i18n.t("components.input_output.table_output.errors.no_datasource")

        if should_load_tables and target_datasource:
            try:
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_id = self._get_datasource_id_from_metadata(target_datasource, options_metadata)

                if datasource_id:
                    # 获取数据源信息以判断是否为公共数据源
                    datasource_info = None
                    for metadata in options_metadata:
                        if metadata.get("display_name") == target_datasource:
                            datasource_info = metadata
                            break

                    # 公共数据源不支持表列表加载，跳过
                    if datasource_info and datasource_info.get("source") == "public":
                        logger.info(f"[TableOutput] Skipping table loading for public datasource: {target_datasource}")
                        build_config["table_selector"]["options"] = []
                        self.status = i18n.t("components.input_output.table_output.status.public_datasource_selected")
                    else:
                        logger.debug(f"[TableOutput] Loading tables for datasource ID: {datasource_id}")
                        # Load tables for this datasource
                        with httpx.Client(timeout=10.0) as client:
                            response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/tables")
                            logger.debug(f"[TableOutput] Tables API response status: {response.status_code}")

                            if response.status_code == 200:
                                tables = response.json()
                                logger.debug(f"[TableOutput] Loaded {len(tables)} tables from datasource: {tables}")

                                build_config["table_selector"]["options"] = sorted(tables)
                                logger.debug(f"[TableOutput] Set table_selector options to {len(tables)} tables")
                                self.status = i18n.t(
                                    "components.input_output.table_output.status.tables_loaded", count=len(tables)
                                )
                            else:
                                logger.warning(
                                    f"[TableOutput] Failed to load tables, status: {response.status_code}, body: {response.text}"
                                )
                                self.status = i18n.t("components.input_output.table_output.errors.load_tables_failed")
                else:
                    logger.error(f"[TableOutput] Cannot find datasource ID for: {target_datasource}")
                    self.status = i18n.t("components.input_output.table_output.errors.no_datasource")
            except Exception as e:
                logger.error(f"[TableOutput] Error loading tables: {e}")
                import traceback

                logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t("components.input_output.table_output.errors.load_tables_failed")

        # 3. When table is selected, load target field list for dropdown
        if field_name == "table_selector" and field_value:
            current_table = field_value
            current_datasource = build_config.get("datasource_selector", {}).get("value")

            logger.debug(f"[TableOutput] Table selected: {current_table}")

            if current_datasource:
                try:
                    options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                    datasource_id = self._get_datasource_id_from_metadata(current_datasource, options_metadata)

                    if datasource_id:
                        # 获取数据源信息以判断是否为公共数据源
                        datasource_info = None
                        for metadata in options_metadata:
                            if metadata.get("display_name") == current_datasource:
                                datasource_info = metadata
                                break

                        # 公共数据源不支持列加载，跳过
                        if datasource_info and datasource_info.get("source") == "public":
                            logger.info("[TableOutput] Skipping column loading for public datasource")
                        else:
                            # Load columns for the target table
                            with httpx.Client(timeout=10.0) as client:
                                response = client.get(
                                    f"{api_url}/api/v1/datasources/{datasource_id}/tables/{current_table}/columns"
                                )

                                if response.status_code == 200:
                                    columns = response.json()
                                    logger.debug(f"[TableOutput] Loaded {len(columns)} columns for table")

                                    # Update target_field dropdown options in field_mappings
                                    target_field_names = [col["name"] for col in columns]

                                    # Find the target_field column in table_schema
                                    for schema_col in build_config["field_mappings"]["table_schema"]:
                                        if schema_col["name"] == "target_field":
                                            schema_col["options"] = target_field_names
                                            logger.debug(
                                                f"[TableOutput] Updated target_field options: {target_field_names[:5]}..."
                                            )
                                            break
                                else:
                                    logger.warning(
                                        f"[TableOutput] Failed to load columns, status: {response.status_code}"
                                    )
                except Exception as e:
                    logger.error(f"[TableOutput] Error loading columns: {e}")

        # 4. Handle "Analyze Schema" button - analyze input data structure
        if field_name == "field_mappings" and action == "analyze_schema":
            logger.info("[TableOutput] Schema analysis triggered by action button")

            try:
                # Get graph data and node ID from build_config
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[TableOutput] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[TableOutput] No graph data available for schema analysis")
                    self.status = i18n.t("components.input_output.table_output.errors.no_graph_data")
                    return build_config

                # Use the generic get_upstream_data method to fetch actual data
                self.status = i18n.t("components.input_output.table_output.status.analyzing_schema")

                # 在同步上下文中运行异步方法
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在运行的事件循环中，使用 run_coroutine_threadsafe
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.get_upstream_data(input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id)
                            )
                            upstream_data = future.result(timeout=10)
                    else:
                        upstream_data = asyncio.run(
                            self.get_upstream_data(input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id)
                        )
                except Exception as e:
                    logger.error(f"[TableOutput] Error getting upstream data: {e}")
                    upstream_data = None

                if not upstream_data:
                    logger.warning("[TableOutput] No data returned from upstream node")
                    self.status = i18n.t("components.input_output.table_output.status.no_input_data")
                    return build_config

                # Extract field structure from upstream data
                field_info = self._extract_field_info_from_data(upstream_data)

                if field_info:
                    build_config["field_mappings"]["value"] = field_info
                    logger.info(f"[TableOutput] Schema analysis completed, generated {len(field_info)} field mappings")
                    self.status = i18n.t(
                        "components.input_output.table_output.status.analysis_success", count=len(field_info)
                    )
                else:
                    logger.warning("[TableOutput] No fields extracted from upstream data")
                    self.status = i18n.t("components.input_output.table_output.status.no_input_data")

            except ValueError as e:
                # Handle expected errors (no upstream node, etc.)
                error_msg = str(e)
                logger.warning(f"[TableOutput] Schema analysis warning: {error_msg}")
                self.status = i18n.t("components.input_output.table_output.errors.analysis_failed", error=error_msg)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[TableOutput] Schema analysis failed: {error_msg}")
                import traceback

                logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t("components.input_output.table_output.errors.analysis_failed", error=error_msg)

        # 5. Handle "Auto Map Fields" button - auto-match source to target fields
        if field_name == "field_mappings" and action == "auto_map_fields":
            logger.info("[TableOutput] Auto field mapping triggered by action button")

            try:
                self.status = _format_i18n("components.input_output.table_output.status.mapping_fields")

                current_mappings = build_config.get("field_mappings", {}).get("value", [])

                if not current_mappings:
                    logger.warning("[TableOutput] No field mappings to auto-map")
                    self.status = i18n.t("components.input_output.table_output.status.no_fields_to_map")
                    return build_config

                # Get target field options
                target_field_options = []
                for schema_col in build_config["field_mappings"]["table_schema"]:
                    if schema_col["name"] == "target_field":
                        target_field_options = schema_col.get("options", [])
                        break

                if not target_field_options:
                    logger.warning("[TableOutput] No target fields available for auto-mapping")
                    self.status = i18n.t("components.input_output.table_output.status.no_target_fields")
                    return build_config

                # Auto-map: match source field to target field by name (case-insensitive)
                mapped_count = 0
                for mapping in current_mappings:
                    source_field = mapping.get("source_field", "").lower()

                    # Try exact match first
                    for target_field in target_field_options:
                        if target_field.lower() == source_field:
                            mapping["target_field"] = target_field
                            mapped_count += 1
                            break
                    else:
                        # If no exact match, leave as is or set to first option
                        if not mapping.get("target_field"):
                            mapping["target_field"] = mapping.get("source_field", "")

                build_config["field_mappings"]["value"] = current_mappings
                logger.info(f"[TableOutput] Auto-mapping completed, mapped {mapped_count} fields")
                self.status = _format_i18n(
                    "components.input_output.table_output.status.mapping_success", count=mapped_count
                )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[TableOutput] Auto field mapping failed: {error_msg}")
                self.status = _format_i18n(
                    "components.input_output.table_output.errors.mapping_failed", error=error_msg
                )

        # 6. Handle "Preview Output Data" button - preview transformed data to be written
        if field_name == "preview_table" and action == "preview_target_data":
            logger.info("[TableOutput] Output data preview triggered by action button")

            try:
                # Get graph data and node ID from build_config
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[TableOutput] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[TableOutput] No graph data available for output preview")
                    self.status = i18n.t("components.input_output.table_output.errors.no_graph_data")
                    return build_config

                # Use the generic get_upstream_data method to fetch actual data
                self.status = i18n.t("components.input_output.table_output.status.previewing_data")

                # 在同步上下文中运行异步方法
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在运行的事件循环中，使用 run_coroutine_threadsafe
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.get_upstream_data(input_name="data_input", graph_data=graph_data, sample_size=100, vertex_id=node_id)
                            )
                            upstream_data = future.result(timeout=10)
                    else:
                        upstream_data = asyncio.run(
                            self.get_upstream_data(input_name="data_input", graph_data=graph_data, sample_size=100, vertex_id=node_id)
                        )
                except Exception as e:
                    logger.error(f"[TableOutput] Error getting upstream data for preview: {e}")
                    upstream_data = None

                if not upstream_data:
                    logger.warning("[TableOutput] No data returned from upstream node")
                    self.status = i18n.t("components.input_output.table_output.status.no_input_data")
                    build_config["preview_table"]["table_schema"] = []
                    build_config["preview_table"]["value"] = []
                    return build_config

                # Convert upstream data to DataFrame
                df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in upstream_data])

                if df.empty:
                    logger.warning("[TableOutput] Upstream data is empty")
                    self.status = i18n.t("components.input_output.table_output.status.no_input_data")
                    build_config["preview_table"]["table_schema"] = []
                    build_config["preview_table"]["value"] = []
                    return build_config

                logger.info(f"[TableOutput] Received {len(df)} rows from upstream")

                # Apply field mappings if configured
                field_mappings = build_config.get("field_mappings", {}).get("value", [])
                if field_mappings:
                    df = self._apply_field_mappings_preview(df, field_mappings)
                    logger.info(
                        f"[TableOutput] Applied field mappings, result: {len(df)} rows, {len(df.columns)} columns"
                    )

                # Limit to 100 rows for preview
                if len(df) > 100:
                    df = df.head(100)
                    logger.info("[TableOutput] Limited preview to 100 rows")

                # Generate table schema
                table_schema = [
                    {
                        "name": str(col),
                        "display_name": str(col),
                        "type": "str",
                        "disable_edit": True,
                    }
                    for col in df.columns
                ]

                # Convert DataFrame to list of dicts
                preview_data = df.fillna("").to_dict("records")

                # Update preview table config
                build_config["preview_table"]["table_schema"] = table_schema
                build_config["preview_table"]["value"] = preview_data

                logger.info(f"[TableOutput] Output preview completed, showing {len(preview_data)} rows")
                self.status = i18n.t(
                    "components.input_output.table_output.status.preview_success", count=len(preview_data)
                )

            except ValueError as e:
                # Handle expected errors (no upstream node, etc.)
                error_msg = str(e)
                logger.warning(f"[TableOutput] Output preview warning: {error_msg}")
                self.status = i18n.t("components.input_output.table_output.errors.preview_failed", error=error_msg)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                logger.error(f"[TableOutput] Output preview failed: {error_msg}")
                import traceback

                logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t("components.input_output.table_output.errors.preview_failed", error=error_msg)

        logger.debug(f"[TableOutput] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_uuid_from_id(self, datasource_id: str) -> str:
        """从数据源ID中提取纯UUID，移除可能的前缀"""
        if not datasource_id:
            return datasource_id

        # 检查是否有前缀（如 custom_, enterprise_ 等）
        if "_" in datasource_id:
            parts = datasource_id.split("_", 1)
            if len(parts) == 2:
                prefix, uuid_part = parts
                # 验证uuid_part是否符合UUID格式（包含-字符且长度正确）
                if "-" in uuid_part and len(uuid_part) == 36:  # UUID标准格式长度为36个字符
                    logger.debug(f"[TableOutput] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                    return uuid_part

        # 如果没有前缀或不符合UUID格式，直接返回
        return datasource_id

    def _get_datasource_id_from_metadata(self, display_name: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据显示名称获取数据源ID"""
        for metadata in options_metadata:
            if metadata.get("display_name") == display_name:
                datasource_id = metadata.get("id")
                logger.debug(f"[TableOutput] Found datasource ID '{datasource_id}' for display name '{display_name}'")
                return datasource_id

        logger.warning(f"[TableOutput] No metadata found for display name: {display_name}")
        return None

    def _load_unified_datasources(self) -> list[dict]:
        """加载统一的数据源列表（内置数据源 + 公共数据源）"""
        try:
            # 获取内置数据源
            logger.debug("[TableOutput] Starting to load builtin datasources...")
            builtin_datasources = self._get_builtin_datasources()
            logger.info(f"[TableOutput] Loaded {len(builtin_datasources)} builtin datasources")
            if builtin_datasources:
                logger.debug(f"[TableOutput] Builtin datasource sample: {builtin_datasources[0]}")

            # 获取公共数据源
            try:
                logger.debug("[TableOutput] Starting to load public datasources...")
                public_datasources = asyncio.run(self._get_public_datasources())
                logger.info(f"[TableOutput] Loaded {len(public_datasources)} public datasources")
                if public_datasources:
                    logger.debug(f"[TableOutput] Public datasource sample: {public_datasources[0]}")
            except Exception as e:
                logger.warning(f"[TableOutput] Failed to get public datasources: {e}")
                import traceback
                logger.debug(f"[TableOutput] Public datasource error traceback: {traceback.format_exc()}")
                public_datasources = []

            # 合并数据源列表
            all_datasources = []

            # 添加内置数据源
            for ds in builtin_datasources:
                display_name = f"{ds['name']} ({ds['type']}) [自定义]"
                all_datasources.append(
                    {
                        "id": str(ds["id"]),
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "builtin",
                        "display_name": display_name,
                    }
                )

            # 添加公共数据源
            for ds in public_datasources:
                display_name = self._build_display_name(ds, "public")
                all_datasources.append(
                    {
                        "id": str(ds["id"]),
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "public",
                        "display_name": display_name,
                        "raw_data": ds,
                    }
                )

            logger.info(
                f"[TableOutput] Loaded {len(all_datasources)} datasources ({len(builtin_datasources)} builtin, {len(public_datasources)} public)"
            )
            if all_datasources:
                logger.debug(f"[TableOutput] Final datasource list sample: {all_datasources[0]}")
            return all_datasources

        except Exception as e:
            logger.error(f"[TableOutput] Error loading unified datasources: {e}")
            import traceback
            logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
            return []

    def _get_builtin_datasources(self) -> list[dict]:
        """获取内置数据源"""
        try:
            logger.debug("[TableOutput] Calling datasource_manager.get_datasources()...")
            datasources = asyncio.run(self.datasource_manager.get_datasources())
            logger.debug(f"[TableOutput] Got raw datasources: {datasources}")

            builtin_datasources = []

            # 合并企业和自定义数据源
            enterprise_list = datasources.get("enterprise", [])
            custom_list = datasources.get("custom", [])

            logger.debug(f"[TableOutput] Enterprise datasources: {len(enterprise_list)} items")
            logger.debug(f"[TableOutput] Custom datasources: {len(custom_list)} items")

            for ds in enterprise_list:
                # 企业数据源ID通常不需要前缀，直接使用
                datasource_id = self._extract_uuid_from_id(ds["id"])
                builtin_datasources.append(
                    {"id": datasource_id, "name": ds["name"], "type": ds["type"], "source": "enterprise"}
                )
                logger.debug(f"[TableOutput] Added enterprise datasource: {ds['name']} -> {datasource_id}")

            for ds in custom_list:
                # 自定义数据源ID可能包含前缀，需要提取纯UUID
                datasource_id = self._extract_uuid_from_id(ds["id"])
                builtin_datasources.append(
                    {"id": datasource_id, "name": ds["name"], "type": ds["type"], "source": "custom"}
                )
                logger.debug(f"[TableOutput] Added custom datasource: {ds['name']} -> {datasource_id}")

            logger.info(f"[TableOutput] Total builtin datasources processed: {len(builtin_datasources)}")
            return builtin_datasources

        except Exception as e:
            logger.error(f"[TableOutput] Error getting builtin datasources: {e}")
            import traceback
            logger.error(f"[TableOutput] Builtin datasource error traceback: {traceback.format_exc()}")
            return []

    async def _get_public_datasources(self) -> list[dict]:
        """通过feign接口获取公共数据源"""
        try:
            logger.debug("[TableOutput] Initializing feign client...")
            from lfx.services.deps import get_feign_service

            feign_service = get_feign_service()
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            client = DataConstructionFeignClient(feign_service)
            logger.info("[TableOutput] Calling feign API to get datasource list...")

            # 调用feign接口获取数据源列表
            datasource_list = asyncio.run(client.get_datasource_list())

            logger.info(f"[TableOutput] Got {len(datasource_list)} public datasources from feign API")
            logger.debug(f"[TableOutput] Public datasource sample: {datasource_list[:1] if datasource_list else 'None'}")
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[TableOutput] Failed to get public datasources: {e}")
            import traceback
            logger.error(f"[TableOutput] Feign client error traceback: {traceback.format_exc()}")
            return []

    def _build_display_name(self, datasource: dict, source: str) -> str:
        """构建丰富的显示名称"""
        base_name = f"{datasource['name']} ({datasource['type']})"

        # 来源标识
        source_label = "[公共]" if source == "public" else "[自定义]"

        # 附加信息标签
        extra_labels = []

        if source == "public":
            # 公共数据源的额外信息
            raw_data = datasource.get("raw_data", datasource)

            # 环境信息
            if raw_data.get("environment"):
                extra_labels.append(f"[{raw_data['environment']}]")

            # 认证方式
            if raw_data.get("authType") == "kerberos":
                extra_labels.append("[Kerberos认证]")
            elif raw_data.get("authType") == "basic":
                extra_labels.append("[用户名密码]")

            # 版本信息
            if raw_data.get("version"):
                extra_labels.append(f"[{raw_data['version']}]")

            # Hive特殊标识
            if datasource.get("type", "").lower() == "hive":
                extra_labels.append("[Hive数据仓库]")

        else:
            # 内置数据源的额外信息
            if datasource.get("source") == "enterprise":
                extra_labels.append("[企业]")

            # 连接状态
            if datasource.get("status") == "connected":
                extra_labels.append("[已连接]")

        # 组合最终显示名称
        if extra_labels:
            return f"{base_name} {source_label} {' '.join(extra_labels)}"
        return f"{base_name} {source_label}"

    def _get_connection_string(self, datasource_id: str, datasource_info: dict = None) -> str:
        """获取数据源连接字符串，支持内置和公共数据源"""
        if datasource_info and datasource_info.get("source") == "public":
            # 公共数据源：从raw_data构建连接字符串
            return self._build_public_connection_string(datasource_info["raw_data"])
        # 内置数据源：使用现有逻辑
        return self._get_builtin_connection_string(datasource_id)

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        ds_type = raw_data.get("type", "mysql").lower()
        params = raw_data.get("dataSourceParam", {})

        if ds_type == "hive":
            # Hive连接字符串构建
            host = params.get("host")
            port = params.get("port", 10000)
            database = params.get("database", "default")
            username = params.get("username", "hive")
            password = params.get("password", "")

            # 构建Hive JDBC连接字符串
            conn_str = f"jdbc:hive2://{host}:{port}/{database}"

            # 添加认证参数
            if password:
                from urllib.parse import quote_plus

                password_encoded = quote_plus(password)
                conn_str += f"?user={username};password={password_encoded}"
            elif username and username != "hive":
                from urllib.parse import quote_plus

                username_encoded = quote_plus(username)
                conn_str += f"?user={username_encoded}"

            return conn_str

        # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
        return self._build_connection_string_from_params(ds_type, params)

    def _build_connection_string_from_params(self, ds_type: str, params: dict) -> str:
        """从参数构建连接字符串"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 3306)
        database = params.get("database", "")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username)
        password_encoded = quote_plus(password)

        if ds_type == "mysql":
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "postgresql":
            return f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "oracle":
            return f"oracle+cx_oracle://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "mssql":
            return f"mssql+pymssql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        raise ValueError(f"Unsupported database type: {ds_type}")

    def _get_builtin_connection_string(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                if response.status_code != 200:
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError(i18n.t("components.input_output.table_output.errors.connection_string_empty"))

                return connection_string
        except Exception as e:
            logger.error(f"[TableOutput] Error getting builtin connection string: {e}")
            raise

    def _get_connection_string_sync(self, datasource_id: str, datasource_info: dict = None) -> str:
        """获取数据源连接字符串，支持内置和公共数据源"""
        if datasource_info and datasource_info.get("source") == "public":
            # 公共数据源：从raw_data构建连接字符串
            return self._build_public_connection_string(datasource_info["raw_data"])
        # 内置数据源：使用现有逻辑
        return self._get_builtin_connection_string_sync(datasource_id)

    def _get_builtin_connection_string_sync(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串（同步版本）"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                if response.status_code != 200:
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError(i18n.t("components.input_output.table_output.errors.connection_string_empty"))

                return connection_string
        except Exception as e:
            logger.error(f"[TableOutput] Error getting builtin connection string: {e}")
            raise

    def _extract_field_info_from_data(self, data_list: list[Data]) -> list[dict]:
        """Extract field information from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field mapping dictionaries with source_field, target_field, data_type, etc.
        """
        try:
            if not data_list:
                return []

            # Get first record to extract field names and types
            first_record = data_list[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[TableOutput] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[TableOutput] Expected dict, got {type(data_dict)}")
                return []

            # Generate field mappings from field names
            field_info = []
            for field_name, value in data_dict.items():
                data_type = self._infer_data_type(value)
                field_info.append(
                    {
                        "source_field": field_name,
                        "target_field": field_name,  # Default to same name
                        "data_type": data_type,
                        "update_option": "sync_update",
                        "is_key_field": False,
                        "null_value": "",
                    }
                )

            logger.info(f"[TableOutput] Extracted {len(field_info)} fields from upstream data")
            return field_info

        except Exception as e:
            logger.error(f"[TableOutput] Error extracting field info: {e}")
            return []

    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from value."""
        if value is None:
            return "string"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        return "string"

    def _get_datasource_id(self) -> str:
        """从选中的显示名称获取实际的数据源ID（支持内置和公共数据源）"""
        if not self.datasource_selector:
            raise ValueError(i18n.t("components.input_output.table_output.errors.no_datasource_selected"))

        try:
            # 加载统一的数据源列表
            all_datasources = self._load_unified_datasources()

            # 查找匹配的数据源
            for ds in all_datasources:
                if ds["display_name"] == self.datasource_selector:
                    datasource_id = ds["id"]
                    source = ds["source"]

                    # 保存数据源信息供后续使用
                    self._current_datasource_info = {
                        "id": datasource_id,
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": source,
                        "display_name": ds["display_name"],
                        "raw_data": ds.get("raw_data"),
                    }

                    logger.debug(
                        f"[TableOutput] Found datasource ID '{datasource_id}' ({source}) for '{self.datasource_selector}'"
                    )
                    return datasource_id

            # 如果没找到匹配的显示名称，尝试直接使用作为ID（向后兼容）
            logger.warning(f"[TableOutput] Display name '{self.datasource_selector}' not found, trying as direct ID")
            return self.datasource_selector

        except Exception as e:
            logger.error(f"[TableOutput] Error getting datasource ID: {e}")
            raise ValueError(f"Cannot determine datasource ID: {e}")

    def write_to_table(self) -> Data:
        """Write data to database table with multiple write modes."""
        try:
            logger.info("[TableOutput] write_to_table called")
            self.status = _format_i18n("components.input_output.table_output.status.writing")

            # 1. Validate inputs
            if not self.data_input:
                error_msg = i18n.t("components.input_output.table_output.errors.no_data")
                self.status = error_msg
                raise ValueError(error_msg)

            if not self.datasource_selector:
                error_msg = i18n.t("components.input_output.table_output.errors.no_datasource")
                self.status = error_msg
                raise ValueError(error_msg)

            if not self.table_selector:
                error_msg = i18n.t("components.input_output.table_output.errors.no_table")
                self.status = error_msg
                raise ValueError(error_msg)

            # 2. Get datasource ID and connection string
            datasource_id = self._get_datasource_id()
            logger.debug(f"[TableOutput] Using datasource ID: {datasource_id}")

            # Get connection string (supports both builtin and public datasources)
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string_sync(datasource_id, datasource_info)

            # 3. Convert data to DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            if df.empty:
                error_msg = i18n.t("components.input_output.table_output.errors.empty_dataframe")
                self.status = error_msg
                raise ValueError(error_msg)

            logger.info(f"[TableOutput] Processing {len(df)} rows to table '{self.table_selector}'")

            # 4. Apply field mappings if configured
            if self.field_mappings:
                df = self._apply_field_mappings(df)

            # 5. Create database engine
            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                isolation_level=self.isolation_level if self.isolation_level != "DEFAULT" else None,
            )

            rows_written = 0

            try:
                with engine.connect() as connection:
                    # Start transaction if enabled
                    if self.enable_transaction:
                        trans = connection.begin()
                        try:
                            rows_written = self._execute_write(connection, df)
                            trans.commit()
                        except Exception as e:
                            trans.rollback()
                            raise e
                    else:
                        rows_written = self._execute_write(connection, df)

            finally:
                engine.dispose()

            # 6. Build result
            result_info = {
                "success": True,
                "table": self.table_selector,
                "rows_written": rows_written,
                "write_mode": self.write_mode,
                "datasource": self.datasource_selector,
            }

            success_msg = _format_i18n(
                "components.input_output.table_output.status.success", rows=rows_written, table=self.table_selector
            )
            self.status = success_msg
            logger.info(f"[TableOutput] {success_msg}")

            return Data(data=result_info)

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            formatted_error = _format_i18n(
                "components.input_output.table_output.errors.write_failed", error_type=error_type, error=error_msg
            )

            self.status = formatted_error
            logger.exception(f"[TableOutput] Write failed: {formatted_error}")
            raise ValueError(formatted_error) from e

    def _apply_field_mappings_preview(self, df: pd.DataFrame, field_mappings: list[dict]) -> pd.DataFrame:
        """Apply field mappings for preview (without database access).

        Args:
            df: Source DataFrame
            field_mappings: List of field mapping configurations

        Returns:
            Transformed DataFrame with target field names
        """
        logger.debug("[TableOutput] Applying field mappings for preview")

        # Build mapping dict: source_field -> target_field
        field_map = {}
        null_value_map = {}

        for mapping in field_mappings:
            source = mapping.get("source_field")
            target = mapping.get("target_field")
            null_value = mapping.get("null_value", "")

            if source and target:
                field_map[source] = target

                if null_value:
                    null_value_map[target] = null_value

        # Only keep mapped fields
        mapped_sources = [src for src in field_map if src in df.columns]
        df_filtered = df[mapped_sources].copy()

        # Rename columns
        df_renamed = df_filtered.rename(columns=field_map)

        # Apply null value replacements
        for target_field, null_value in null_value_map.items():
            if target_field in df_renamed.columns:
                df_renamed[target_field] = df_renamed[target_field].fillna(null_value)

        logger.debug(
            f"[TableOutput] Field mappings applied for preview: {len(field_map)} fields mapped, "
            f"{len(df_renamed.columns)} columns in result"
        )
        return df_renamed

    def _apply_field_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply field mappings and transformations to DataFrame."""
        logger.debug("[TableOutput] Applying field mappings")

        # Build mapping dict: source_field -> target_field
        field_map = {}
        null_value_map = {}

        for mapping in self.field_mappings:
            source = mapping.get("source_field")
            target = mapping.get("target_field")
            null_value = mapping.get("null_value", "")

            if source and target:
                field_map[source] = target

                if null_value:
                    null_value_map[target] = null_value

        # Rename columns
        df_renamed = df.rename(columns=field_map)

        # Apply null value replacements
        for target_field, null_value in null_value_map.items():
            if target_field in df_renamed.columns:
                df_renamed[target_field] = df_renamed[target_field].fillna(null_value)

        logger.debug(f"[TableOutput] Field mappings applied: {len(field_map)} fields mapped")
        return df_renamed

    def _execute_write(self, connection, df: pd.DataFrame) -> int:
        """Execute write operation based on write mode."""
        logger.debug(f"[TableOutput] Executing write mode: {self.write_mode}")

        # Handle truncate first option
        if self.clear_table_first:
            logger.info(f"[TableOutput] Clearing table '{self.table_selector}' before write")
            connection.execute(text(f"TRUNCATE TABLE {self.table_selector}"))
            connection.commit()

        # Execute write based on mode
        if self.write_mode == "batch_insert":
            return self._write_batch_insert(connection, df)
        if self.write_mode == "upsert":
            return self._write_upsert(connection, df)
        if self.write_mode == "replace":
            return self._write_replace(connection, df)
        if self.write_mode == "append":
            return self._write_append(connection, df)
        raise ValueError(f"Unknown write mode: {self.write_mode}")

    def _write_batch_insert(self, connection, df: pd.DataFrame) -> int:
        """Fast batch insert without duplicate checking."""
        logger.debug(f"[TableOutput] Batch insert: {len(df)} rows")

        df.to_sql(
            self.table_selector,
            connection,
            if_exists="append",
            index=False,
            chunksize=self.batch_size,
            method="multi",
        )

        return len(df)

    def _write_append(self, connection, df: pd.DataFrame) -> int:
        """Simple append mode - same as batch insert."""
        return self._write_batch_insert(connection, df)

    def _write_replace(self, connection, df: pd.DataFrame) -> int:
        """Replace mode - truncate and insert."""
        logger.debug(f"[TableOutput] Replace mode: truncating and inserting {len(df)} rows")

        df.to_sql(
            self.table_selector, connection, if_exists="replace", index=False, chunksize=self.batch_size, method="multi"
        )

        return len(df)

    def _write_upsert(self, connection, df: pd.DataFrame) -> int:
        """Upsert mode - insert or update based on key fields."""
        if not self.field_mappings:
            raise ValueError(i18n.t("components.input_output.table_output.errors.no_field_mappings"))

        # Get key fields
        key_fields = [
            mapping.get("target_field")
            for mapping in self.field_mappings
            if mapping.get("is_key_field") and mapping.get("target_field")
        ]

        if not key_fields:
            raise ValueError(i18n.t("components.input_output.table_output.errors.no_key_fields"))

        logger.debug(f"[TableOutput] Upsert mode with key fields: {key_fields}")

        # Get update options for each field
        update_options = {}
        for mapping in self.field_mappings:
            target_field = mapping.get("target_field")
            update_option = mapping.get("update_option", "sync_update")
            if target_field:
                update_options[target_field] = update_option

        rows_written = 0

        for _, row in df.iterrows():
            row_dict = row.to_dict()

            # Build WHERE clause for key fields
            where_clause = " AND ".join([f"{col} = :{col}" for col in key_fields])

            # Check if record exists
            check_query = f"SELECT COUNT(*) FROM {self.table_selector} WHERE {where_clause}"
            params = {col: row_dict.get(col) for col in key_fields}

            result = connection.execute(text(check_query), params).scalar()

            if result > 0:
                # UPDATE existing record
                update_fields = []
                update_params = {}

                for col in df.columns:
                    if col not in key_fields:  # Don't update key fields
                        update_option = update_options.get(col, "sync_update")

                        # Apply update option logic
                        if update_option == "prohibit_update":
                            continue  # Skip this field
                        if update_option == "insert_only":
                            continue  # Only insert, don't update
                        if update_option == "update_when_has_value":
                            if pd.isna(row_dict.get(col)) or row_dict.get(col) is None:
                                continue  # Skip if no value
                        elif update_option == "update_when_not_empty":
                            if pd.isna(row_dict.get(col)) or row_dict.get(col) == "":
                                continue  # Skip if empty
                        elif update_option == "cumulative_update":
                            # Add to existing value
                            update_fields.append(f"{col} = {col} + :{col}")
                            update_params[col] = row_dict.get(col, 0)
                            continue

                        # Default: sync_update
                        update_fields.append(f"{col} = :{col}")
                        update_params[col] = row_dict.get(col)

                if update_fields:
                    update_set = ", ".join(update_fields)
                    update_query = f"UPDATE {self.table_selector} SET {update_set} WHERE {where_clause}"

                    # Merge params (key fields + update fields)
                    all_params = {**params, **update_params}

                    connection.execute(text(update_query), all_params)
                    rows_written += 1

            else:
                # INSERT new record
                cols = ", ".join(df.columns)
                placeholders = ", ".join([f":{col}" for col in df.columns])
                insert_query = f"INSERT INTO {self.table_selector} ({cols}) VALUES ({placeholders})"

                connection.execute(text(insert_query), row_dict)
                rows_written += 1

        connection.commit()
        logger.debug(f"[TableOutput] Upsert completed: {rows_written} rows affected")

        return rows_written

    def get_row_count(self) -> Data:
        """Get the count of written rows."""
        result = self.write_to_table()
        return Data(data={"row_count": result.data.get("rows_written", 0), "table": self.table_selector})
