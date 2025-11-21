import asyncio
import re
from typing import Any
from urllib.parse import unquote

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
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.table_output.field_mappings.data_type"),
                    "type": "str",
                    "disable_edit": True,
                    "formatter": "code",
                    "translate_value": False,
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

                # Table Output 排除 Kafka（Kafka 使用专门的 kafka_output 组件）
                excluded_types = {"kafka"}

                for ds in all_datasources:
                    # 过滤：排除 Kafka
                    ds_type = ds.get("type", "").lower()
                    if ds_type in excluded_types:
                        logger.debug(f"[TableOutput] Skipping excluded datasource type: {ds_type} (name={ds['name']})")
                        continue

                    # options 只包含ID (唯一值)
                    options.append(ds["id"])
                    # options_metadata 包含显示信息，使用 label 字段供前端显示
                    options_metadata.append(
                        {
                            "value": ds["id"],  # 实际值
                            "label": ds["display_name"],  # 显示名称
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
                logger.debug(f"[TableOutput] Set datasource_selector options: {options} (excluded Kafka)")
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

            # 检测是否为Neo4j数据源，动态调整table_selector的required属性
            try:
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_info = None
                for metadata in options_metadata:
                    if metadata.get("value") == target_datasource or metadata.get("display_name") == target_datasource:
                        datasource_info = metadata
                        break

                if datasource_info:
                    datasource_type = datasource_info.get("type", "").lower()
                    logger.debug(f"[TableOutput] Detected datasource type: {datasource_type}")

                    # Neo4j不需要选择表（使用节点标签），设置为非必填
                    if datasource_type == "neo4j":
                        build_config["table_selector"]["required"] = False
                        build_config["table_selector"]["info"] = i18n.t(
                            "components.input_output.table_output.table_selector.info_neo4j"
                        )
                        logger.info("[TableOutput] Neo4j detected - table_selector set to optional")
                    else:
                        # 其他数据库恢复必填
                        build_config["table_selector"]["required"] = True
                        build_config["table_selector"]["info"] = i18n.t(
                            "components.input_output.table_output.table_selector.info"
                        )
            except Exception as e:
                logger.error(f"[TableOutput] Error checking datasource type: {e}")

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
                        # 使用 value 或 id 字段匹配，而不是 display_name
                        if metadata.get("value") == target_datasource or metadata.get("id") == target_datasource:
                            datasource_info = metadata
                            break

                    # 公共数据源：使用新的表加载接口
                    if datasource_info and datasource_info.get("source") == "public":
                        logger.info(f"[TableOutput] Loading tables for public datasource: {target_datasource}")
                        try:
                            tables = self._load_public_datasource_tables(datasource_info)
                            if tables:
                                build_config["table_selector"]["options"] = sorted(tables)
                                logger.debug(f"[TableOutput] Loaded {len(tables)} tables from public datasource")
                                self.status = i18n.t(
                                    "components.input_output.table_output.status.tables_loaded", count=len(tables)
                                )
                            else:
                                build_config["table_selector"]["options"] = []
                                logger.warning(
                                    f"[TableOutput] No tables found for public datasource: {target_datasource}"
                                )
                                self.status = i18n.t("components.input_output.table_output.errors.no_tables_found")
                        except Exception as e:
                            logger.error(f"[TableOutput] Failed to load tables from public datasource: {e}")
                            build_config["table_selector"]["options"] = []
                            self.status = i18n.t("components.input_output.table_output.errors.load_tables_failed")
                    else:
                        # 提取纯UUID（移除可能的前缀）
                        clean_datasource_id = self._extract_uuid_from_id(datasource_id)
                        logger.debug(
                            f"[TableOutput] Loading tables for datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
                        )
                        # Load tables for this datasource
                        with httpx.Client(timeout=120.0) as client:
                            response = client.get(f"{api_url}/api/v1/datasources/{clean_datasource_id}/tables")
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

        # 4. Handle "Analyze Schema" button - analyze input data structure using static field extraction
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

                # Use static field extraction instead of executing upstream components
                self.status = i18n.t("components.input_output.table_output.status.analyzing_schema")
                logger.info("[TableOutput] Using static field extraction from upstream component configuration")

                try:
                    from lfx.components.helpers.field_extraction import extract_fields_from_node_template
                    from lfx.custom.graph_utils import find_upstream_node_id

                    # Find the upstream node connected to data_input
                    upstream_node_id = find_upstream_node_id(graph_data, node_id, "data_input")
                    if not upstream_node_id:
                        logger.warning("[TableOutput] No upstream node found for field analysis")
                        self.status = i18n.t("components.input_output.table_output.status.no_fields_found")
                        return build_config

                    # Find the upstream node in graph data
                    upstream_node = None
                    for node in graph_data.get("nodes", []):
                        if node.get("id") == upstream_node_id:
                            upstream_node = node
                            break

                    if not upstream_node:
                        logger.warning(f"[TableOutput] Upstream node {upstream_node_id} not found in graph data")
                        self.status = i18n.t("components.input_output.table_output.status.no_fields_found")
                        return build_config

                    # Extract field names using the same logic as FieldNameMapping
                    field_names = extract_fields_from_node_template(
                        upstream_node, component_name="TableOutput", graph_data=graph_data
                    )

                    if not field_names:
                        logger.warning("[TableOutput] No fields extracted from upstream configuration")
                        self.status = i18n.t("components.input_output.table_output.status.no_fields_found")
                        return build_config

                    logger.info(f"[TableOutput] Extracted {len(field_names)} fields from upstream: {field_names}")

                    # Convert field info (dict format) to field mapping format
                    field_info = []
                    for field_item in field_names:
                        # Handle new dict format: {"name": "field1", "type": "string"}
                        if isinstance(field_item, dict):
                            field_name = field_item.get("name")
                            data_type = field_item.get("type", "string")
                        else:
                            # Backward compatibility: if still a string
                            field_name = field_item
                            data_type = "string"

                        field_info.append(
                            {
                                "source_field": field_name,
                                "target_field": field_name,  # Default to same name
                                "data_type": data_type,  # Use extracted type
                                "update_option": UPDATE_OPTIONS[0],  # Use localized default
                                "is_key_field": False,
                                "null_value": "",
                            }
                        )

                    build_config["field_mappings"]["value"] = field_info
                    logger.info(
                        f"[TableOutput] Static field analysis completed, generated {len(field_info)} field mappings"
                    )
                    self.status = i18n.t(
                        "components.input_output.table_output.status.analysis_success", count=len(field_info)
                    )

                except Exception as e:
                    logger.error(f"[TableOutput] Static field extraction failed: {e}")
                    self.status = i18n.t("components.input_output.table_output.errors.analysis_failed", error=str(e))

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

        # 6. Handle "Preview Output Data" button - generate sample preview data from field structure
        if field_name == "preview_table" and action == "preview_target_data":
            logger.info("[TableOutput] Output data preview triggered by action button")

            try:
                # Use field mappings to generate sample preview data (no actual data execution needed)
                self.status = i18n.t("components.input_output.table_output.status.previewing_data")
                logger.info("[TableOutput] Generating sample preview data from field mappings")

                field_mappings = build_config.get("field_mappings", {}).get("value", [])
                if not field_mappings:
                    logger.warning("[TableOutput] No field mappings configured for preview")
                    self.status = i18n.t("components.input_output.table_output.status.no_fields_to_map")
                    build_config["preview_table"]["table_schema"] = []
                    build_config["preview_table"]["value"] = []
                    return build_config

                # Create a sample DataFrame with the field mappings structure
                sample_data = {}
                for mapping in field_mappings:
                    source_field = mapping.get("source_field", "")
                    if source_field:
                        # Generate sample data based on field name heuristics
                        if "id" in source_field.lower():
                            sample_data[source_field] = f"sample_{hash(source_field) % 1000:03d}"
                        elif "name" in source_field.lower():
                            sample_data[source_field] = f"Sample {source_field.title()}"
                        elif "email" in source_field.lower():
                            sample_data[source_field] = f"sample_{source_field}@example.com"
                        elif "phone" in source_field.lower():
                            sample_data[source_field] = "13800138000"
                        elif "date" in source_field.lower() or "time" in source_field.lower():
                            sample_data[source_field] = "2024-01-01 12:00:00"
                        elif "amount" in source_field.lower() or "price" in source_field.lower():
                            sample_data[source_field] = f"{(hash(source_field) % 10000) / 100:.2f}"
                        elif "count" in source_field.lower() or "num" in source_field.lower():
                            sample_data[source_field] = hash(source_field) % 100
                        else:
                            sample_data[source_field] = f"Sample {source_field}"

                # Create DataFrame from sample data
                df = pd.DataFrame([sample_data])

                # Apply field mappings if configured
                if field_mappings:
                    df = self._apply_field_mappings_preview(df, field_mappings)
                    logger.info(
                        f"[TableOutput] Applied field mappings to preview, result: {len(df)} rows, {len(df.columns)} columns"
                    )

                logger.info(f"[TableOutput] Generated sample preview with {len(df.columns)} columns")

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

                logger.info(f"[TableOutput] Sample preview completed, showing {len(preview_data)} rows")
                self.status = i18n.t(
                    "components.input_output.table_output.status.preview_success", count=len(preview_data)
                )

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                logger.error(f"[TableOutput] Preview generation failed: {error_msg}")
                import traceback

                logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t("components.input_output.table_output.errors.preview_failed", error=error_msg)

        logger.debug(f"[TableOutput] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _load_public_datasource_tables(self, datasource_info: dict) -> list[str]:
        """为公共数据源加载表列表，直接通过连接信息查询数据库"""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.pool import NullPool

        try:
            # 从datasource_info获取raw_data
            raw_data = datasource_info.get("raw_data", datasource_info)

            # 构建连接字符串
            connection_string = self._build_public_connection_string(raw_data)
            logger.debug("[TableOutput] Loading tables for public datasource with connection string")

            # 获取数据源类型
            params = raw_data.get("dataSourceParam", {})
            ds_type = params.get("type") if isinstance(params, dict) else None
            if not ds_type:
                ds_type = raw_data.get("type") or raw_data.get("dataSourceType") or raw_data.get("dbType") or "mysql"
            ds_type = ds_type.lower()
            logger.debug(f"[TableOutput] Public datasource type: {ds_type}")

            # Neo4j特殊处理：使用neo4j驱动而不是SQLAlchemy
            if ds_type == "neo4j":
                return self._load_neo4j_labels(raw_data)

            # MongoDB特殊处理：使用pymongo驱动而不是SQLAlchemy
            if ds_type == "mongodb":
                return self._load_mongodb_collections(raw_data)

            # ClickHouse特殊处理：使用clickhouse-connect驱动而不是SQLAlchemy
            if ds_type == "clickhouse":
                return self._load_clickhouse_tables(raw_data)

            # 其他数据库使用SQLAlchemy
            engine = create_engine(connection_string, poolclass=NullPool)

            with engine.connect() as conn:
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                logger.info(f"[TableOutput] Loaded {len(tables)} tables from public datasource")
                return tables

        except Exception as e:
            logger.error(f"[TableOutput] Failed to load tables from public datasource: {e}")
            import traceback

            logger.error(f"[TableOutput] Traceback: {traceback.format_exc()}")
            raise
        finally:
            if "engine" in locals():
                engine.dispose()

    def _load_neo4j_labels(self, raw_data: dict) -> list[str]:
        """为Neo4j公共数据源加载节点标签列表"""
        from neo4j import GraphDatabase

        try:
            params = raw_data.get("dataSourceParam", {})

            # 优先使用URL中的连接信息
            url = params.get("url", "")
            if url and url.startswith("bolt://"):
                uri = url
            else:
                host = params.get("host", "localhost")
                port = params.get("port", 7687)
                uri = f"bolt://{host}:{port}"

            username = params.get("username", "neo4j")
            password = params.get("password", "")
            database = params.get("database", "neo4j")

            logger.debug(f"[TableOutput] Connecting to Neo4j at {uri}, database: {database}")

            driver = GraphDatabase.driver(uri, auth=(username, password))

            with driver.session(database=database) as session:
                result = session.run("CALL db.labels()")
                labels = [record["label"] for record in result]
                logger.info(f"[TableOutput] Loaded {len(labels)} labels from Neo4j: {labels}")
                return labels

        except Exception as e:
            logger.error(f"[TableOutput] Failed to load Neo4j labels: {e}")
            raise
        finally:
            if "driver" in locals():
                driver.close()

    def _load_public_datasource_columns(self, datasource_info: dict, table_name: str) -> list[dict]:
        """为公共数据源加载表的列信息，直接通过连接信息查询数据库"""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.pool import NullPool

        raw_data = datasource_info.get("raw_data", datasource_info)
        connection_string = self._build_public_connection_string(raw_data)

        # Get datasource type
        params = raw_data.get("dataSourceParam", {})
        ds_type = params.get("type") if isinstance(params, dict) else None
        if not ds_type:
            ds_type = raw_data.get("type") or "mysql"
        ds_type = ds_type.lower()

        # Neo4j special handling - return property keys from sample nodes
        if ds_type == "neo4j":
            return self._load_neo4j_columns(raw_data, table_name)

        # MongoDB special handling - return field names from sample documents
        if ds_type == "mongodb":
            return self._load_mongodb_columns(raw_data, table_name)

        # ClickHouse special handling - use clickhouse-connect
        if ds_type == "clickhouse":
            return self._load_clickhouse_columns(raw_data, table_name)

        # Other databases use SQLAlchemy
        engine = create_engine(connection_string, poolclass=NullPool)
        try:
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            # Convert to format expected by frontend: [{"name": "col1", "type": "varchar"}, ...]
            return [{"name": col["name"], "type": str(col["type"])} for col in columns]
        finally:
            engine.dispose()

    def _load_neo4j_columns(self, raw_data: dict, label: str) -> list[dict]:
        """为Neo4j公共数据源加载节点属性列表"""
        from neo4j import GraphDatabase

        params = raw_data.get("dataSourceParam", {})
        url = params.get("url", "")
        if url and url.startswith("bolt://"):
            uri = url
        else:
            host = params.get("host", "localhost")
            port = params.get("port", 7687)
            uri = f"bolt://{host}:{port}"

        username = params.get("username", "neo4j")
        password = params.get("password", "")
        database = params.get("database", "neo4j")

        driver = GraphDatabase.driver(uri, auth=(username, password))
        try:
            with driver.session(database=database) as session:
                # Get all property keys for nodes with this label
                query = f"""
                MATCH (n:{label})
                UNWIND keys(n) AS key
                RETURN DISTINCT key AS name, 'string' AS type
                LIMIT 100
                """
                result = session.run(query)
                columns = [{"name": record["name"], "type": record["type"]} for record in result]
                logger.info(f"[TableOutput] Loaded {len(columns)} properties for Neo4j label '{label}'")
                return columns
        finally:
            driver.close()

    def _load_mongodb_collections(self, raw_data: dict) -> list[str]:
        """为MongoDB公共数据源加载集合列表"""
        from pymongo import MongoClient

        try:
            params = raw_data.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 27017)
            database = params.get("database", "admin")
            username = params.get("username", "")
            password = params.get("password", "")

            # Build MongoDB connection parameters
            mongo_params = {
                "host": host,
                "port": port,
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 20000,
            }

            if username and password:
                mongo_params["username"] = username
                mongo_params["password"] = password

            # Create MongoDB client
            client = MongoClient(**mongo_params)

            try:
                db = client[database]
                collections = db.list_collection_names()
                logger.info(f"[TableOutput] Loaded {len(collections)} collections from MongoDB")
                return sorted(collections)
            finally:
                client.close()

        except Exception as e:
            logger.error(f"[TableOutput] Failed to load MongoDB collections: {e}")
            raise

    def _load_mongodb_columns(self, raw_data: dict, collection_name: str) -> list[dict]:
        """为MongoDB公共数据源加载集合的字段列表（从样本文档推断）"""
        from pymongo import MongoClient

        params = raw_data.get("dataSourceParam", {})
        host = params.get("host", "localhost")
        port = params.get("port", 27017)
        database = params.get("database", "admin")
        username = params.get("username", "")
        password = params.get("password", "")

        # Build MongoDB connection parameters
        mongo_params = {
            "host": host,
            "port": port,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 20000,
        }

        if username and password:
            mongo_params["username"] = username
            mongo_params["password"] = password

        # Create MongoDB client
        client = MongoClient(**mongo_params)

        try:
            db = client[database]
            collection = db[collection_name]

            # Get sample documents to infer schema
            sample_docs = list(collection.find().limit(100))

            # Extract all unique field names
            fields = set()
            for doc in sample_docs:
                fields.update(doc.keys())

            # Convert to expected format
            columns = [{"name": field, "type": "string"} for field in sorted(fields)]
            logger.info(f"[TableOutput] Inferred {len(columns)} fields from MongoDB collection '{collection_name}'")
            return columns
        finally:
            client.close()

    def _load_clickhouse_tables(self, raw_data: dict) -> list[str]:
        """为ClickHouse公共数据源加载表列表"""
        import clickhouse_connect

        try:
            params = raw_data.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 8123)
            database = params.get("database", "default")
            username = params.get("username", "default")
            password = params.get("password", "")

            # Create ClickHouse client
            client = clickhouse_connect.get_client(
                host=host, port=port, username=username, password=password, database=database
            )

            try:
                # Get table list
                result = client.query("SHOW TABLES")
                tables = [row[0] for row in result.result_rows]
                logger.info(f"[TableOutput] Loaded {len(tables)} tables from ClickHouse")
                return sorted(tables)
            finally:
                client.close()

        except Exception as e:
            logger.error(f"[TableOutput] Failed to load ClickHouse tables: {e}")
            raise

    def _load_clickhouse_columns(self, raw_data: dict, table_name: str) -> list[dict]:
        """为ClickHouse公共数据源加载表的列信息"""
        import clickhouse_connect

        params = raw_data.get("dataSourceParam", {})
        host = params.get("host", "localhost")
        port = params.get("port", 8123)
        database = params.get("database", "default")
        username = params.get("username", "default")
        password = params.get("password", "")

        # Create ClickHouse client
        client = clickhouse_connect.get_client(
            host=host, port=port, username=username, password=password, database=database
        )

        try:
            # Get column information
            result = client.query(f"DESCRIBE TABLE {table_name}")
            columns = [{"name": row[0], "type": row[1]} for row in result.result_rows]
            logger.info(f"[TableOutput] Loaded {len(columns)} columns from ClickHouse table '{table_name}'")
            return columns
        finally:
            client.close()

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

    def _get_datasource_id_from_metadata(self, selector_value: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据选择器值获取数据源ID

        Args:
            selector_value: 选择器的值，现在直接就是数据源ID
            options_metadata: 元数据列表

        Returns:
            数据源ID，如果未找到则返回None
        """
        # 现在 selector_value 直接就是ID，直接返回
        # 但我们先验证它确实存在于 metadata 中
        for metadata in options_metadata:
            if metadata.get("id") == selector_value or metadata.get("value") == selector_value:
                logger.debug(f"[TableOutput] Found valid datasource ID: '{selector_value}'")
                return selector_value

        # 向后兼容：尝试从旧的 "ID|||显示名称" 格式中提取ID
        if "|||" in selector_value:
            datasource_id = selector_value.split("|||")[0]
            logger.warning(f"[TableOutput] Legacy format detected, extracted ID '{datasource_id}' from selector value")
            return datasource_id

        # 再向后兼容：按显示名称查找
        logger.warning(f"[TableOutput] Trying legacy lookup by display name for: '{selector_value}'")
        for metadata in options_metadata:
            if metadata.get("display_name") == selector_value:
                datasource_id = metadata.get("id")
                logger.debug(f"[TableOutput] Found datasource ID '{datasource_id}' for display name '{selector_value}'")
                return datasource_id

        logger.warning(f"[TableOutput] No metadata found for selector value: '{selector_value}'")
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
                # 使用线程池执行器运行异步方法
                try:
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_public_datasources())
                        public_datasources = future.result(timeout=10)
                except Exception:
                    # 如果异步方法失败，回退到空列表
                    logger.debug("[TableOutput] Async method failed, falling back to empty public datasource list")
                    public_datasources = []

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

            # 添加内置数据源 - 不包含 connection_string，通过 API 动态获取
            for ds in builtin_datasources:
                display_name = f"{ds['name']} ({ds['type']}) [自定义]"
                all_datasources.append(
                    {
                        "id": str(ds["id"]),
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "builtin",
                        "display_name": display_name,
                        # ❌ 移除预构建的 connection_string，改为通过 API 动态获取
                    }
                )

            # 添加公共数据源
            for ds in public_datasources:
                # ✅ 修复：从 dataSourceParam.type 获取正确的类型
                params = ds.get("dataSourceParam", {})
                ds_type = params.get("type") if isinstance(params, dict) else None
                if not ds_type:
                    ds_type = ds.get("type") or ds.get("dataSourceType") or ds.get("dbType") or "mysql"

                display_name = self._build_display_name(ds, "public")
                all_datasources.append(
                    {
                        "id": str(ds["id"]),
                        "name": ds["name"],
                        "type": ds_type,  # ✅ 使用从 dataSourceParam 获取的正确类型
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
        """获取内置数据源 - 直接从数据库读取，包含完整连接信息"""
        try:
            # 直接从数据库读取数据源，避免API调用导致的死锁
            import concurrent.futures

            from langflow.services.database.models.datasource import DataSource
            from langflow.services.deps import session_scope
            from sqlmodel import select

            async def fetch_datasources():
                """异步获取数据源列表"""
                try:
                    async with session_scope() as session:
                        statement = select(DataSource)
                        result = await session.exec(statement)
                        datasources = result.all()

                        logger.debug(f"[TableOutput] Fetched {len(datasources)} datasources from database")

                        builtin_list = []
                        for ds in datasources:
                            # 构建包含所有连接参数的字典（包括密码）
                            ds_dict = {
                                "id": str(ds.id),
                                "name": ds.name,
                                "type": ds.type.lower(),
                                "host": ds.host,
                                "port": ds.port,
                                "database": ds.database,
                                "username": ds.username,
                                "password": ds.password,  # 包含密码用于构建连接字符串
                                "source": "builtin",
                                "advanced_config": ds.advanced_config,
                            }
                            builtin_list.append(ds_dict)

                        return builtin_list
                except Exception as e:
                    logger.error(f"[TableOutput] Error fetching datasources from database: {e}")
                    return []

            # 执行异步操作
            try:
                loop = asyncio.get_running_loop()
                # 在事件循环中，使用ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch_datasources())
                    builtin_datasources = future.result(timeout=10)
            except RuntimeError:
                # 没有运行中的事件循环，直接使用asyncio.run
                builtin_datasources = asyncio.run(fetch_datasources())

            logger.debug(f"[TableOutput] Got {len(builtin_datasources)} builtin datasources from database")
            return builtin_datasources

        except Exception as e:
            logger.error(f"[TableOutput] Error getting builtin datasources: {e}")
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

            # 直接调用异步方法，不使用 asyncio.run
            datasource_list = await client.get_datasource_list()

            logger.info(f"[TableOutput] Got {len(datasource_list)} public datasources from feign API")
            logger.debug(
                f"[TableOutput] Public datasource sample: {datasource_list[:1] if datasource_list else 'None'}"
            )
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[TableOutput] Failed to get public datasources: {e}")
            import traceback

            logger.error(f"[TableOutput] Feign client error traceback: {traceback.format_exc()}")
            return []

    def _get_datasource_type_for_display(self, datasource: dict, source: str) -> dict:
        """获取用于显示的数据源类型和数据库信息"""
        if source == "public":
            # 公共数据源：从dataSourceParam获取信息
            raw_data = datasource.get("raw_data", datasource)
            params = raw_data.get("dataSourceParam", {})

            # ✅ 优先从 dataSourceParam.type 获取类型
            ds_type = params.get("type") if isinstance(params, dict) else None
            if not ds_type:
                ds_type = raw_data.get("type", "mysql")

            # 获取数据库和连接信息
            database = params.get("database", "default")
            host = params.get("host", "localhost")
            port = params.get("port", self._get_default_port(ds_type))

        else:
            # 内置数据源：使用现有逻辑
            ds_type = datasource.get("type", "mysql")
            database = datasource.get("database", "default")
            host = datasource.get("host", "localhost")
            port = datasource.get("port", self._get_default_port(ds_type))

        return {"type": ds_type.lower(), "database": database, "host": host, "port": port}

    def _get_default_port(self, ds_type: str) -> int:
        """获取数据源的默认端口"""
        default_ports = {
            "mysql": 3306,
            "postgresql": 5432,
            "hive": 10000,
            "neo4j": 7687,
            "oracle": 1521,
            "sqlserver": 1433,
        }
        return default_ports.get(ds_type.lower(), 3306)

    def _build_display_name(self, datasource: dict, source: str) -> str:
        """构建丰富的显示名称 - 恢复原来的格式，信息在 option_metadata 中处理"""
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
        # 调试日志：检查 datasource_info 内容
        logger.info(f"[TableOutput] _get_connection_string called for datasource_id={datasource_id}")
        if datasource_info:
            logger.info(f"[TableOutput] datasource_info keys: {list(datasource_info.keys())}")
            logger.info(
                f"[TableOutput] datasource_info values: name={datasource_info.get('name')}, "
                f"type={datasource_info.get('type')}, host={datasource_info.get('host')}, "
                f"port={datasource_info.get('port')}, database={datasource_info.get('database')}, "
                f"source={datasource_info.get('source')}, connection_string={datasource_info.get('connection_string')}"
            )
        else:
            logger.warning("[TableOutput] datasource_info is None!")

        # 优先使用datasource_info中预先构建的connection_string（避免API调用死锁）
        if datasource_info and datasource_info.get("connection_string"):
            logger.debug("[TableOutput] Using pre-built connection string from datasource_info")
            return datasource_info["connection_string"]

        # 公共数据源：从raw_data构建连接字符串
        if datasource_info and datasource_info.get("source") == "public":
            return self._build_public_connection_string(datasource_info["raw_data"])

        # 内置数据源且有完整参数：直接构建连接字符串（避免API调用）
        if datasource_info and datasource_info.get("source") == "builtin":
            required_fields = ["host", "port", "database", "type"]
            missing_fields = [field for field in required_fields if datasource_info.get(field) is None]
            if missing_fields:
                logger.error(
                    f"[TableOutput] Missing required fields in datasource_info: {missing_fields}, "
                    f"available fields: {datasource_info}"
                )
            else:
                logger.debug("[TableOutput] Building connection string from datasource_info parameters")
                return self._build_connection_string_from_params(datasource_info["type"], datasource_info)

        # 后备方案：使用API调用（可能导致死锁，应避免）
        logger.warning(
            f"[TableOutput] Falling back to API call for connection string (datasource_id={datasource_id}, "
            f"reason: connection_string is None or missing required fields)"
        )
        return self._get_builtin_connection_string(datasource_id)

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        # 获取数据源参数
        params = raw_data.get("dataSourceParam", {})
        if not params:
            logger.warning("[TableOutput] No dataSourceParam found in raw_data")
            params = {}

        # ✅ 修复：优先从 dataSourceParam.type 获取类型（公共数据源的实际位置）
        ds_type = params.get("type") if isinstance(params, dict) else None

        # 如果 dataSourceParam.type 为空，再尝试其他字段（向后兼容）
        if not ds_type:
            ds_type = raw_data.get("type", "mysql")

        ds_type = ds_type.lower()
        logger.debug(f"[TableOutput] Using datasource type: {ds_type}")

        if ds_type == "hive":
            # Hive连接字符串构建 - 使用 SQLAlchemy 格式，不是 JDBC 格式
            from urllib.parse import quote_plus

            host = params.get("host", "localhost")
            port = params.get("port", 10000)
            database = params.get("database", "default")
            username = params.get("username", "hive")
            password = params.get("password", "")

            # ✅ 修复：使用 SQLAlchemy + PyHive 格式：hive://[user[:password]@]host:port/database
            # 不再使用 JDBC 格式 jdbc:hive2://
            username_encoded = quote_plus(username) if username else ""
            password_encoded = quote_plus(password) if password else ""

            if username and password:
                conn_str = f"hive://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
            elif username:
                conn_str = f"hive://{username_encoded}@{host}:{port}/{database}"
            else:
                conn_str = f"hive://{host}:{port}/{database}"

            logger.debug(
                f"[TableOutput] Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}"
            )
            return conn_str

        # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
        return self._build_connection_string_from_params(ds_type, params)

    def _build_connection_string_from_params(self, ds_type: str, params: dict) -> str:
        """从参数构建连接字符串 - Support MySQL, PostgreSQL, Hive, Neo4j, MongoDB, ClickHouse, Doris"""
        from urllib.parse import quote_plus, unquote

        host = params.get("host", "localhost")
        port = params.get("port", 3306)
        database = params.get("database", "")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if ds_type == "mysql":
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "postgresql":
            return f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "hive":
            # Hive connection - 与table_input保持一致的格式
            # 完全由数据源决定端口，不使用默认值
            hive_database = database or "default"

            conn_str = f"hive://{host}"
            if port:
                conn_str += f":{port}"
            conn_str += f"/{hive_database}"

            if username:
                conn_str += f"?auth={username}"
                if password:
                    # 使用unquote解密密码，与table_input保持一致
                    password_decoded = unquote(password)
                    conn_str += f"&pwd={password_decoded}"

            logger.info(f"[TableOutput] Built Hive connection: {conn_str}")
            return conn_str
        if ds_type == "neo4j":
            # Neo4j connection - 使用 bolt:// 协议，不是 neo4j://
            # 优先使用URL中的连接信息
            url = params.get("url", "")
            if url and url.startswith("bolt://"):
                import re

                match = re.match(r"bolt://([^:]+):(\d+)", url)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))
            else:
                # 回退到使用host和port参数
                neo4j_port = port if port != 3306 else 7687
                port = neo4j_port

            if username and password:
                return f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
            return f"bolt://{host}:{port}"
        if ds_type == "mongodb":
            # MongoDB connection string
            mongo_port = port if port != 3306 else 27017
            if username and password:
                return f"mongodb://{username_encoded}:{password_encoded}@{host}:{mongo_port}/{database}"
            return f"mongodb://{host}:{mongo_port}/{database}"
        if ds_type == "clickhouse":
            # ClickHouse connection using clickhouse-connect driver
            ch_port = port if port != 3306 else 8123
            return f"clickhouse+connect://{username_encoded}:{password_encoded}@{host}:{ch_port}/{database}"
        if ds_type == "doris":
            # Doris connection using MySQL protocol (compatible with MySQL driver)
            doris_port = port if port != 3306 else 9030
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{doris_port}/{database}"
        raise ValueError(f"Unsupported database type: {ds_type}")

    def _get_builtin_connection_string(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            # 提取纯UUID（移除可能的前缀）
            clean_datasource_id = self._extract_uuid_from_id(datasource_id)
            logger.debug(
                f"[TableOutput] Getting connection string for datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
            )

            with httpx.Client(timeout=120.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{clean_datasource_id}/connection-string")

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
        # 公共数据源：从raw_data构建连接字符串
        if datasource_info and datasource_info.get("source") == "public":
            logger.info("[TableOutput] Building connection string for public datasource")
            return self._build_public_connection_string(datasource_info["raw_data"])

        # 内置数据源：通过 API 调用获取连接字符串（包含最新密码）
        if datasource_info and datasource_info.get("source") == "builtin":
            logger.info(
                f"[TableOutput] Getting connection string from API for builtin datasource (datasource_id={datasource_id})"
            )
            return self._get_builtin_connection_string_sync(datasource_id)

        # 后备方案：通过 API 获取
        logger.warning(f"[TableOutput] Falling back to API call for connection string (datasource_id={datasource_id})")
        return self._get_builtin_connection_string_sync(datasource_id)

    def _get_builtin_connection_string_sync(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串（同步版本）"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            # 提取纯UUID（移除可能的前缀）
            clean_datasource_id = self._extract_uuid_from_id(datasource_id)
            logger.debug(
                f"[TableOutput] Getting connection string (sync) for datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
            )

            with httpx.Client(timeout=120.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{clean_datasource_id}/connection-string")

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
        """从选中的ID或显示名称获取实际的数据源ID（支持内置和公共数据源）"""
        if not self.datasource_selector:
            raise ValueError(i18n.t("components.input_output.table_output.errors.no_datasource_selected"))

        try:
            # 加载统一的数据源列表
            all_datasources = self._load_unified_datasources()

            logger.info(f"[TableOutput] Looking for datasource: '{self.datasource_selector}'")

            # 构建数据源列表摘要（避免f-string中使用反斜杠）
            ds_summary = [f"{ds['name']} (id={ds['id'][:8]}...)" for ds in all_datasources[:5]]
            more_indicator = " ..." if len(all_datasources) > 5 else ""
            logger.info(f"[TableOutput] Available datasources ({len(all_datasources)}): {ds_summary}{more_indicator}")

            # 策略1: 优先按ID匹配（前端通常传ID）
            for ds in all_datasources:
                if ds["id"] == self.datasource_selector:
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
                        # ✅ 移除预构建的连接字符串和参数，改为通过 API 动态获取
                    }

                    logger.info(
                        f"[TableOutput] ✅ Matched by ID: '{datasource_id}' "
                        f"({source}) type='{ds['type']}' name='{ds['name']}'"
                    )
                    return datasource_id

            # 策略2: 按display_name匹配（向后兼容）
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
                        # ✅ 移除预构建的连接字符串和参数，改为通过 API 动态获取
                    }

                    logger.info(
                        f"[TableOutput] ✅ Matched by display_name: '{ds['display_name']}' "
                        f"(id={datasource_id}) type='{ds['type']}'"
                    )
                    return datasource_id

            # 策略3: 都没找到，向后兼容（假设直接是ID，type=None）
            logger.warning("[TableOutput] ⚠️  Not found in datasource list, using as direct ID (type will be unknown)")

            # 在向后兼容模式下，我们无法确定类型，设置为None
            self._current_datasource_info = {
                "id": self.datasource_selector,
                "name": self.datasource_selector,
                "type": None,  # Unknown type in backward compatibility mode
                "source": "unknown",
                "display_name": self.datasource_selector,
                "raw_data": None,
            }

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

            # 2. Get datasource ID and connection string
            datasource_id = self._get_datasource_id()
            logger.debug(f"[TableOutput] Using datasource ID: {datasource_id}")

            # Get datasource info (set by _get_datasource_id)
            datasource_info = getattr(self, "_current_datasource_info", None)
            logger.debug(f"[TableOutput] datasource_info from _get_datasource_id: {datasource_info}")

            # Check if this is Neo4j (case-insensitive)
            datasource_type = datasource_info.get("type", "") if datasource_info else ""
            logger.debug(
                f"[TableOutput] Extracted datasource_type: '{datasource_type}' (type: {type(datasource_type)})"
            )
            is_neo4j = (
                datasource_type.strip().lower() == "neo4j" if datasource_type and datasource_type.strip() else False
            )
            logger.info(
                f"[TableOutput] Datasource type check - type: '{datasource_type}', "
                f"is_neo4j: {is_neo4j}, datasource_info keys: {list(datasource_info.keys()) if datasource_info else 'None'}"
            )

            # Neo4j doesn't require table_selector (uses node labels), other databases need validation
            if not is_neo4j and not self.table_selector:
                error_msg = i18n.t("components.input_output.table_output.errors.no_table")
                self.status = error_msg
                raise ValueError(error_msg)

            # Get connection string (supports both builtin and public datasources)
            connection_string = self._get_connection_string_sync(datasource_id, datasource_info)

            # 3. Convert data to DataFrame
            data_records = []
            logger.debug(f"[TableOutput] Processing data_input with {len(self.data_input)} items")
            logger.debug(f"[TableOutput] data_input type: {type(self.data_input)}")

            # Ensure data_input is a list
            if not isinstance(self.data_input, list):
                data_input_list = [self.data_input]
                logger.debug("[TableOutput] Wrapped single data_input into list")
            else:
                data_input_list = self.data_input

            for i, d in enumerate(data_input_list):
                logger.debug(f"[TableOutput] Processing item {i}: type={type(d)}")

                # Try to extract the actual data
                if isinstance(d, tuple):
                    # Handle tuple data from streaming - recursively process tuple contents
                    logger.debug(f"[TableOutput] Processing tuple with {len(d)} items")
                    for j, item in enumerate(d):
                        logger.debug(f"[TableOutput] Tuple item {j}: type={type(item)}")
                        if hasattr(item, "data") and isinstance(item.data, dict):
                            data_records.append(item.data)
                            logger.debug(f"[TableOutput] Added Data object from tuple with {len(item.data)} fields")
                        elif isinstance(item, dict):
                            data_records.append(item)
                            logger.debug(f"[TableOutput] Added dict from tuple with {len(item)} fields")
                        else:
                            logger.warning(f"[TableOutput] Skipping unexpected tuple item type: {type(item)}")
                elif hasattr(d, "data") and isinstance(d.data, dict):
                    data_records.append(d.data)
                    logger.debug(f"[TableOutput] Added Data object with {len(d.data)} fields")
                elif isinstance(d, dict):
                    data_records.append(d)
                    logger.debug(f"[TableOutput] Added dict with {len(d)} fields")
                else:
                    logger.warning(f"[TableOutput] Unexpected data type: {type(d)}")

            logger.info(
                f"[TableOutput] Extracted {len(data_records)} data records from {len(data_input_list)} input items"
            )
            logger.debug(f"[TableOutput] data_records sample: {data_records[:2] if data_records else 'empty'}")

            if not data_records:
                error_msg = i18n.t("components.input_output.table_output.errors.empty_dataframe")
                self.status = error_msg
                raise ValueError(error_msg)

            # Create DataFrame with explicit error handling
            try:
                df = pd.DataFrame(data_records)
                logger.debug(
                    f"[TableOutput] Created DataFrame with type: {type(df)}, isinstance check: {isinstance(df, pd.DataFrame)}"
                )

                # Verify it's actually a DataFrame
                if not isinstance(df, pd.DataFrame):
                    logger.error(f"[TableOutput] ERROR: pd.DataFrame() returned {type(df)} instead of DataFrame!")
                    logger.error(f"[TableOutput] data_records type: {type(data_records)}, len: {len(data_records)}")
                    logger.error(f"[TableOutput] First record: {data_records[0] if data_records else 'N/A'}")
                    raise ValueError(f"pd.DataFrame() returned {type(df)} instead of DataFrame")

                logger.debug(f"[TableOutput] DataFrame shape: {df.shape}, columns: {list(df.columns)}")
            except Exception as e:
                logger.error(f"[TableOutput] Failed to create DataFrame: {e}")
                logger.error(f"[TableOutput] data_records: {data_records}")
                raise ValueError(f"Failed to create DataFrame: {e}") from e

            if df.empty:
                error_msg = i18n.t("components.input_output.table_output.errors.empty_dataframe")
                self.status = error_msg
                raise ValueError(error_msg)

            logger.info(f"[TableOutput] Processing {len(df)} rows to table '{self.table_selector}'")

            # 4. Apply field mappings if configured
            if self.field_mappings:
                df = self._apply_field_mappings(df)

            # 5. 检测数据源类型并路由到相应的写入方法
            # 使用之前已经检查过的数据源类型变量（在步骤2中已经设置）
            db_type = datasource_type.strip().lower() if datasource_type and datasource_type.strip() else ""

            is_neo4j = db_type == "neo4j"
            is_hive = db_type == "hive"
            is_clickhouse = db_type == "clickhouse"
            is_doris = db_type == "doris"
            is_mongodb = db_type == "mongodb"

            if is_neo4j:
                # 使用Neo4j驱动写入
                logger.info("[TableOutput] Detected Neo4j datasource, using Neo4j driver")
                rows_written = self._write_to_neo4j(connection_string, df)

                # Build result
                result_info = {
                    "success": True,
                    "table": self.table_selector,
                    "rows_written": rows_written,
                    "write_mode": self.write_mode,
                    "datasource": self.datasource_selector,
                }

                success_msg = _format_i18n(
                    "components.input_output.table_output.status.success",
                    rows=rows_written,
                    table=self.table_selector,
                )
                self.status = success_msg
                logger.info(f"[TableOutput] {success_msg}")

                # 缓存结果供get_row_count使用，避免重复写入
                result_data = Data(data=result_info)
                self._last_write_result = result_data
                return result_data
            if is_hive:
                # 使用Hive专用写入方法
                logger.info("[TableOutput] Detected Hive datasource, using Hive-specific write method")
                rows_written = self._write_to_hive(connection_string, df)

                # Build result
                result_info = {
                    "success": True,
                    "table": self.table_selector,
                    "rows_written": rows_written,
                    "write_mode": self.write_mode,
                    "datasource": self.datasource_selector,
                }

                success_msg = _format_i18n(
                    "components.input_output.table_output.status.success",
                    rows=rows_written,
                    table=self.table_selector,
                )
                self.status = success_msg
                logger.info(f"[TableOutput] {success_msg}")

                # 缓存结果供get_row_count使用，避免重复写入
                result_data = Data(data=result_info)
                self._last_write_result = result_data
                return result_data

            if is_clickhouse:
                # 使用ClickHouse原生驱动写入
                logger.info("[TableOutput] Detected ClickHouse datasource, using ClickHouse native driver")
                rows_written = self._write_to_clickhouse(connection_string, df)

                # Build result
                result_info = {
                    "success": True,
                    "table": self.table_selector,
                    "rows_written": rows_written,
                    "write_mode": self.write_mode,
                    "datasource": self.datasource_selector,
                }

                success_msg = _format_i18n(
                    "components.input_output.table_output.status.success",
                    rows=rows_written,
                    table=self.table_selector,
                )
                self.status = success_msg
                logger.info(f"[TableOutput] {success_msg}")

                result_data = Data(data=result_info)
                self._last_write_result = result_data
                return result_data

            if is_doris:
                # 使用Doris (pymysql) 写入
                logger.info("[TableOutput] Detected Doris datasource, using pymysql driver")
                rows_written = self._write_to_doris(connection_string, df)

                # Build result
                result_info = {
                    "success": True,
                    "table": self.table_selector,
                    "rows_written": rows_written,
                    "write_mode": self.write_mode,
                    "datasource": self.datasource_selector,
                }

                success_msg = _format_i18n(
                    "components.input_output.table_output.status.success",
                    rows=rows_written,
                    table=self.table_selector,
                )
                self.status = success_msg
                logger.info(f"[TableOutput] {success_msg}")

                result_data = Data(data=result_info)
                self._last_write_result = result_data
                return result_data

            if is_mongodb:
                # 使用MongoDB原生驱动写入
                logger.info("[TableOutput] Detected MongoDB datasource, using pymongo driver")
                rows_written = self._write_to_mongodb(connection_string, df)

                # Build result
                result_info = {
                    "success": True,
                    "table": self.table_selector,
                    "rows_written": rows_written,
                    "write_mode": self.write_mode,
                    "datasource": self.datasource_selector,
                }

                success_msg = _format_i18n(
                    "components.input_output.table_output.status.success",
                    rows=rows_written,
                    table=self.table_selector,
                )
                self.status = success_msg
                logger.info(f"[TableOutput] {success_msg}")

                result_data = Data(data=result_info)
                self._last_write_result = result_data
                return result_data

            # 原有的SQLAlchemy逻辑 (MySQL, PostgreSQL等)
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

            # 缓存结果供get_row_count使用，避免重复写入
            result_data = Data(data=result_info)
            self._last_write_result = result_data
            return result_data

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
            where_clause = " AND ".join([f"{col!s} = :{col}" for col in key_fields])

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
                            update_fields.append(f"{col!s} = {col!s} + :{col}")
                            update_params[col] = row_dict.get(col, 0)
                            continue

                        # Default: sync_update
                        update_fields.append(f"{col!s} = :{col}")
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
                cols = ", ".join([str(col) for col in df.columns])
                placeholders = ", ".join([f":{col}" for col in df.columns])
                insert_query = f"INSERT INTO {self.table_selector} ({cols}) VALUES ({placeholders})"

                connection.execute(text(insert_query), row_dict)
                rows_written += 1

        connection.commit()
        logger.debug(f"[TableOutput] Upsert completed: {rows_written} rows affected")

        return rows_written

    def _extract_key_fields_from_mappings(self) -> list[str]:
        """从字段映射中提取标记为关键字段的字段名。

        Returns:
            list[str]: 关键字段名列表
        """
        key_fields = []

        if not self.field_mappings:
            return key_fields

        for mapping in self.field_mappings:
            if mapping.get("is_key_field", False):
                target_field = mapping.get("target_field")
                if target_field:
                    key_fields.append(target_field)

        logger.info(f"[TableOutput] Extracted key fields from mappings: {key_fields}")
        return key_fields

    def _sanitize_label(self, label: str) -> str:
        """清理标签名称，确保符合Neo4j命名规范。

        Neo4j标签规则：
        - 只能包含字母、数字、下划线
        - 不能以数字开头
        - 不能使用保留关键字

        Args:
            label: 原始标签名

        Returns:
            str: 清理后的合法标签名
        """
        import re

        # 移除特殊字符，替换为下划线
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", label)

        # 如果以数字开头，添加前缀
        if sanitized and sanitized[0].isdigit():
            sanitized = f"T_{sanitized}"

        # 如果为空，使用默认
        if not sanitized:
            sanitized = "TableData"

        logger.debug(f"[TableOutput] Sanitized label: '{label}' -> '{sanitized}'")
        return sanitized

    def _write_to_neo4j(self, connection_string: str, df: pd.DataFrame) -> int:
        """写入数据到Neo4j数据库"""
        import uuid

        from neo4j import GraphDatabase

        # 解析连接字符串
        match = re.match(r"bolt://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", connection_string)
        if not match:
            raise ValueError(f"Invalid Neo4j connection string: {connection_string}")

        username, password, host, port = match.groups()
        if username:
            username = unquote(username)
        if password:
            password = unquote(password)

        uri = f"bolt://{host}:{port}"
        driver = GraphDatabase.driver(uri, auth=(username, password) if username else None)

        try:
            # 1. 确定节点标签
            if self.table_selector:
                label = self._sanitize_label(self.table_selector)
            else:
                label = "TableData"
            logger.info(f"[TableOutput] Using Neo4j label: {label}")

            # 2. 从字段映射中提取关键字段
            key_fields = self._extract_key_fields_from_mappings()

            # 3. 如果使用upsert模式但没有关键字段，自动生成UUID
            df_copy = df.copy()
            if self.write_mode == "upsert" and not key_fields:
                logger.info("[TableOutput] No key fields found for upsert mode, generating UUID")
                df_copy["_uuid"] = [str(uuid.uuid4()) for _ in range(len(df_copy))]
                key_fields = ["_uuid"]

            # 4. 根据write_mode调用对应方法
            if self.write_mode == "batch_insert":
                rows_written = self._neo4j_write_batch_insert(driver, df_copy, label)
            elif self.write_mode == "append":
                rows_written = self._neo4j_write_append(driver, df_copy, label)
            elif self.write_mode == "upsert":
                rows_written = self._neo4j_write_upsert(driver, df_copy, label, key_fields)
            elif self.write_mode == "replace":
                rows_written = self._neo4j_write_replace(driver, df_copy, label)
            else:
                raise ValueError(f"Unsupported write_mode: {self.write_mode}")

            return rows_written
        finally:
            driver.close()

    def _neo4j_write_batch_insert(self, driver, df: pd.DataFrame, label: str) -> int:
        """BATCH_INSERT mode: Fast CREATE without duplicate checking.

        Args:
            driver: Neo4j driver instance
            df: DataFrame containing data to insert
            label: Node label to use

        Returns:
            int: Number of rows written
        """
        query = f"""
        UNWIND $batch AS row
        CREATE (n:{label})
        SET n += row
        RETURN count(n) AS count
        """

        rows_written = 0
        batch_data = df.to_dict("records")

        # 清理None值
        for record in batch_data:
            keys_to_remove = [k for k, v in record.items() if pd.isna(v)]
            for k in keys_to_remove:
                del record[k]

        logger.info(f"[TableOutput] Writing {len(batch_data)} rows in batches of {self.batch_size}")

        with driver.session() as session:
            for i in range(0, len(batch_data), self.batch_size):
                batch = batch_data[i : i + self.batch_size]

                if self.enable_transaction:
                    with session.begin_transaction() as tx:
                        result = tx.run(query, batch=batch)
                        count = result.single()["count"]
                        rows_written += count
                        tx.commit()
                        logger.debug(f"[TableOutput] Batch {i // self.batch_size + 1}: wrote {count} rows")
                else:
                    result = session.run(query, batch=batch)
                    count = result.single()["count"]
                    rows_written += count
                    logger.debug(f"[TableOutput] Batch {i // self.batch_size + 1}: wrote {count} rows")

        logger.info(f"[TableOutput] batch_insert completed: {rows_written} rows created")
        return rows_written

    def _neo4j_write_append(self, driver, df: pd.DataFrame, label: str) -> int:
        """APPEND mode: Simple CREATE (same as batch_insert).

        Args:
            driver: Neo4j driver instance
            df: DataFrame containing data to insert
            label: Node label to use

        Returns:
            int: Number of rows written
        """
        # append和batch_insert行为相同，都是直接CREATE
        logger.info("[TableOutput] append mode - using CREATE")
        return self._neo4j_write_batch_insert(driver, df, label)

    def _neo4j_write_upsert(self, driver, df: pd.DataFrame, label: str, key_fields: list[str]) -> int:
        """UPSERT mode: MERGE based on key fields.

        Args:
            driver: Neo4j driver instance
            df: DataFrame containing data to insert/update
            label: Node label to use
            key_fields: List of field names to use as unique identifiers

        Returns:
            int: Number of rows processed
        """
        if not key_fields:
            error_msg = i18n.t("components.input_output.table_output.errors.no_key_fields_neo4j")
            raise ValueError(error_msg)

        # 构建MERGE匹配条件
        match_props = ", ".join([f"{field}: row.{field}" for field in key_fields])

        query = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{{match_props}}})
        ON CREATE SET n += row, n._created = timestamp()
        ON MATCH SET n += row, n._updated = timestamp()
        RETURN count(n) AS count
        """

        rows_written = 0
        batch_data = df.to_dict("records")

        # 清理None值
        for record in batch_data:
            keys_to_remove = [k for k, v in record.items() if pd.isna(v)]
            for k in keys_to_remove:
                del record[k]

        logger.info(
            f"[TableOutput] Upserting {len(batch_data)} rows with key fields: {key_fields} "
            f"in batches of {self.batch_size}"
        )

        with driver.session() as session:
            for i in range(0, len(batch_data), self.batch_size):
                batch = batch_data[i : i + self.batch_size]

                if self.enable_transaction:
                    with session.begin_transaction() as tx:
                        result = tx.run(query, batch=batch)
                        count = result.single()["count"]
                        rows_written += count
                        tx.commit()
                        logger.debug(f"[TableOutput] Batch {i // self.batch_size + 1}: upserted {count} rows")
                else:
                    result = session.run(query, batch=batch)
                    count = result.single()["count"]
                    rows_written += count
                    logger.debug(f"[TableOutput] Batch {i // self.batch_size + 1}: upserted {count} rows")

        logger.info(f"[TableOutput] upsert completed: {rows_written} rows processed")
        return rows_written

    def _neo4j_write_replace(self, driver, df: pd.DataFrame, label: str) -> int:
        """REPLACE mode: DELETE all nodes with label, then CREATE new.

        Args:
            driver: Neo4j driver instance
            df: DataFrame containing data to insert
            label: Node label to use

        Returns:
            int: Number of rows written
        """
        with driver.session() as session:
            # Step 1: 删除所有同标签节点
            delete_query = f"MATCH (n:{label}) DETACH DELETE n"
            session.run(delete_query)
            logger.info(f"[TableOutput] Deleted all nodes with label :{label}")

        # Step 2: 创建新节点（复用batch_insert逻辑）
        return self._neo4j_write_batch_insert(driver, df, label)

    def _write_to_hive(self, connection_string: str, df: pd.DataFrame) -> int:
        """写入数据到Hive数据库"""
        from pyhive import hive

        try:
            # 解析连接字符串：hive://host:port/database?auth=user&pwd=pass
            import urllib.parse

            parsed = urllib.parse.urlparse(connection_string)

            if parsed.scheme != "hive":
                raise ValueError(f"Invalid Hive connection string scheme: {parsed.scheme}")

            host = parsed.hostname
            port = parsed.port or 10000  # Hive默认端口
            database = parsed.path.lstrip("/") if parsed.path else "default"

            # 解析认证参数
            auth_params = urllib.parse.parse_qs(parsed.query)
            username = auth_params.get("auth", [None])[0]
            password = auth_params.get("pwd", [None])[0]

            logger.info(f"[TableOutput] Connecting to Hive: {host}:{port}/{database}")

            # 建立Hive连接
            connection = hive.Connection(
                host=host,
                port=port,
                username=username if username else "hive",
                database=database,
                password=password,
                auth="CUSTOM" if username else None,
            )

            # 1. 确定表名
            if not self.table_selector:
                error_msg = i18n.t("components.input_output.table_output.errors.no_table")
                raise ValueError(error_msg)
            table_name = self.table_selector
            logger.info(f"[TableOutput] Using Hive table: {table_name}")

            # 2. 根据write_mode调用对应方法
            if self.write_mode == "batch_insert":
                rows_written = self._hive_write_batch_insert(connection, df, table_name)
            elif self.write_mode == "append":
                rows_written = self._hive_write_append(connection, df, table_name)
            elif self.write_mode == "upsert":
                rows_written = self._hive_write_upsert(connection, df, table_name)
            elif self.write_mode == "replace":
                rows_written = self._hive_write_replace(connection, df, table_name)
            else:
                raise ValueError(f"Unsupported write_mode: {self.write_mode}")

            return rows_written

        except Exception as e:
            logger.error(f"[TableOutput] Hive connection error: {e!s}")
            raise
        finally:
            try:
                if "connection" in locals():
                    connection.close()
            except:
                pass

    def _hive_write_batch_insert(self, connection, df: pd.DataFrame, table_name: str) -> int:
        """BATCH_INSERT mode: Fast INSERT without duplicate checking."""
        rows_written = 0

        # 清理DataFrame - 移除包含NaN的行或替换为默认值
        df_clean = df.copy()
        for col in df_clean.columns:
            # 对于数值列，NaN替换为0或适当的默认值
            if df_clean[col].dtype in ["int64", "float64"]:
                df_clean[col] = df_clean[col].fillna(0)
            else:
                # 对于字符串列，NaN替换为空字符串
                df_clean[col] = df_clean[col].fillna("")

        logger.info(f"[TableOutput] Writing {len(df_clean)} rows to Hive table: {table_name}")

        try:
            with connection.cursor() as cursor:
                # 构建列名和占位符
                columns = list(df_clean.columns)
                column_str = ", ".join([f"`{col}`" for col in columns])

                # 准备数据 - 将DataFrame转换为元组列表
                data_tuples = [tuple(row) for row in df_clean.values]

                # 构建INSERT语句 - 使用标准的Hive SQL语法
                # 注意：Hive支持INSERT INTO ... VALUES语法，但需要明确指定列名
                placeholders = ", ".join(["%s"] * len(columns))
                insert_query = f"INSERT INTO TABLE `{table_name}` ({column_str}) VALUES ({placeholders})"

                logger.debug(f"[TableOutput] Hive INSERT query: {insert_query}")

                # Hive不支持事务，使用单独INSERT语句避免executemany的"No result set"错误
                batch_size = min(self.batch_size, 100)  # 减小批量大小以提高稳定性

                for i in range(0, len(data_tuples), batch_size):
                    batch = data_tuples[i : i + batch_size]

                    # 为每行数据单独执行INSERT语句，避免executemany的问题
                    for row_data in batch:
                        cursor.execute(insert_query, row_data)
                        rows_written += 1

                    logger.debug(f"[TableOutput] Batch {i // batch_size + 1}: inserted {len(batch)} rows")

        except Exception as e:
            logger.error(f"[TableOutput] Hive batch insert error: {e!s}")
            raise

        logger.info(f"[TableOutput] Hive batch_insert completed: {rows_written} rows inserted")
        return rows_written

    def _hive_write_append(self, connection, df: pd.DataFrame, table_name: str) -> int:
        """APPEND mode: Simple INSERT (same as batch_insert)."""
        # append和batch_insert行为相同，都是直接INSERT
        logger.info("[TableOutput] append mode - using INSERT")
        return self._hive_write_batch_insert(connection, df, table_name)

    def _hive_write_upsert(self, connection, df: pd.DataFrame, table_name: str) -> int:
        """UPSERT mode: INSERT or UPDATE based on key fields."""
        # 从字段映射中提取关键字段
        key_fields = self._extract_key_fields_from_mappings()

        if not key_fields:
            error_msg = i18n.t("components.input_output.table_output.errors.no_key_fields_upsert")
            raise ValueError(error_msg)

        rows_written = 0

        # 清理DataFrame
        df_clean = df.copy()
        for col in df_clean.columns:
            if df_clean[col].dtype in ["int64", "float64"]:
                df_clean[col] = df_clean[col].fillna(0)
            else:
                df_clean[col] = df_clean[col].fillna("")

        logger.info(
            f"[TableOutput] Upserting {len(df_clean)} rows to Hive table: {table_name} with key fields: {key_fields}"
        )

        try:
            with connection.cursor() as cursor:
                # Hive不支持原生的UPSERT，需要手动实现
                # 策略：先尝试更新，如果影响行数为0则插入

                for index, row in df_clean.iterrows():
                    # 构建UPDATE条件
                    where_conditions = []
                    where_values = []
                    for key_field in key_fields:
                        where_conditions.append(f"`{key_field}` = %s")
                        where_values.append(row[key_field])

                    where_clause = " AND ".join(where_conditions)

                    # 构建UPDATE语句
                    update_fields = []
                    update_values = []
                    for col in df_clean.columns:
                        if col not in key_fields:
                            update_fields.append(f"`{col}` = %s")
                            update_values.append(row[col])

                    if update_fields:
                        update_set = ", ".join(update_fields)
                        update_query = f"UPDATE `{table_name}` SET {update_set} WHERE {where_clause}"

                        cursor.execute(update_query, update_values + where_values)

                        # 检查是否有行被更新
                        if cursor.rowcount == 0:
                            # 没有行被更新，执行INSERT
                            columns = list(df_clean.columns)
                            column_str = ", ".join([f"`{col}`" for col in columns])
                            placeholders = ", ".join(["%s"] * len(columns))
                            insert_values = [row[col] for col in columns]

                            insert_query = f"INSERT INTO TABLE `{table_name}` ({column_str}) VALUES ({placeholders})"
                            cursor.execute(insert_query, insert_values)

                        rows_written += 1

        except Exception as e:
            logger.error(f"[TableOutput] Hive upsert error: {e!s}")
            raise

        logger.info(f"[TableOutput] Hive upsert completed: {rows_written} rows processed")
        return rows_written

    def _hive_write_replace(self, connection, df: pd.DataFrame, table_name: str) -> int:
        """REPLACE mode: DELETE all rows, then INSERT new."""
        logger.info(f"[TableOutput] replace mode - clearing table {table_name} before insert")

        try:
            with connection.cursor() as cursor:
                # Step 1: 清空表（Hive不支持DELETE，需要TRUNCATE或DROP/CREATE）
                # 使用TRUNCATE TABLE（如果支持）或者DROP/CREATE
                try:
                    cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                    logger.info(f"[TableOutput] Truncated Hive table: {table_name}")
                except Exception as truncate_error:
                    # 如果TRUNCATE不支持，使用DELETE（Hive 2.0+支持）
                    logger.warning(f"[TableOutput] TRUNCATE failed, trying DELETE: {truncate_error!s}")
                    try:
                        cursor.execute(f"DELETE FROM `{table_name}`")
                        logger.info(f"[TableOutput] Deleted all rows from Hive table: {table_name}")
                    except Exception as delete_error:
                        # 如果都不支持，只能使用INSERT OVERWRITE（Hive特有）
                        logger.warning(f"[TableOutput] DELETE failed, using INSERT OVERWRITE: {delete_error!s}")
                        # INSERT OVERWRITE会覆盖整个表，所以直接插入新数据即可

                # Step 2: 插入新数据
                if self.write_mode == "replace":
                    # 对于INSERT OVERWRITE模式，直接使用INSERT OVERWRITE语法
                    columns = list(df.columns)
                    column_str = ", ".join([f"`{col}`" for col in columns])

                    # 清理数据
                    df_clean = df.copy()
                    for col in df_clean.columns:
                        if df_clean[col].dtype in ["int64", "float64"]:
                            df_clean[col] = df_clean[col].fillna(0)
                        else:
                            df_clean[col] = df_clean[col].fillna("")

                    # 构建INSERT OVERWRITE语句（Hive特有，高效覆盖表数据）
                    placeholders = ", ".join(["%s"] * len(columns))
                    insert_query = f"INSERT OVERWRITE TABLE `{table_name}` ({column_str}) VALUES ({placeholders})"

                    data_tuples = [tuple(row) for row in df_clean.values]

                    # 使用单独INSERT语句避免executemany的"No result set"错误
                    rows_written = 0
                    for row_data in data_tuples:
                        cursor.execute(insert_query, row_data)
                        rows_written += 1
                else:
                    # 使用标准INSERT（如果之前使用了TRUNCATE或DELETE）
                    rows_written = self._hive_write_batch_insert(connection, df, table_name)

        except Exception as e:
            logger.error(f"[TableOutput] Hive replace error: {e!s}")
            raise

        logger.info(f"[TableOutput] Hive replace completed: {rows_written} rows inserted")
        return rows_written

    def get_row_count(self) -> Data:
        """Get the count of written rows from cached result."""
        # 避免重复写入数据，从缓存的结果中获取行数
        if hasattr(self, "_last_write_result") and self._last_write_result:
            rows_written = self._last_write_result.data.get("rows_written", 0)
        else:
            # 如果没有缓存结果，返回0（不应该发生，因为result输出应该先执行）
            logger.warning("[TableOutput] get_row_count called but no cached write result found")
            rows_written = 0

        return Data(data={"row_count": rows_written, "table": self.table_selector})

    def _write_to_clickhouse(self, connection_string: str, df: pd.DataFrame) -> int:
        """Write data to ClickHouse using native driver.

        Args:
            connection_string: ClickHouse connection string (clickhouse+connect://username:password@host:port/database)
            df: DataFrame to write

        Returns:
            Number of rows written
        """
        import re
        from urllib.parse import unquote

        import clickhouse_connect

        # Parse ClickHouse connection string
        # Format: clickhouse+connect://username:password@host:port/database
        match = re.match(r"clickhouse\+connect://([^:]+):([^@]*)@([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError(f"Invalid ClickHouse connection string format")

        username, password, host, port, database = match.groups()
        username = unquote(username)
        password = unquote(password) if password else ""
        port = int(port)

        logger.info(f"[TableOutput] Connecting to ClickHouse: {host}:{port}/{database}")

        # Build client parameters
        client_params = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        }

        # Create ClickHouse client
        client = clickhouse_connect.get_client(**client_params)

        try:
            table_name = self.table_selector

            # Handle write modes
            if self.write_mode == "replace":
                # Truncate table
                client.command(f"TRUNCATE TABLE IF EXISTS {table_name}")
                logger.info(f"[TableOutput] ClickHouse table '{table_name}' truncated")

            # Insert data
            # Convert DataFrame to list of lists for ClickHouse
            data = df.values.tolist()
            column_names = df.columns.tolist()

            client.insert(table_name, data, column_names=column_names)

            rows_written = len(df)
            logger.info(f"[TableOutput] Successfully wrote {rows_written} rows to ClickHouse table '{table_name}'")
            return rows_written

        finally:
            client.close()

    def _write_to_doris(self, connection_string: str, df: pd.DataFrame) -> int:
        """Write data to Apache Doris using pymysql.

        Args:
            connection_string: Doris connection string (mysql://username:password@host:port/database)
            df: DataFrame to write

        Returns:
            Number of rows written
        """
        import re
        from urllib.parse import unquote

        import pymysql

        # Parse Doris/MySQL connection string
        # Format: mysql://username:password@host:port/database or mysql+pymysql://...
        match = re.match(r"mysql(?:\+pymysql)?://([^:]+):([^@]*)@([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError(f"Invalid Doris/MySQL connection string format")

        username, password, host, port, database = match.groups()
        username = unquote(username)
        password = unquote(password) if password else ""
        port = int(port)

        logger.info(f"[TableOutput] Connecting to Doris: {host}:{port}/{database}")

        # Build connection parameters
        conn_params = {
            "host": host,
            "port": port,
            "user": username,
            "password": password,
            "database": database,
            "charset": "utf8",
        }

        # Create Doris connection
        connection = pymysql.connect(**conn_params)

        try:
            with connection.cursor() as cursor:
                table_name = self.table_selector

                # Handle write modes
                if self.write_mode == "replace":
                    # Truncate table
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                    connection.commit()
                    logger.info(f"[TableOutput] Doris table '{table_name}' truncated")

                # Prepare INSERT statement
                columns = df.columns.tolist()
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)
                insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"

                # Convert DataFrame to list of tuples
                data = [tuple(row) for row in df.values]

                # Batch insert
                cursor.executemany(insert_sql, data)
                connection.commit()

                rows_written = len(df)
                logger.info(f"[TableOutput] Successfully wrote {rows_written} rows to Doris table '{table_name}'")
                return rows_written

        finally:
            connection.close()

    def _write_to_mongodb(self, connection_string: str, df: pd.DataFrame) -> int:
        """Write data to MongoDB using pymongo.

        Args:
            connection_string: MongoDB connection string (mongodb://username:password@host:port/database)
            df: DataFrame to write

        Returns:
            Number of documents written
        """
        import re
        from urllib.parse import unquote

        from pymongo import MongoClient

        # Parse MongoDB connection string
        # Format: mongodb://[username:password@]host:port/database
        match = re.match(r"mongodb://(?:([^:]+):([^@]*)@)?([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError(f"Invalid MongoDB connection string format")

        username, password, host, port, database = match.groups()
        if username:
            username = unquote(username)
        if password:
            password = unquote(password)
        port = int(port)

        logger.info(f"[TableOutput] Connecting to MongoDB: {host}:{port}/{database}")

        # Build MongoDB connection parameters
        mongo_params = {
            "host": host,
            "port": port,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 20000,
        }

        # Add authentication if provided
        if username and password:
            mongo_params["username"] = username
            mongo_params["password"] = password

        # Create MongoDB client
        client = MongoClient(**mongo_params)

        try:
            # Access database and collection
            db = client[database]
            collection_name = self.table_selector
            collection = db[collection_name]

            # Handle write modes
            if self.write_mode == "replace":
                # Delete all documents
                collection.delete_many({})
                logger.info(f"[TableOutput] MongoDB collection '{collection_name}' cleared")

            # Convert DataFrame to list of dicts
            # Replace NaN with None for JSON compatibility
            df_clean = df.replace({pd.NA: None, pd.NaT: None})
            import numpy as np

            df_clean = df_clean.replace({np.nan: None, np.inf: None, -np.inf: None})

            documents = df_clean.to_dict("records")

            # Insert documents
            if documents:
                result = collection.insert_many(documents)
                rows_written = len(result.inserted_ids)
                logger.info(
                    f"[TableOutput] Successfully wrote {rows_written} documents to MongoDB collection '{collection_name}'"
                )
            else:
                rows_written = 0
                logger.warning("[TableOutput] No documents to insert")

            return rows_written

        finally:
            client.close()
