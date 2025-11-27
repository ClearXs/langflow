from typing import Any

import i18n
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.base.datasource.manager import DataSourceManager
from lfx.base.transformation import TransformationExecutor
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Transformation rule options - just the values
TRANSFORMATION_RULE_VALUES = [
    "none",
    "upper",
    "lower",
    "trim",
    "mask_phone",
    "mask_idcard",
    "mask_email",
    "mask_name",
    "md5",
    "sha256",
    "to_int",
    "to_float",
    "to_str",
    "to_bool",
    "expression",
    "javascript",
    "python",
]


def _serialize_value_for_table(value):
    """通用对象包装函数 - 把各种数据库对象包装成React可以渲染的简单结构。

    核心原则：保持原始数据结构不变，只是在表格显示时包装成 {"value": ""} 格式。
    支持：Neo4j, MongoDB, ClickHouse等数据库的复杂对象。
    """
    # 如果已经是原始类型，包装成 {"value": 原始值}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"value": value}


def _serialize_neo4j_value(value):
    """Neo4j对象包装函数 - 调用通用序列化函数。"""
    return _serialize_value_for_table(value)


def _convert_neo4j_record_to_dict(record):
    """Convert a Neo4j Record to a flat dictionary with serializable values.

    Args:
        record: A Neo4j Record object

    Returns:
        A dictionary with all values serialized for table display
    """
    logger.debug(f"[TableInput] Converting Neo4j record with keys: {record.keys()}")
    result = {}
    for key in record.keys():
        try:
            value = record[key]
            logger.debug(f"[TableInput] Processing field '{key}' of type {type(value)}")

            # 保持原始数据,只是转换为JSON字符串用于显示
            serialized_value = _serialize_neo4j_value(value)

            logger.debug(f"[TableInput] Serialized '{key}' to: {type(serialized_value)}")
            result[key] = serialized_value
        except Exception as e:
            # If serialization fails for any reason, provide error info
            error_msg = f"<Error: {e!s}>"
            logger.error(f"[TableInput] Error serializing field '{key}': {error_msg}")
            result[key] = error_msg

    logger.debug(f"[TableInput] Final converted record: {result}")
    return result


def _convert_mongodb_doc_to_table_format(doc: dict) -> dict:
    """Convert a MongoDB document to single-field table format.

    This function takes a MongoDB document and converts it to a single-field
    format suitable for table display, where the entire document is JSON-serialized
    and wrapped in a {"value": "..."} structure.

    Args:
        doc: A MongoDB document (dict)

    Returns:
        A dictionary with single "value" key containing JSON-serialized document
    """
    try:
        # Convert ObjectId and other MongoDB-specific types to strings
        import json

        # Deep copy to avoid modifying original
        doc_copy = {}
        for key, value in doc.items():
            if key == "_id":
                # Convert ObjectId to string
                doc_copy[key] = str(value)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                doc_copy[key] = value
            else:
                # For complex types, convert to string
                try:
                    doc_copy[key] = json.dumps(value, ensure_ascii=False, default=str)
                except Exception:
                    doc_copy[key] = str(value)

        # Convert the entire document to JSON string
        json_str = json.dumps(doc_copy, ensure_ascii=False, default=str)

        # Wrap in single-field format for table display
        table_format = {"value": json_str}

        logger.debug(f"[TableInput] MongoDB document converted to table format: {table_format}")
        return table_format

    except Exception as e:
        error_msg = f"<Error converting MongoDB document to table format: {e!s}>"
        logger.error(f"[TableInput] Error in MongoDB table format conversion: {error_msg}")
        return {"value": error_msg}


def _convert_neo4j_record_to_table_format(record):
    """Convert a Neo4j Record to single-field table format.

    This function takes a Neo4j record and converts it to a single-field
    format suitable for table display, where the entire record is JSON-serialized
    and wrapped in a {"value": "..."} structure.

    Args:
        record: A Neo4j Record object

    Returns:
        A dictionary with single "value" key containing JSON-serialized record
    """
    logger.debug(f"[TableInput] Converting Neo4j record to table format with keys: {record.keys()}")

    # First convert using the standard method
    record_dict = _convert_neo4j_record_to_dict(record)

    try:
        # Convert the entire record to JSON string
        import json

        json_str = json.dumps(record_dict, ensure_ascii=False, default=str)

        # Wrap in single-field format for table display
        table_format = {"value": json_str}

        logger.debug(f"[TableInput] Table format result: {table_format}")
        return table_format

    except Exception as e:
        error_msg = f"<Error converting record to table format: {e!s}>"
        logger.error(f"[TableInput] Error in table format conversion: {error_msg}")
        return {"value": error_msg}


class ETLTableInputComponent(Component):
    display_name = i18n.t("components.input_output.table_input.display_name")
    description = i18n.t("components.input_output.table_input.description")
    icon = "database"
    name = "ETLTableInput"
    include_universal_input = True  # Enable universal input for Table Input

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_manager = DataSourceManager()
        self.transformation_executor = TransformationExecutor()

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.table_input.datasource_selector.display_name"),
            info=i18n.t("components.input_output.table_input.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],  # Will be loaded dynamically
            real_time_refresh=True,
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        MultilineInput(
            name="sql_query",
            display_name=i18n.t("components.input_output.table_input.sql_query.display_name"),
            info=i18n.t("components.input_output.table_input.sql_query.info"),
            required=True,
            placeholder="SELECT * FROM your_table WHERE 1=1",
            advanced=False,
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.input_output.table_input.field_mappings.display_name"),
            info=i18n.t("components.input_output.table_input.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.source_field"),
                    "type": "str",
                    "disable_edit": True,  # 只读
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.data_type"),
                    "type": "str",
                    "disable_edit": True,  # 只读
                    "formatter": "code",
                    "translate_value": False,
                },
                {
                    "name": "null_value",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.null_value"),
                    "type": "str",
                    "description": i18n.t("components.input_output.table_input.field_mappings.null_value_desc"),
                },
                {
                    "name": "transformation_rule",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.transformation_rule"),
                    "type": "str",
                    "formatter": "text",
                    "options": TRANSFORMATION_RULE_VALUES,
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "analyze_sql",
                        "label": i18n.t("components.input_output.table_input.field_mappings.analyze_sql_button"),
                        "icon": "Search",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.table_input.preview_table.display_name"),
            info=i18n.t("components.input_output.table_input.preview_table.info"),
            table_schema=[],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "preview_data",
                        "label": i18n.t("components.input_output.table_input.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        BoolInput(
            name="use_pagination",
            display_name=i18n.t("components.input_output.table_input.use_pagination.display_name"),
            info=i18n.t("components.input_output.table_input.use_pagination.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="page_size",
            display_name=i18n.t("components.input_output.table_input.page_size.display_name"),
            info=i18n.t("components.input_output.table_input.page_size.info"),
            value=1000,
            range_spec={"min": 1, "max": 100000},
            advanced=True,
        ),
        IntInput(
            name="max_records",
            display_name=i18n.t("components.input_output.table_input.max_records.display_name"),
            info=i18n.t("components.input_output.table_input.max_records.info"),
            value=0,
            advanced=True,
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t("components.input_output.table_input.enable_transaction.display_name"),
            info=i18n.t("components.input_output.table_input.enable_transaction.info"),
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="isolation_level",
            display_name=i18n.t("components.input_output.table_input.isolation_level.display_name"),
            info=i18n.t("components.input_output.table_input.isolation_level.info"),
            options=["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "DEFAULT"],
            value="DEFAULT",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.table_input.outputs.data"),
            method="load_data",
        ),
        Output(
            name="row_count",
            display_name=i18n.t("components.input_output.table_input.outputs.row_count"),
            method="get_row_count",
        ),
        Output(
            name="fields_schema",
            display_name=i18n.t("components.input_output.table_input.outputs.fields_schema"),
            method="get_fields_schema",
        ),
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates based on field changes and action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(
            f"[TableInput] update_build_config called - field_name: {field_name}, "
            f"field_value: {field_value}, action: {action}"
        )

        # Always load datasources for: initial load (None) or refresh datasource_selector (empty value)
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"[TableInput] Loading datasources (field_name={field_name}, field_value={field_value})")
            try:
                # 加载统一的数据源列表（内置 + 公共）
                all_datasources = self._load_unified_datasources()

                # 构建显示选项和元数据
                options = []
                options_metadata = []

                # Table Input 排除 Kafka（Kafka 不支持 SQL 查询）
                excluded_types = {"kafka"}

                for ds in all_datasources:
                    # 过滤：排除 Kafka
                    ds_type = ds.get("type", "").lower()
                    if ds_type in excluded_types:
                        logger.debug(f"[TableInput] Skipping excluded datasource type: {ds_type} (name={ds['name']})")
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
                logger.debug(f"[TableInput] Set datasource_selector options: {options} (excluded Kafka)")
                logger.debug(f"[TableInput] Set options_metadata with {len(options_metadata)} entries")

            except Exception as e:
                logger.error(f"[TableInput] Error loading unified datasources: {e}")
                # 设置错误选项
                build_config["datasource_selector"]["options"] = ["加载失败"]
                build_config["datasource_selector"]["options_metadata"] = []

        # When datasource is selected, we can optionally load table/column metadata for SQL assistance
        # But we don't auto-populate anything - user writes their own SQL
        if field_name == "datasource_selector" and field_value:
            current_datasource = field_value
            logger.info(f"[TableInput] Datasource selected: {current_datasource}")

            # 验证选择的数据源是否在可用列表中
            options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
            if options_metadata:
                available_names = [m.get("display_name") for m in options_metadata]
                if current_datasource not in available_names:
                    logger.warning(
                        f"[TableInput] Selected datasource '{current_datasource}' is not in the available list: {available_names}"
                    )
                    logger.warning(
                        "[TableInput] This may indicate a stale selection. The datasource may have been deleted or renamed."
                    )
                    # 不抛出错误，但记录警告，让用户知道可能有问题
            else:
                logger.warning(
                    f"[TableInput] No options_metadata available to validate datasource selection: {current_datasource}"
                )

            # Just log the selection, no further action needed
            # User will write their own SQL query

        # Handle action button clicks (from field_mappings table)
        if field_name == "field_mappings" and action == "analyze_sql":
            logger.info("[TableInput] SQL analysis triggered by action button")

            try:
                # 获取当前SQL和数据源
                current_sql = build_config.get("sql_query", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("[TableInput] No SQL query provided")
                    self.status = i18n.t("components.input_output.table_input.errors.no_sql")
                    return build_config

                if not current_datasource:
                    logger.warning("[TableInput] No datasource selected")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # 从 options_metadata 中获取数据源ID和信息
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_id = self._get_datasource_id_from_metadata(current_datasource, options_metadata)

                if not datasource_id:
                    logger.error(f"[TableInput] Cannot find datasource ID for: {current_datasource}")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # 获取数据源详细信息（用于区分公共和内置数据源）
                datasource_info = None
                for metadata in options_metadata:
                    # 优先按 id/value 匹配（公共数据源传递ID），向后兼容 display_name
                    if (
                        metadata.get("id") == current_datasource
                        or metadata.get("value") == current_datasource
                        or metadata.get("display_name") == current_datasource
                    ):
                        datasource_info = metadata
                        break

                # ✅ 检查 datasource_info 是否包含必要的连接参数
                # 如果是内置数据源但缺少 host/port，或者是公共数据源但缺少 raw_data，则重新加载
                needs_reload = False
                if datasource_info:
                    source = datasource_info.get("source")
                    if source == "builtin":
                        # 内置数据源需要 host 和 port（Neo4j除外，它可能用url）
                        ds_type = datasource_info.get("type", "").lower()
                        if ds_type != "neo4j" and (
                            not datasource_info.get("host") or not datasource_info.get("port")
                        ):
                            logger.warning(
                                f"[TableInput] Cached datasource_info missing connection params (host/port), reloading"
                            )
                            needs_reload = True
                    elif source == "public":
                        # 公共数据源需要 raw_data
                        if not datasource_info.get("raw_data"):
                            logger.warning(f"[TableInput] Cached datasource_info missing raw_data, reloading")
                            needs_reload = True

                # 如果在 options_metadata 中找不到，或者缺少必要参数，尝试重新加载数据源列表
                if not datasource_info or needs_reload:
                    if not datasource_info:
                        logger.warning("[TableInput] Datasource info not found in options_metadata, reloading datasources")
                    else:
                        logger.info("[TableInput] Reloading datasources to get complete connection params")
                    all_datasources = self._load_unified_datasources()
                    for ds in all_datasources:
                        # 优先按 id 匹配，向后兼容 display_name
                        if ds["id"] == current_datasource or ds["display_name"] == current_datasource:
                            datasource_info = {
                                "id": ds["id"],
                                "name": ds["name"],
                                "type": ds["type"],
                                "source": ds["source"],
                                "display_name": ds["display_name"],
                                "raw_data": ds.get("raw_data"),
                                # ✅ 包含预构建的连接字符串和参数，避免API调用
                                "connection_string": ds.get("connection_string"),
                                "host": ds.get("host"),
                                "port": ds.get("port"),
                                "database": ds.get("database"),
                                "username": ds.get("username"),
                                "password": ds.get("password"),
                                "advanced_config": ds.get("advanced_config"),
                            }
                            # 更新 options_metadata
                            if ds["display_name"] not in [m.get("display_name") for m in options_metadata]:
                                options_metadata.append(datasource_info)
                            break

                # 保存数据源信息供后续使用
                self._current_datasource_info = datasource_info

                # 调试日志
                if datasource_info:
                    logger.debug(
                        f"[TableInput] Datasource info found: source={datasource_info.get('source')}, "
                        f"has_raw_data={bool(datasource_info.get('raw_data'))}"
                    )
                else:
                    logger.error(f"[TableInput] Failed to find datasource info for: {current_datasource}")

                # 执行SQL分析
                logger.info("[TableInput] Starting SQL field inference...")
                self.status = i18n.t("components.input_output.table_input.status.analyzing_sql")

                field_info = self._infer_field_info(datasource_id, current_sql)

                if field_info:
                    # 更新field_mappings
                    build_config["field_mappings"]["value"] = field_info
                    logger.info(f"[TableInput] SQL analysis completed, generated {len(field_info)} field mappings")
                    self.status = i18n.t(
                        "components.input_output.table_input.status.analysis_success", count=len(field_info)
                    )
                else:
                    logger.warning("[TableInput] No fields inferred from SQL")
                    self.status = i18n.t("components.input_output.table_input.status.no_fields_found")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[TableInput] SQL analysis failed: {error_msg}")
                self.status = i18n.t("components.input_output.table_input.errors.analysis_failed", error=error_msg)
                # Don't throw exception, let user continue

        # Handle preview button clicks (from preview_table)
        if field_name == "preview_table" and action == "preview_data":
            logger.info("[TableInput] Data preview triggered by action button")

            try:
                # 获取当前SQL和数据源
                current_sql = build_config.get("sql_query", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("[TableInput] No SQL query provided for preview")
                    self.status = i18n.t("components.input_output.table_input.errors.no_sql")
                    return build_config

                if not current_datasource:
                    logger.warning("[TableInput] No datasource selected for preview")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # 从 options_metadata 中获取数据源ID
                datasource_id = self._get_datasource_id_from_metadata(
                    current_datasource, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if not datasource_id:
                    logger.error(f"[TableInput] Cannot find datasource ID for preview: {current_datasource}")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # Execute preview query (max 100 rows)
                logger.info("[TableInput] Starting data preview (first 100 rows)...")
                self.status = i18n.t("components.input_output.table_input.status.previewing_data")

                # Get database connection string
                # 从options_metadata中获取数据源信息
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_info = None
                for metadata in options_metadata:
                    # 支持通过 display_name、id 或 value 来匹配
                    if (
                        metadata.get("display_name") == current_datasource
                        or metadata.get("id") == current_datasource
                        or metadata.get("value") == current_datasource
                    ):
                        datasource_info = metadata
                        break

                # ✅ 检查 datasource_info 是否包含必要的连接参数（与SQL分析相同的逻辑）
                needs_reload = False
                if datasource_info:
                    source = datasource_info.get("source")
                    if source == "builtin":
                        # 内置数据源需要 host 和 port（Neo4j除外）
                        ds_type = datasource_info.get("type", "").lower()
                        if ds_type != "neo4j" and (
                            not datasource_info.get("host") or not datasource_info.get("port")
                        ):
                            logger.warning(
                                f"[TableInput] Preview: Cached datasource_info missing connection params, reloading"
                            )
                            needs_reload = True
                    elif source == "public":
                        # 公共数据源需要 raw_data
                        if not datasource_info.get("raw_data"):
                            logger.warning(f"[TableInput] Preview: Cached datasource_info missing raw_data, reloading")
                            needs_reload = True

                # 如果在 options_metadata 中找不到，或缺少必要参数，尝试重新加载数据源列表
                if not datasource_info or needs_reload:
                    if not datasource_info:
                        logger.warning(
                            "[TableInput] Datasource info not found in options_metadata for preview, reloading datasources"
                        )
                    else:
                        logger.info("[TableInput] Preview: Reloading datasources to get complete connection params")
                    all_datasources = self._load_unified_datasources()
                    for ds in all_datasources:
                        # 支持通过 display_name 或 id 来匹配
                        if ds["display_name"] == current_datasource or ds["id"] == current_datasource:
                            datasource_info = {
                                "id": ds["id"],
                                "name": ds["name"],
                                "type": ds["type"],
                                "source": ds["source"],
                                "display_name": ds["display_name"],
                                "raw_data": ds.get("raw_data"),
                                # ✅ 包含预构建的连接字符串和参数，避免API调用
                                "connection_string": ds.get("connection_string"),
                                "host": ds.get("host"),
                                "port": ds.get("port"),
                                "database": ds.get("database"),
                                "username": ds.get("username"),
                                "password": ds.get("password"),
                                "advanced_config": ds.get("advanced_config"),
                            }
                            break

                # 保存数据源信息供后续使用
                self._current_datasource_info = datasource_info

                # ✅ 添加详细调试日志
                if datasource_info:
                    logger.debug(
                        f"[TableInput] Found datasource info: type={datasource_info.get('type')}, "
                        f"name={datasource_info.get('name')}, id={datasource_info.get('id')}, "
                        f"source={datasource_info.get('source')}, has_raw_data={bool(datasource_info.get('raw_data'))}"
                    )
                    # 如果是公共数据源，显示 raw_data 的键
                    if datasource_info.get("source") == "public" and datasource_info.get("raw_data"):
                        raw_data = datasource_info["raw_data"]
                        logger.debug(f"[TableInput] Public datasource raw_data keys: {list(raw_data.keys())}")
                        if "dataSourceParam" in raw_data:
                            params = raw_data["dataSourceParam"]
                            logger.debug(
                                f"[TableInput] dataSourceParam keys: {list(params.keys()) if isinstance(params, dict) else 'NOT A DICT'}"
                            )
                            if isinstance(params, dict):
                                logger.debug(
                                    f"[TableInput] Extracted params: host={params.get('host')}, "
                                    f"port={params.get('port')}, database={params.get('database')}"
                                )
                else:
                    logger.warning("[TableInput] datasource_info is None!")

                connection_string = self._get_connection_string(datasource_id, datasource_info)

                # Check datasource type
                is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"
                is_mongodb = datasource_info and datasource_info.get("type", "").lower() == "mongodb"
                is_clickhouse = datasource_info and datasource_info.get("type", "").lower() == "clickhouse"

                logger.debug(
                    f"[TableInput] Datasource type check: is_neo4j={is_neo4j}, is_mongodb={is_mongodb}, "
                    f"is_clickhouse={is_clickhouse}, type={datasource_info.get('type') if datasource_info else 'N/A'}"
                )

                if is_neo4j:
                    # Neo4j requires native driver, not SQLAlchemy
                    import re
                    from urllib.parse import unquote

                    from neo4j import GraphDatabase

                    logger.debug(f"[TableInput] Neo4j connection string: {connection_string}")

                    # Parse bolt URI to get host, port, and credentials
                    # Format: bolt://[username:password@]host:port
                    match = re.match(r"bolt://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", connection_string)
                    if not match:
                        raise ValueError(f"Invalid Neo4j connection string format: {connection_string}")

                    username, password, host, port = match.groups()

                    # URL decode username and password (they are URL-encoded in the connection string)
                    if username:
                        username = unquote(username)
                    if password:
                        password = unquote(password)

                    logger.debug(
                        f"[TableInput] Parsed Neo4j connection: username={username}, "
                        f"password={'***' if password else None}, host={host}, port={port}"
                    )
                    uri = f"bolt://{host}:{port}"

                    driver = GraphDatabase.driver(uri, auth=(username, password) if username else None)
                    try:
                        with driver.session() as session:
                            # Execute Cypher query
                            result = session.run(current_sql)
                            # Convert to list of dictionaries with serialized Neo4j objects
                            records = []
                            for record in result:
                                records.append(_convert_neo4j_record_to_table_format(record))
                            df = pd.DataFrame(records)
                    finally:
                        driver.close()
                elif is_mongodb:
                    # MongoDB requires pymongo, not SQLAlchemy
                    import json
                    import re
                    from urllib.parse import unquote

                    from pymongo import MongoClient

                    logger.info("[TableInput] Detected MongoDB datasource, using pymongo driver")

                    # Parse MongoDB query JSON
                    try:
                        query_dict = json.loads(current_sql)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f'Invalid MongoDB query JSON: {e}. Expected format: {{"collection": "name", "operation": "find", "filter": {{}}}}'
                        ) from e

                    collection_name = query_dict.get("collection")
                    if not collection_name:
                        raise ValueError("MongoDB query must specify 'collection' field")

                    operation = query_dict.get("operation", "find")
                    mongo_filter = query_dict.get("filter", {})
                    projection = query_dict.get("projection")
                    sort = query_dict.get("sort")
                    limit = query_dict.get("limit", 100)  # Default 100 for preview

                    # Parse MongoDB connection string to get correct parameters
                    # Format: mongodb://[username:password@]host:port/database
                    match = re.match(r"mongodb://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)/(.+)", connection_string)
                    if not match:
                        raise ValueError(f"Invalid MongoDB connection string: {connection_string}")

                    username, password, host, port, database = match.groups()
                    if username:
                        username = unquote(username)
                    if password:
                        password = unquote(password)

                    logger.debug(f"[TableInput] MongoDB connection: host={host}, port={port}, database={database}")

                    # Build MongoDB connection parameters
                    mongo_params = {
                        "host": host,
                        "port": int(port),
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

                        if operation == "find":
                            # Build find query
                            cursor = collection.find(mongo_filter, projection)
                            if sort:
                                cursor = cursor.sort(list(sort.items()))
                            cursor = cursor.limit(limit)

                            # Fetch data and serialize for table display
                            records = []
                            for doc in cursor:
                                # Convert entire MongoDB document to table format (like Neo4j)
                                # Wrap whole document as {"value": "JSON string"}
                                table_row = _convert_mongodb_doc_to_table_format(doc)
                                logger.debug(f"[TableInput] MongoDB table row: {table_row}")
                                records.append(table_row)

                            logger.debug(f"[TableInput] MongoDB records count: {len(records)}")
                            if records:
                                logger.debug(f"[TableInput] First MongoDB record: {records[0]}")

                            df = pd.DataFrame(records)
                            logger.debug(f"[TableInput] DataFrame columns: {df.columns.tolist()}")
                            logger.debug(f"[TableInput] DataFrame shape: {df.shape}")
                        elif operation == "aggregate":
                            # Aggregation pipeline
                            pipeline = query_dict.get("pipeline", [])
                            cursor = collection.aggregate(pipeline)

                            records = []
                            for doc in cursor:
                                # Convert entire MongoDB document to table format (like Neo4j)
                                # Wrap whole document as {"value": "JSON string"}
                                table_row = _convert_mongodb_doc_to_table_format(doc)
                                logger.debug(f"[TableInput] MongoDB aggregate table row: {table_row}")
                                records.append(table_row)

                            logger.debug(f"[TableInput] MongoDB aggregate records count: {len(records)}")
                            if records:
                                logger.debug(f"[TableInput] First MongoDB aggregate record: {records[0]}")

                            df = pd.DataFrame(records)
                            logger.debug(f"[TableInput] Aggregate DataFrame columns: {df.columns.tolist()}")
                            logger.debug(f"[TableInput] Aggregate DataFrame shape: {df.shape}")
                        else:
                            raise ValueError(f"Unsupported MongoDB operation: {operation}")

                        logger.debug(f"[TableInput] MongoDB query returned {len(df)} rows")
                    finally:
                        client.close()
                elif is_clickhouse:
                    # ClickHouse requires clickhouse-connect, not SQLAlchemy
                    import re
                    from urllib.parse import unquote

                    import clickhouse_connect

                    logger.info("[TableInput] Detected ClickHouse datasource, using clickhouse-connect driver")

                    # ✅ 添加调试日志：显示连接字符串
                    logger.debug(f"[TableInput] Preview - ClickHouse connection_string: {connection_string}")

                    # Parse ClickHouse connection string
                    # Format: clickhouse+connect://username:password@host:port/database
                    match = re.match(r"clickhouse\+connect://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", connection_string)
                    if not match:
                        raise ValueError(f"Invalid ClickHouse connection string format: {connection_string}")

                    username, password, host, port, database = match.groups()
                    username = unquote(username)
                    password = unquote(password)

                    # ✅ 添加调试日志：显示解析后的参数
                    logger.debug(
                        f"[TableInput] Preview - Parsed ClickHouse params: host={host}, port={port}, "
                        f"database={database}, username={username}"
                    )

                    # Create ClickHouse client
                    logger.info(
                        f"[TableInput] Preview - Creating ClickHouse client: host={host}, port={port}, database={database}"
                    )
                    client = clickhouse_connect.get_client(
                        host=host, port=int(port), username=username, password=password, database=database
                    )

                    try:
                        # Add LIMIT to query if not present
                        query_upper = current_sql.upper().strip()
                        if "LIMIT" not in query_upper:
                            preview_sql = f"{current_sql} LIMIT 100"
                        else:
                            preview_sql = current_sql

                        # Execute query
                        result = client.query(preview_sql)

                        # Convert to DataFrame
                        if result.result_rows:
                            column_names = result.column_names
                            records = [dict(zip(column_names, row, strict=False)) for row in result.result_rows]
                            df = pd.DataFrame(records)
                        else:
                            df = pd.DataFrame()

                        logger.debug(f"[TableInput] ClickHouse query returned {len(df)} rows")
                    finally:
                        client.close()
                else:
                    # For SQL databases, use SQLAlchemy
                    engine = create_engine(connection_string, poolclass=NullPool)
                    try:
                        with engine.connect() as conn:
                            # Execute SQL query, limit to 100 rows
                            preview_sql = f"{current_sql} LIMIT 100"
                            df = pd.read_sql_query(text(preview_sql), conn)
                    finally:
                        engine.dispose()

                # Process query results (common for both Neo4j and SQL)
                if df.empty:
                    logger.warning("[TableInput] No data returned from preview query")
                    self.status = i18n.t("components.input_output.table_input.status.no_data_found")
                    # Clear preview table
                    build_config["preview_table"]["table_schema"] = []
                    build_config["preview_table"]["value"] = []
                    return build_config

                # Generate table schema
                # For MongoDB/Neo4j single-column format, use "json" type for better frontend rendering
                table_schema = []
                for col in df.columns:
                    col_type = "str"  # Default type
                    # If this is MongoDB/Neo4j format (single "value" column), use "json" type
                    if str(col) == "value" and len(df.columns) == 1:
                        col_type = "json"
                        logger.debug("[TableInput] Using 'json' type for single 'value' column (MongoDB/Neo4j format)")

                    table_schema.append(
                        {
                            "name": str(col),
                            "display_name": str(col),
                            "type": col_type,
                            "disable_edit": True,
                        }
                    )

                # Convert DataFrame to list of dicts
                preview_data = df.fillna("").to_dict("records")

                logger.debug(f"[TableInput] Preview table schema: {table_schema}")
                logger.debug(f"[TableInput] Preview data count: {len(preview_data)}")
                if preview_data:
                    logger.debug(f"[TableInput] First preview data row: {preview_data[0]}")
                    logger.debug(f"[TableInput] First preview data row type: {type(preview_data[0])}")
                    if preview_data[0]:
                        for key, val in preview_data[0].items():
                            logger.debug(
                                f"[TableInput] Preview data field '{key}': {type(val).__name__} = {str(val)[:200]}"
                            )

                # Update preview table config
                build_config["preview_table"]["table_schema"] = table_schema
                build_config["preview_table"]["value"] = preview_data

                logger.info(f"[TableInput] Preview completed, showing {len(preview_data)} rows")
                self.status = self._format_i18n(
                    "components.input_output.table_input.status.preview_success", count=len(preview_data)
                )

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                logger.error(f"[TableInput] Data preview failed: {error_msg}")
                self.status = self._format_i18n(
                    "components.input_output.table_input.errors.preview_failed", error=error_msg
                )
                # Don't throw exception, let user continue

        logger.debug(f"[TableInput] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _load_unified_datasources(self) -> list[dict]:
        """加载统一的数据源列表（内置数据源 + 公共数据源）"""
        try:
            # 获取内置数据源
            builtin_datasources = self._get_builtin_datasources()

            # 获取公共数据源
            try:
                # Use asyncio.get_event_loop().run_until_complete() to handle nested event loops
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    # Already in event loop, use ThreadPoolExecutor
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_public_datasources())
                        public_datasources = future.result(timeout=5)
                except RuntimeError:
                    # No running event loop, use asyncio.run()
                    public_datasources = asyncio.run(self._get_public_datasources())
            except Exception as e:
                logger.warning(f"[TableInput] Failed to get public datasources: {e}")
                public_datasources = []

            # 合并数据源列表
            all_datasources = []

            # 添加内置数据源 - 包含完整连接参数（包括密码），用于本地构建连接字符串
            for ds in builtin_datasources:
                display_name = f"{ds['name']} ({ds['type']}) [自定义]"

                # ✅ 调试日志：显示从 builtin_datasources 获取的值
                logger.debug(
                    f"[TableInput] Adding builtin datasource {ds['name']}: "
                    f"has_host={ds.get('host') is not None}, has_port={ds.get('port') is not None}, "
                    f"host={ds.get('host')}, port={ds.get('port')}, "
                    f"keys={list(ds.keys())}"
                )

                all_datasources.append(
                    {
                        "id": str(ds["id"]),
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "builtin",
                        "display_name": display_name,
                        # ✅ 包含预构建的连接字符串和参数，避免API调用
                        "host": ds.get("host"),
                        "port": ds.get("port"),
                        "database": ds.get("database"),
                        "username": ds.get("username"),
                        "password": ds.get("password"),
                        "advanced_config": ds.get("advanced_config"),
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
                f"[TableInput] Loaded {len(all_datasources)} datasources ({len(builtin_datasources)} builtin, {len(public_datasources)} public)"
            )
            return all_datasources

        except Exception as e:
            logger.error(f"[TableInput] Error loading unified datasources: {e}")
            return []

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
                    logger.debug(f"[TableInput] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                    return uuid_part

        # 如果没有前缀或不符合UUID格式，直接返回
        return datasource_id

    def _get_builtin_datasources(self) -> list[dict]:
        """获取内置数据源 - 直接从数据库读取，包含完整连接信息"""
        logger.info("[TableInput] ✅ _get_builtin_datasources() called - NEW CODE VERSION")
        try:
            # 直接从数据库读取数据源，避免API调用导致的死锁
            import asyncio
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

                        logger.debug(f"[TableInput] Fetched {len(datasources)} datasources from database")

                        builtin_list = []
                        for ds in datasources:
                            # ✅ 调试日志：查看从数据库加载的数据源字段值
                            logger.debug(
                                f"[TableInput] DB datasource {ds.name}: "
                                f"type={ds.type}, host={ds.host}, port={ds.port}, "
                                f"database={ds.database}, username={ds.username}, "
                                f"has_password={bool(ds.password)}, "
                                f"advanced_config={ds.advanced_config[:100] if ds.advanced_config else None}"
                            )

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
                    logger.error(f"[TableInput] Error fetching datasources from database: {e}")
                    return []

            # 执行异步操作
            try:
                loop = asyncio.get_running_loop()
                # 在事件循环中，使用ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch_datasources())
                    builtin_datasources = future.result(timeout=5)
            except RuntimeError:
                # 没有运行中的事件循环，直接使用asyncio.run
                builtin_datasources = asyncio.run(fetch_datasources())

            logger.debug(f"[TableInput] Got {len(builtin_datasources)} builtin datasources from database")
            return builtin_datasources

        except Exception as e:
            logger.error(f"[TableInput] Error getting builtin datasources: {e}")
            return []

    def _get_builtin_datasources_legacy(self) -> list[dict]:
        """获取内置数据源 - 旧方法（通过DataSourceManager）"""
        try:
            # Use ThreadPoolExecutor to handle nested event loops
            import asyncio
            import concurrent.futures

            try:
                loop = asyncio.get_running_loop()
                # Already in event loop, use ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.datasource_manager.get_datasources())
                    datasources = future.result(timeout=5)
            except RuntimeError:
                # No running event loop, use asyncio.run()
                datasources = asyncio.run(self.datasource_manager.get_datasources())

            logger.debug(
                f"[TableInput] Got datasources from manager: enterprise={len(datasources.get('enterprise', []))}, custom={len(datasources.get('custom', []))}"
            )

            builtin_datasources = []

            # 合并企业和自定义数据源
            for ds in datasources.get("enterprise", []):
                # 企业数据源ID通常不需要前缀，直接使用
                datasource_id = self._extract_uuid_from_id(ds["id"])
                builtin_datasources.append(
                    {
                        "id": datasource_id,
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "enterprise",
                        "database": ds.get("database"),  # 保留 database 字段
                        "host": ds.get("host"),
                        "port": ds.get("port"),
                    }
                )
                logger.debug(f"[TableInput] Added enterprise datasource: {ds['name']} (ID: {datasource_id})")

            for ds in datasources.get("custom", []):
                # 自定义数据源ID可能包含前缀，需要提取纯UUID
                datasource_id = self._extract_uuid_from_id(ds["id"])
                builtin_datasources.append(
                    {
                        "id": datasource_id,
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": "custom",
                        "database": ds.get("database"),  # 保留 database 字段
                        "host": ds.get("host"),
                        "port": ds.get("port"),
                    }
                )
                logger.debug(f"[TableInput] Added custom datasource: {ds['name']} (ID: {datasource_id})")

            logger.info(f"[TableInput] Total builtin datasources loaded: {len(builtin_datasources)}")
            return builtin_datasources

        except Exception as e:
            logger.error(f"[TableInput] Error getting builtin datasources: {e}")
            import traceback

            logger.error(f"[TableInput] Traceback: {traceback.format_exc()}")
            return []

    async def _get_public_datasources(self) -> list[dict]:
        """通过feign接口获取公共数据源"""
        try:
            from lfx.services.deps import get_feign_service

            feign_service = get_feign_service()
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            client = DataConstructionFeignClient(feign_service)

            # 调用feign接口
            datasource_list = await client.get_datasource_list()

            logger.info(f"[TableInput] Got {len(datasource_list)} public datasources from feign API")
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[TableInput] Error getting public datasources: {e}")
            return []

    def _get_datasource_type_for_display(self, datasource: dict, source: str) -> dict:
        """获取用于显示的数据源类型和数据库信息"""
        if source == "public":
            # 公共数据源：从dataSourceParam获取信息
            raw_data = datasource
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
            raw_data = datasource

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

    def _get_datasource_id_from_metadata(self, selector_value: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据选择器值获取数据源ID

        Args:
            selector_value: 选择器的值，现在直接就是数据源ID
            options_metadata: 元数据列表

        Returns:
            数据源ID，如果未找到则返回None
        """
        logger.debug(f"[TableInput] Looking for datasource ID from selector value: '{selector_value}'")
        logger.debug(f"[TableInput] Available metadata entries: {len(options_metadata)}")

        if not options_metadata:
            logger.warning("[TableInput] No options_metadata provided")
            return None

        # 现在 selector_value 直接就是ID，直接返回
        # 但我们先验证它确实存在于 metadata 中
        for metadata in options_metadata:
            if metadata.get("id") == selector_value or metadata.get("value") == selector_value:
                logger.info(f"[TableInput] Found valid datasource ID: '{selector_value}'")
                return selector_value

        # 向后兼容：尝试从旧的 "ID|||显示名称" 格式中提取ID
        if "|||" in selector_value:
            datasource_id = selector_value.split("|||")[0]
            logger.warning(f"[TableInput] Legacy format detected, extracted ID '{datasource_id}' from selector value")
            return datasource_id

        # 再向后兼容：按显示名称查找
        logger.warning(f"[TableInput] Trying legacy lookup by display name for: '{selector_value}'")
        for metadata in options_metadata:
            if metadata.get("display_name") == selector_value:
                datasource_id = metadata.get("id")
                logger.info(f"[TableInput] Found datasource ID '{datasource_id}' for display name '{selector_value}'")
                return datasource_id

        logger.error(f"[TableInput] No metadata found for selector value: '{selector_value}'")
        return None

    def _format_i18n(self, key: str, **kwargs) -> str:
        """Format i18n text with parameter substitution.

        The i18n library's built-in parameter substitution doesn't work properly,
        so we do manual string replacement.
        """
        text = i18n.t(key)
        for param_key, param_value in kwargs.items():
            text = text.replace(f"{{{param_key}}}", str(param_value))
        return text

    def _parse_sql_fields(self, sql: str) -> list[str]:
        """从SQL中解析字段名"""
        import sqlparse

        try:
            # 解析SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                logger.warning("[TableInput] SQL parsing returned empty result")
                return []

            stmt = parsed[0]
            fields = []
            in_select = False

            for token in stmt.tokens:
                # 跳过空白和注释
                if token.is_whitespace or isinstance(token, sqlparse.sql.Comment):
                    continue

                # 找到SELECT关键字
                if token.ttype is sqlparse.tokens.Keyword.DML and token.value.upper() == "SELECT":
                    in_select = True
                    continue

                # 遇到FROM等关键字，停止解析
                if in_select and token.ttype is sqlparse.tokens.Keyword:
                    break

                if in_select:
                    # 处理IdentifierList (多个字段，逗号分隔)
                    if isinstance(token, sqlparse.sql.IdentifierList):
                        for identifier in token.get_identifiers():
                            field_name = self._extract_field_name(identifier)
                            if field_name and field_name != "*":
                                fields.append(field_name)
                            elif field_name == "*":
                                return ["*"]  # 特殊标记
                    # 处理单个Identifier
                    elif isinstance(token, sqlparse.sql.Identifier):
                        field_name = self._extract_field_name(token)
                        if field_name:
                            fields.append(field_name)
                    # 处理通配符 *
                    elif token.ttype is sqlparse.tokens.Wildcard:
                        return ["*"]

            logger.debug(f"[TableInput] Parsed fields from SQL: {fields}")
            return fields

        except Exception as e:
            logger.error(f"[TableInput] SQL parsing error: {e}")
            return []

    def _extract_field_name(self, identifier) -> str:
        """提取字段名（处理别名）"""
        try:
            # 如果有别名(AS)，使用别名
            if identifier.has_alias():
                alias = identifier.get_alias()
                logger.debug(f"[TableInput] Field has alias: {alias}")
                return alias

            # 否则使用真实名称
            real_name = identifier.get_real_name()

            # 处理函数调用，如 COUNT(*), MAX(id) 等
            if identifier.ttype is None and "(" in str(identifier):
                # 尝试提取函数表达式作为字段名
                return str(identifier).strip()

            return real_name
        except Exception as e:
            logger.error(f"[TableInput] Error extracting field name: {e}")
            return str(identifier).strip()

    def _get_connection_string(self, datasource_id: str, datasource_info: dict = None) -> str:
        """获取数据源连接字符串，支持内置和公共数据源

        统一使用 datasource_info 构建连接字符串，避免调用API。
        """
        if not datasource_info:
            raise ValueError(f"Missing datasource_info for datasource_id: {datasource_id}")

        source = datasource_info.get("source")
        ds_type = datasource_info.get("type", "").lower()

        logger.info(f"[TableInput] Building connection string for {source} datasource (type={ds_type})")

        # 公共数据源：从 raw_data 构建
        if source == "public":
            raw_data = datasource_info.get("raw_data", {})
            if not raw_data:
                raise ValueError(f"Missing raw_data for public datasource: {datasource_id}")
            return self._build_connection_string_from_datasource_info(datasource_info)

        # 内置数据源：从 datasource_info 直接构建
        if source == "builtin":
            return self._build_connection_string_from_datasource_info(datasource_info)

        # 未知来源
        raise ValueError(f"Unknown datasource source: {source}")

    def _build_connection_string_from_datasource_info(self, datasource_info: dict) -> str:
        """从 datasource_info 构建连接字符串（统一方法）"""
        from urllib.parse import quote_plus

        source = datasource_info.get("source")

        # ✅ 入口日志 - 验证新代码已加载
        logger.info(
            f"[TableInput] _build_connection_string_from_datasource_info ENTRY - "
            f"source={source}, type={datasource_info.get('type')}, "
            f"keys={list(datasource_info.keys())}"
        )

        # 公共数据源：从 raw_data 提取参数
        if source == "public":
            raw_data = datasource_info.get("raw_data", {})
            params = raw_data.get("dataSourceParam", {}) or raw_data.get("parameters", {})

            if not params:
                raise ValueError("[TableInput] No dataSourceParam found in raw_data")

            ds_type = params.get("type", "").lower()

            # ✅ Neo4j特殊处理：从URL提取host/port
            if ds_type == "neo4j":
                url = params.get("url", "")
                username = params.get("username", "")
                password = params.get("password", "")

                if not url:
                    raise ValueError("[TableInput] Missing required 'url' parameter for Neo4j datasource")

                import re

                match = re.match(r"bolt://([^:]+):(\d+)", url)
                if not match:
                    raise ValueError(f"[TableInput] Invalid Neo4j URL format: {url}")

                host = match.group(1)
                port = int(match.group(2))

                username_encoded = quote_plus(username) if username else ""
                password_encoded = quote_plus(password) if password else ""

                if username and password:
                    return f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
                return f"bolt://{host}:{port}"

            # 其他数据源：正常提取host/port
            host = params.get("host")
            port = params.get("port")
            database = params.get("database")
            username = params.get("username")
            password = params.get("password")

        # 内置数据源：直接从 datasource_info 提取
        elif source == "builtin":
            ds_type = datasource_info.get("type", "").lower()

            # ✅ Neo4j特殊处理：内置数据源可能有url或host/port
            if ds_type == "neo4j":
                url = datasource_info.get("url", "")
                username = datasource_info.get("username", "")
                password = datasource_info.get("password", "")

                # 如果有URL，从URL中解析host和port
                if url:
                    import re

                    match = re.match(r"bolt://([^:]+):(\d+)", url)
                    if not match:
                        raise ValueError(f"[TableInput] Invalid Neo4j URL format: {url}")

                    host = match.group(1)
                    port = int(match.group(2))
                else:
                    # 没有URL，尝试使用host和port字段
                    host = datasource_info.get("host")
                    port = datasource_info.get("port")

                    if not host or not port:
                        raise ValueError(
                            f"[TableInput] Neo4j datasource missing both 'url' and 'host/port' fields. "
                            f"Available fields: {list(datasource_info.keys())}"
                        )

                username_encoded = quote_plus(username) if username else ""
                password_encoded = quote_plus(password) if password else ""

                if username and password:
                    return f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
                return f"bolt://{host}:{port}"

            # 其他数据源：正常提取
            host = datasource_info.get("host")
            port = datasource_info.get("port")
            database = datasource_info.get("database")
            username = datasource_info.get("username")
            password = datasource_info.get("password")

        else:
            raise ValueError(f"Unknown source: {source}")

        # 验证必填字段（Neo4j已经在上面处理并返回了）
        if not host or not port:
            # ✅ 详细错误信息，帮助诊断
            logger.error(
                f"[TableInput] VALIDATION FAILED - Missing host/port for {ds_type} datasource. "
                f"source={source}, host={host}, port={port}, "
                f"datasource_info keys: {list(datasource_info.keys())}, "
                f"datasource_info content: {datasource_info}"
            )
            raise ValueError(f"Missing required parameters: host={host}, port={port}")

        # URL编码用户名和密码
        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        # 根据数据库类型构建连接字符串
        if ds_type == "mysql":
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "postgresql":
            return f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "clickhouse":
            return f"clickhouse+connect://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "doris":
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if ds_type == "mongodb":
            return f"mongodb://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        raise ValueError(f"Unsupported datasource type: {ds_type}")

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        # 记录原始数据以便调试
        logger.debug(f"[TableInput] Building connection string from raw_data with keys: {list(raw_data.keys())}")

        # 获取数据源参数
        params = raw_data.get("dataSourceParam", {}) or raw_data.get("parameters", {})
        if not params:
            logger.warning("[TableInput] No dataSourceParam found in raw_data")
            params = {}

        # ✅ 添加详细的调试日志，查看 params 的内容
        logger.debug(
            f"[TableInput] Extracted params keys: {list(params.keys()) if isinstance(params, dict) else 'NOT A DICT'}"
        )
        logger.debug(
            f"[TableInput] Params content: host={params.get('host') if isinstance(params, dict) else 'N/A'}, "
            f"port={params.get('port') if isinstance(params, dict) else 'N/A'}, "
            f"database={params.get('database') if isinstance(params, dict) else 'N/A'}, "
            f"username={params.get('username') if isinstance(params, dict) else 'N/A'}, "
            f"type={params.get('type') if isinstance(params, dict) else 'N/A'}"
        )

        # ✅ 修复：优先从 dataSourceParam.type 获取类型（公共数据源的实际位置）
        ds_type = params.get("type") if isinstance(params, dict) else None

        # 如果 dataSourceParam.type 为空，再尝试其他字段（向后兼容）
        if not ds_type:
            ds_type = (
                raw_data.get("type")
                or raw_data.get("dataSourceType")
                or raw_data.get("dbType")
                or raw_data.get("datasourceType")
                or raw_data.get("databaseType")
            )

        # 记录找到的type值
        logger.debug(
            f"[TableInput] Found type values - dataSourceParam.type: {params.get('type')}, "
            f"type: {raw_data.get('type')}, "
            f"dataSourceType: {raw_data.get('dataSourceType')}, "
            f"dbType: {raw_data.get('dbType')}, "
            f"final: {ds_type}"
        )

        # 如果是空字符串或None，尝试从名称推断
        if not ds_type or (isinstance(ds_type, str) and ds_type.strip() == ""):
            logger.warning(
                f"[TableInput] Public datasource type is empty, raw_data sample: {dict(list(raw_data.items())[:3])}"
            )
            # 尝试从datasource名称推断（作为最后的后备方案）
            ds_name = raw_data.get("name", "").lower()
            if "pg" in ds_name or "postgres" in ds_name:
                ds_type = "postgresql"
                logger.info(f"[TableInput] Inferred type 'postgresql' from name: {ds_name}")
            elif "mysql" in ds_name:
                ds_type = "mysql"
                logger.info(f"[TableInput] Inferred type 'mysql' from name: {ds_name}")
            elif "hive" in ds_name:
                ds_type = "hive"
                logger.info(f"[TableInput] Inferred type 'hive' from name: {ds_name}")
            else:
                # 最后的默认值
                ds_type = "postgresql"
                logger.warning("[TableInput] Cannot infer type, using default: postgresql")

        ds_type = ds_type.lower().strip()
        logger.info(f"[TableInput] Using datasource type: {ds_type}")

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
                f"[TableInput] Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}"
            )
            return conn_str

        # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
        return self._build_connection_string_from_params(ds_type, params)

    def _build_connection_string_from_params(self, ds_type: str, params: dict) -> str:
        """从参数构建连接字符串 - Support MySQL, PostgreSQL, Hive, Neo4j, MongoDB, ClickHouse, Doris"""
        from urllib.parse import quote_plus

        # 调试日志：记录传入的参数
        logger.debug(f"[TableInput] Building connection string for type={ds_type}, params keys={list(params.keys())}")
        logger.debug(
            f"[TableInput] Connection params: host={params.get('host')}, port={params.get('port')}, "
            f"database={params.get('database')}, username={params.get('username')}, url={params.get('url')}"
        )

        # ✅ Neo4j特殊处理：使用URL而不是host/port
        if ds_type == "neo4j":
            url = params.get("url", "")
            username = params.get("username", "")
            password = params.get("password", "")

            if not url:
                raise ValueError(
                    f"[TableInput] Missing required 'url' parameter for Neo4j datasource. "
                    f"Available params: {list(params.keys())}"
                )

            username_encoded = quote_plus(username) if username else ""
            password_encoded = quote_plus(password) if password else ""

            # 从URL中提取host和port（用于连接字符串构建）
            import re

            match = re.match(r"bolt://([^:]+):(\d+)", url)
            if not match:
                raise ValueError(f"[TableInput] Invalid Neo4j URL format: {url}. Expected: bolt://host:port")

            host = match.group(1)
            port = int(match.group(2))

            if username and password:
                conn_str = f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
            else:
                conn_str = f"bolt://{host}:{port}"

            logger.info(f"[TableInput] Built Neo4j connection string: bolt://{username_encoded}:***@{host}:{port}")
            return conn_str

        # ✅ 其他数据源：验证必填字段host和port
        if not params.get("host"):
            raise ValueError(
                f"[TableInput] Missing required 'host' parameter for {ds_type} datasource. "
                f"Available params: {list(params.keys())}"
            )
        if not params.get("port"):
            raise ValueError(
                f"[TableInput] Missing required 'port' parameter for {ds_type} datasource. "
                f"Available params: {list(params.keys())}"
            )

        host = params["host"]
        port = params["port"]
        database = params.get("database", "")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if ds_type == "mysql":
            conn_str = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        elif ds_type == "postgresql":
            conn_str = f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        elif ds_type == "hive":
            # Hive connection - username/password optional
            hive_database = database or "default"
            conn_str = f"hive://{host}:{port}/{hive_database}"
            if username:
                conn_str += f"?auth={username}"
                if password:
                    conn_str += f"&pwd={password_encoded}"
        elif ds_type == "mongodb":
            # MongoDB connection string
            if username and password:
                conn_str = f"mongodb://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
            else:
                conn_str = f"mongodb://{host}:{port}/{database}"
        elif ds_type == "clickhouse":
            # ClickHouse connection using clickhouse-connect driver
            conn_str = f"clickhouse+connect://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        elif ds_type == "doris":
            # Doris connection using MySQL protocol (compatible with MySQL driver)
            conn_str = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        else:
            raise ValueError(f"Unsupported database type: {ds_type}")

        # 调试日志：记录构建的连接字符串（隐藏密码）
        import re

        safe_conn_str = re.sub(r"://([^:]+):([^@]*)@", r"://\1:***@", conn_str)
        logger.info(f"[TableInput] Built connection string for {ds_type}: {safe_conn_str}")

        return conn_str

    def _get_builtin_connection_string(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串 - 使用同步HTTP客户端

        从 update_build_config() 等同步上下文调用此方法。
        使用同步 httpx.Client 避免事件循环冲突。
        """
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            # 提取纯UUID（移除可能的前缀）
            clean_datasource_id = self._extract_uuid_from_id(datasource_id)
            logger.debug(
                f"[TableInput] Getting connection string for builtin datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
            )

            # 使用同步 httpx.Client（不需要事件循环）
            timeout_config = httpx.Timeout(30.0, connect=10.0)
            with httpx.Client(timeout=timeout_config) as client:
                url = f"{api_url}/api/v1/datasources/{clean_datasource_id}/connection-string"
                logger.debug(f"[TableInput] Making sync request to: {url}")

                response = client.get(url)

                if response.status_code != 200:
                    logger.error(f"[TableInput] API request failed. Status: {response.status_code}, URL: {url}")
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError(i18n.t("components.input_output.table_input.errors.connection_string_empty"))

                return connection_string

        except httpx.TimeoutException:
            logger.error(f"[TableInput] Timeout getting connection string for datasource: {datasource_id}")
            raise ValueError("Connection string request timed out")
        except httpx.RequestError as e:
            logger.error(f"[TableInput] Network error getting connection string: {e}")
            raise ValueError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"[TableInput] Error getting builtin connection string: {e}")
            raise

    def _map_dtype(self, dtype) -> str:
        """映射pandas dtype到标准类型"""
        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        if pd.api.types.is_float_dtype(dtype):
            return "float"
        if pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        if pd.api.types.is_object_dtype(dtype):
            return "string"
        return "string"

    def _infer_clickhouse_fields(self, connection_string: str, sql: str, fields: list[str]) -> list[dict]:
        """使用ClickHouse原生驱动推断字段信息"""
        import re
        from urllib.parse import unquote

        import clickhouse_connect

        # Parse ClickHouse connection string
        # Format: clickhouse+connect://username:password@host:port/database
        match = re.match(r"clickhouse\+connect://([^:]+):([^@]*)@([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError("Invalid ClickHouse connection string format")

        username, password, host, port, database = match.groups()
        username = unquote(username)
        password = unquote(password) if password else ""
        port = int(port)

        logger.debug(f"[TableInput] Connecting to ClickHouse: {host}:{port}/{database}")

        # Create ClickHouse client
        client = clickhouse_connect.get_client(
            host=host, port=port, username=username, password=password, database=database
        )

        try:
            # Execute query with LIMIT 1 to get sample data
            logger.debug(f"[TableInput] Executing ClickHouse query with LIMIT 1: {sql[:100]}...")
            result = client.query(f"{sql} LIMIT 1")

            # Get column names and types
            column_names = result.column_names
            column_types = result.column_types

            logger.debug(f"[TableInput] ClickHouse query returned {len(column_names)} columns")

            # If fields is ["*"], use all columns from result
            if fields == ["*"]:
                fields = column_names
                logger.debug(f"[TableInput] Wildcard detected, using columns: {fields}")

            # Map ClickHouse types to standard types
            field_info = []
            for i, field in enumerate(fields):
                if i < len(column_types):
                    ch_type = str(column_types[i]).lower()
                    # Map ClickHouse types to our standard types
                    if "int" in ch_type or "uint" in ch_type:
                        data_type = "integer"
                    elif "float" in ch_type or "decimal" in ch_type:
                        data_type = "float"
                    elif "bool" in ch_type:
                        data_type = "boolean"
                    elif "date" in ch_type or "time" in ch_type:
                        data_type = "datetime"
                    else:
                        data_type = "string"
                else:
                    data_type = "string"

                field_info.append(
                    {
                        "source_field": field,
                        "data_type": data_type,
                        "null_value": "",
                        "transformation_rule": "none",
                    }
                )

            return field_info

        finally:
            client.close()

    def _infer_field_info(self, datasource_id: str, sql: str) -> list[dict]:
        """解析SQL并推断字段信息（执行LIMIT 1查询）"""
        try:
            # 1. 解析SQL字段
            logger.debug(f"[TableInput] Parsing SQL: {sql[:100]}...")
            fields = self._parse_sql_fields(sql)

            if not fields:
                logger.warning("[TableInput] No fields parsed from SQL")
                return []

            # 2. 获取数据库连接
            # 从options_metadata中获取数据源信息
            datasource_info = None
            if hasattr(self, "_current_datasource_info"):
                datasource_info = self._current_datasource_info

            connection_string = self._get_connection_string(datasource_id, datasource_info)

            # Check datasource type for special handling
            is_clickhouse = datasource_info and datasource_info.get("type", "").lower() == "clickhouse"
            is_mongodb = datasource_info and datasource_info.get("type", "").lower() == "mongodb"
            is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"

            logger.debug(
                f"[TableInput] Field inference - datasource type: {datasource_info.get('type') if datasource_info else 'N/A'}, "
                f"is_clickhouse={is_clickhouse}, is_mongodb={is_mongodb}, is_neo4j={is_neo4j}"
            )

            field_info = []

            # Handle ClickHouse using native driver
            if is_clickhouse:
                logger.info("[TableInput] Using ClickHouse native driver for field inference")
                field_info = self._infer_clickhouse_fields(connection_string, sql, fields)
                logger.info(f"[TableInput] Inferred {len(field_info)} fields from ClickHouse")
                return field_info

            # Handle MongoDB - not applicable for SQL inference
            if is_mongodb:
                logger.warning("[TableInput] MongoDB does not support SQL - skipping field inference")
                raise ValueError("MongoDB does not support SQL queries. Please use MongoDB query syntax.")

            # Handle Neo4j - not applicable for SQL inference
            if is_neo4j:
                logger.warning("[TableInput] Neo4j uses Cypher, not SQL - skipping field inference")
                raise ValueError("Neo4j uses Cypher query language, not SQL. Please use Cypher syntax.")

            # For other databases, use SQLAlchemy
            engine = create_engine(connection_string, poolclass=NullPool)

            try:
                with engine.connect() as conn:
                    # 3. 如果是 *, 需要执行查询获取实际列名
                    if fields == ["*"]:
                        logger.debug("[TableInput] Wildcard detected, executing LIMIT 0 to get columns")
                        df = pd.read_sql_query(text(f"{sql} LIMIT 0"), conn)
                        fields = df.columns.tolist()
                        logger.debug(f"[TableInput] Actual columns: {fields}")

                    # 4. 执行 LIMIT 1 获取样本数据，推断类型
                    logger.debug("[TableInput] Executing LIMIT 1 to infer types")
                    df_sample = pd.read_sql_query(text(f"{sql} LIMIT 1"), conn)

                    # 5. 为每个字段创建映射配置
                    for field in fields:
                        if field in df_sample.columns:
                            dtype = df_sample[field].dtype
                            data_type = self._map_dtype(dtype)
                        else:
                            # 字段不在结果中（可能是别名问题），默认string
                            data_type = "string"

                        field_info.append(
                            {
                                "source_field": field,
                                "data_type": data_type,
                                "null_value": "",
                                "transformation_rule": "none",
                            }
                        )

                    logger.info(f"[TableInput] Inferred {len(field_info)} fields")
                    return field_info

            finally:
                engine.dispose()

        except Exception as e:
            logger.error(f"[TableInput] Field inference failed: {e}")
            raise

    def _get_datasource_id(self) -> str:
        """从选中的显示名称获取实际的数据源ID（支持内置和公共数据源）"""
        if not self.datasource_selector:
            raise ValueError(i18n.t("components.input_output.table_input.errors.no_datasource_selected"))

        try:
            # 加载统一的数据源列表
            all_datasources = self._load_unified_datasources()

            # 查找匹配的数据源 - 支持display_name或直接的ID
            for ds in all_datasources:
                # 尝试匹配display_name、id或value
                if (
                    ds["display_name"] == self.datasource_selector
                    or ds["id"] == self.datasource_selector
                    or ds.get("value") == self.datasource_selector
                ):
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
                        # ✅ 包含连接参数，用于本地构建连接字符串
                        "host": ds.get("host"),
                        "port": ds.get("port"),
                        "database": ds.get("database"),
                        "username": ds.get("username"),
                        "password": ds.get("password"),
                        "advanced_config": ds.get("advanced_config"),
                    }

                    logger.debug(
                        f"[TableInput] Found datasource ID '{datasource_id}' ({source}) for '{self.datasource_selector}'"
                    )
                    return datasource_id

            # 如果没找到匹配的显示名称，这通常表示配置有问题
            logger.error(f"[TableInput] Selector value '{self.datasource_selector}' not found in datasource list")
            datasource_list = [f"{ds['display_name']} (ID: {ds['id']})" for ds in all_datasources]
            logger.error(f"[TableInput] Available datasources: {datasource_list}")
            raise ValueError(
                f"Selected datasource '{self.datasource_selector}' is not available. Please refresh the datasource list and select a valid datasource."
            )

        except Exception as e:
            logger.error(f"[TableInput] Error getting datasource ID: {e}")
            raise ValueError(f"Cannot determine datasource ID: {e}")

    def _apply_null_values(self, row_dict: dict) -> dict:
        """应用缺省值填充空值字段"""
        if not self.field_mappings:
            return row_dict

        result = {}

        for mapping in self.field_mappings:
            source_field = mapping.get("source_field")
            null_value = mapping.get("null_value", "")

            if source_field and source_field in row_dict:
                value = row_dict[source_field]

                # 检查是否为空值：None, "", NaN
                is_null = value is None or value == "" or (isinstance(value, float) and pd.isna(value))

                if is_null and null_value:
                    # 使用缺省值
                    result[source_field] = null_value
                    logger.debug(f"[TableInput] Applied null value for '{source_field}': '{null_value}'")
                else:
                    result[source_field] = value
            elif source_field:
                # 字段在映射中但不在数据中
                result[source_field] = row_dict.get(source_field)

        # 保留未映射的字段
        for key, value in row_dict.items():
            if key not in result:
                result[key] = value

        return result

    def _apply_field_transformations(self, row_dict: dict) -> dict:
        if not self.field_mappings:
            return row_dict

        result = {}

        for mapping in self.field_mappings:
            source_field = mapping.get("source_field")
            transformation_rule = mapping.get("transformation_rule", None)

            if source_field and source_field in row_dict:
                value = row_dict[source_field]

                # 应用转换规则
                if transformation_rule and transformation_rule != "none":
                    try:
                        value = self.transformation_executor.apply_transformation(value, transformation_rule, row_dict)
                        logger.debug(f"[TableInput] Applied transformation '{transformation_rule}' to '{source_field}'")
                    except Exception as e:
                        logger.error(f"[TableInput] Transformation failed for '{source_field}': {e}")

                result[source_field] = value

        # 保留未映射的字段
        for key, value in row_dict.items():
            mapped_sources = [m.get("source_field") for m in self.field_mappings]
            if key not in mapped_sources and key not in result:
                result[key] = value

        return result

    async def load_data(self) -> list[Data]:
        """Extract data from database table with SQL support, pagination, and transaction handling."""
        try:
            logger.info("[TableInput] load_data called")
            self.status = i18n.t("components.input_output.table_input.status.connecting")

            # Validate inputs
            if not self.datasource_selector or not self.sql_query:
                logger.warning("[TableInput] Missing datasource or SQL query")
                # In design-time context (e.g., field analysis), return empty sample with schema
                if self.field_mappings:
                    # Use field_mappings to create a sample record
                    sample_data = {
                        mapping.get("source_field"): None
                        for mapping in self.field_mappings
                        if mapping.get("source_field")
                    }
                    if sample_data:
                        logger.info(
                            f"[TableInput] Returning sample record with {len(sample_data)} fields from mappings"
                        )
                        return [Data(data=sample_data)]

                raise ValueError(i18n.t("components.input_output.table_input.errors.missing_config"))

            # 获取实际的数据源ID(从显示名称转换)
            datasource_id = self._get_datasource_id()
            logger.debug(f"[TableInput] Using datasource ID: {datasource_id}")

            # Get connection string (supports both builtin and public datasources)
            try:
                # 使用保存的数据源信息
                datasource_info = getattr(self, "_current_datasource_info", None)

                # ✅ 添加调试日志：显示datasource_info状态
                logger.debug(
                    f"[TableInput] Before get_connection_string - datasource_info is None: {datasource_info is None}"
                )
                if datasource_info:
                    logger.debug(f"[TableInput] datasource_info keys: {list(datasource_info.keys())}")
                    logger.debug(f"[TableInput] datasource_info source: {datasource_info.get('source')}")
                    logger.debug(f"[TableInput] datasource_info type: {datasource_info.get('type')}")

                connection_string = self._get_connection_string(datasource_id, datasource_info)

                # ✅ 添加调试日志：显示连接字符串内容（隐藏密码）
                import re

                safe_conn_str = re.sub(r"://([^:]+):([^@]*)@", r"://\1:***@", connection_string)
                logger.info(f"[TableInput] Built connection string: {safe_conn_str}")
                logger.debug(f"[TableInput] Got connection string for datasource {datasource_id}")

            except Exception as e:
                logger.error(f"[TableInput] Failed to get connection string: {e}")
                # In design-time, if connection fails, use field_mappings as fallback
                if self.field_mappings:
                    sample_data = {
                        mapping.get("source_field"): None
                        for mapping in self.field_mappings
                        if mapping.get("source_field")
                    }
                    if sample_data:
                        logger.info(
                            f"[TableInput] Connection failed, returning sample record with {len(sample_data)} fields from mappings"
                        )
                        return [Data(data=sample_data)]
                raise ValueError(i18n.t("components.input_output.table_input.errors.invalid_datasource")) from e

            # Build SQL query - use as provided by user
            sql_query = self.sql_query.strip()

            # Check datasource type for special handling
            datasource_info = getattr(self, "_current_datasource_info", None)

            # ✅ 添加调试日志：显示 load_data 使用的 datasource_info
            if datasource_info:
                logger.debug(
                    f"[TableInput] load_data using datasource_info: source={datasource_info.get('source')}, "
                    f"type={datasource_info.get('type')}, has_raw_data={bool(datasource_info.get('raw_data'))}"
                )
                if datasource_info.get("source") == "public":
                    if datasource_info.get("raw_data"):
                        raw_data = datasource_info["raw_data"]
                        logger.debug(f"[TableInput] load_data - raw_data keys: {list(raw_data.keys())}")
                        if "dataSourceParam" in raw_data:
                            params = raw_data["dataSourceParam"]
                            logger.debug(
                                f"[TableInput] load_data - params from raw_data: host={params.get('host') if isinstance(params, dict) else 'N/A'}, "
                                f"port={params.get('port') if isinstance(params, dict) else 'N/A'}"
                            )
                    else:
                        logger.warning("[TableInput] load_data - Public datasource but no raw_data!")
            else:
                logger.warning("[TableInput] load_data - No datasource_info available!")

            db_type = datasource_info.get("type", "").lower() if datasource_info else ""

            # Neo4j-specific handling
            if db_type == "neo4j":
                return await self._fetch_neo4j_data(connection_string, sql_query)

            # ClickHouse-specific handling
            if db_type == "clickhouse":
                return await self._fetch_clickhouse_data(datasource_info, sql_query)

            # Doris-specific handling
            if db_type == "doris":
                return await self._fetch_doris_data(datasource_info, sql_query)

            # MongoDB-specific handling
            if db_type == "mongodb":
                return await self._fetch_mongodb_data(datasource_info, sql_query)

            # For SQL databases (MySQL, PostgreSQL, Hive), use SQLAlchemy
            # Create database engine
            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                isolation_level=self.isolation_level if self.isolation_level != "DEFAULT" else None,
            )

            result_data = []
            total_records = 0

            with engine.connect() as connection:
                # Start transaction if enabled
                if self.enable_transaction:
                    trans = connection.begin()
                    try:
                        result_data = self._fetch_data(connection, sql_query)
                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        raise e
                else:
                    result_data = self._fetch_data(connection, sql_query)

            total_records = len(result_data)

            # IMPORTANT: Ensure we return at least one sample record for field inference
            # If no data was returned but query succeeded, create a sample record with NULL values
            if not result_data:
                logger.warning("[TableInput] No data returned from query, creating sample record for field inference")
                # Get schema from LIMIT 1 to create empty sample
                with engine.connect() as connection:
                    df_sample = pd.read_sql_query(text(f"{sql_query} LIMIT 0"), connection)
                    if not df_sample.empty or len(df_sample.columns) > 0:
                        # Create a sample record with None values for all fields
                        sample_data = dict.fromkeys(df_sample.columns)
                        result_data = [Data(data=sample_data)]
                        logger.info(f"[TableInput] Created sample record with {len(sample_data)} fields")

            self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
            logger.info(f"[TableInput] Returning {len(result_data)} data records")

            return result_data

        except Exception as e:
            # Improved error logging
            logger.exception(f"[TableInput] load_data failed with error: {e}")
            error_msg = str(e)

            # Try to use i18n, but fallback to plain error if i18n fails
            try:
                status_msg = i18n.t("components.input_output.table_input.errors.extraction_failed", error=error_msg)
            except Exception:
                status_msg = f"Data extraction failed: {error_msg}"

            self.status = status_msg
            raise ValueError(status_msg) from e

    def _fetch_data(self, connection, sql_query: str) -> list[Data]:
        """Fetch data with pagination support and transformation."""
        result_data = []

        if self.use_pagination:
            offset = 0
            while True:
                # Apply pagination to query
                paginated_query = f"{sql_query} LIMIT {self.page_size} OFFSET {offset}"

                df = pd.read_sql_query(text(paginated_query), connection)

                if df.empty:
                    break

                # ✅ 清理 NaN 和 NaT 值，替换为 None（JSON 可序列化）
                import numpy as np

                df = df.replace({pd.NaT: None, pd.NA: None, np.nan: None, np.inf: None, -np.inf: None})
                df = df.where(pd.notna(df), None)

                # Convert DataFrame to Data objects with transformations
                for _, row in df.iterrows():
                    row_dict = row.to_dict()

                    # 1. 应用缺省值填充
                    if self.field_mappings:
                        row_dict = self._apply_null_values(row_dict)

                    # 2. 应用字段转换规则
                    if self.field_mappings:
                        row_dict = self._apply_field_transformations(row_dict)

                    result_data.append(Data(data=row_dict))

                offset += self.page_size

                # Check max records limit
                if self.max_records > 0 and len(result_data) >= self.max_records:
                    result_data = result_data[: self.max_records]
                    break
        else:
            # Fetch all data at once
            df = pd.read_sql_query(text(sql_query), connection)

            # ✅ 清理 NaN 和 NaT 值，替换为 None（JSON 可序列化）
            import numpy as np

            df = df.replace({pd.NaT: None, pd.NA: None, np.nan: None, np.inf: None, -np.inf: None})
            df = df.where(pd.notna(df), None)

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # 1. 应用缺省值填充
                if self.field_mappings:
                    row_dict = self._apply_null_values(row_dict)

                # 2. 应用字段转换规则
                if self.field_mappings:
                    row_dict = self._apply_field_transformations(row_dict)

                result_data.append(Data(data=row_dict))

                if self.max_records > 0 and len(result_data) >= self.max_records:
                    break

        return result_data

    async def get_row_count(self) -> Data:
        """Get the count of extracted rows."""
        data = await self.load_data()
        count = len(data)
        return Data(data={"row_count": count, "datasource": self.datasource_selector})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the SQL query result.

        This method is designed to be lightweight - it only fetches 1 row to infer schema.
        This is useful for downstream components that need to know field structure
        without loading all data.

        Returns:
            Data: A Data object containing fields metadata with structure:
                  {
                      "fields": [
                          {"name": "field1", "type": "string"},
                          {"name": "field2", "type": "integer"},
                          ...
                      ],
                      "field_names": ["field1", "field2", ...]  # For quick access
                  }
        """
        try:
            logger.info("[TableInput] get_fields_schema called")

            # Reuse existing field_mappings if available (from SQL analysis)
            if self.field_mappings:
                logger.debug(f"[TableInput] Using existing field_mappings: {len(self.field_mappings)} fields")

                fields = [
                    {
                        "name": mapping.get("source_field"),
                        "type": mapping.get("data_type", "string"),
                    }
                    for mapping in self.field_mappings
                    if mapping.get("source_field")
                ]

                field_names = [f["name"] for f in fields]

                logger.info(f"[TableInput] Returning schema with {len(fields)} fields from mappings")
                return Data(data={"fields": fields, "field_names": field_names})

            # If no field_mappings, infer from actual data (fetch LIMIT 1)
            logger.debug("[TableInput] No field_mappings available, inferring from data")

            # Get datasource ID
            datasource_id = self._get_datasource_id()

            # Get connection string (supports both builtin and public datasources)
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)
            engine = create_engine(connection_string, poolclass=NullPool)

            try:
                with engine.connect() as connection:
                    # Execute LIMIT 1 to get schema
                    sql_query = self.sql_query.strip()
                    df_sample = pd.read_sql_query(text(f"{sql_query} LIMIT 1"), connection)

                    fields = []
                    for col in df_sample.columns:
                        dtype = df_sample[col].dtype
                        data_type = self._map_dtype(dtype)
                        fields.append({"name": col, "type": data_type})

                    field_names = [f["name"] for f in fields]

                    logger.info(f"[TableInput] Inferred schema with {len(fields)} fields from data")
                    return Data(data={"fields": fields, "field_names": field_names})

            finally:
                engine.dispose()

        except Exception as e:
            logger.error(f"[TableInput] Failed to get fields schema: {e}")
            # Return empty schema rather than failing
            return Data(data={"fields": [], "field_names": []})

    async def _fetch_neo4j_data(self, connection_string: str, cypher_query: str) -> list[Data]:
        """Fetch data from Neo4j using native driver.

        Args:
            connection_string: Neo4j bolt:// connection string
            cypher_query: Cypher query to execute

        Returns:
            List of Data objects
        """
        import re
        from urllib.parse import unquote

        from neo4j import GraphDatabase

        # Parse bolt URI
        match = re.match(r"bolt://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", connection_string)
        if not match:
            raise ValueError(f"Invalid Neo4j connection string format: {connection_string}")

        username, password, host, port = match.groups()

        # URL decode username and password
        if username:
            username = unquote(username)
        if password:
            password = unquote(password)

        uri = f"bolt://{host}:{port}"

        driver = GraphDatabase.driver(uri, auth=(username, password) if username else None)
        try:
            with driver.session() as session:
                # Execute Cypher query
                result = session.run(cypher_query)
                result_data = []
                for record in result:
                    result_data.append(Data(data=_convert_neo4j_record_to_table_format(record)))
                total_records = len(result_data)
        finally:
            driver.close()

        logger.info(f"[TableInput] Returning {len(result_data)} data records from Neo4j")
        self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
        return result_data

    async def _fetch_clickhouse_data(self, datasource_info: dict, sql_query: str) -> list[Data]:
        """Fetch data from ClickHouse using native driver.

        Args:
            datasource_info: Datasource configuration
            sql_query: SQL query to execute

        Returns:
            List of Data objects
        """
        import clickhouse_connect

        # ✅ 添加调试日志：显示传入的 datasource_info 的完整结构
        logger.debug(
            f"[TableInput] _fetch_clickhouse_data called with datasource_info keys: {list(datasource_info.keys())}"
        )
        logger.debug(f"[TableInput] datasource_info source: {datasource_info.get('source')}")
        logger.debug(f"[TableInput] datasource_info type: {datasource_info.get('type')}")
        logger.debug(f"[TableInput] has raw_data: {bool(datasource_info.get('raw_data'))}")

        # 公共数据源：从 raw_data.dataSourceParam 提取参数
        if datasource_info.get("source") == "public":
            raw_data = datasource_info.get("raw_data", {})
            logger.debug(f"[TableInput] raw_data keys: {list(raw_data.keys()) if raw_data else 'None'}")
            params = raw_data.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 8123)
            database = params.get("database", "default")
            username = params.get("username", "default")
            password = params.get("password", "")
            advanced_config = {}  # 公共数据源的高级配置在 pool 里，不适用于 clickhouse-connect

            logger.debug(
                f"[TableInput] ClickHouse public datasource params: host={host}, port={port}, "
                f"database={database}, username={username}, has_password={bool(password)}"
            )
        else:
            # 内置数据源：直接从 datasource_info 提取
            host = datasource_info.get("host", "localhost")
            port = datasource_info.get("port", 8123)
            database = datasource_info.get("database", "default")
            username = datasource_info.get("username", "default")
            password = datasource_info.get("password", "")
            advanced_config = datasource_info.get("advanced_config", {})

            logger.debug(
                f"[TableInput] ClickHouse builtin datasource params: host={host}, port={port}, "
                f"database={database}, username={username}, has_password={bool(password)}"
            )

        if isinstance(advanced_config, str):
            import json

            advanced_config = json.loads(advanced_config)

        # Build client parameters
        client_params = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        }

        if advanced_config.get("connect_timeout"):
            client_params["connect_timeout"] = advanced_config["connect_timeout"]
        if advanced_config.get("send_receive_timeout"):
            client_params["send_receive_timeout"] = advanced_config["send_receive_timeout"]
        if advanced_config.get("compress"):
            client_params["compress"] = advanced_config["compress"]
        if advanced_config.get("secure"):
            client_params["secure"] = advanced_config["secure"]
        if advanced_config.get("verify"):
            client_params["verify"] = advanced_config["verify"]

        logger.info(
            f"[TableInput] Creating ClickHouse client with params: host={client_params['host']}, "
            f"port={client_params['port']}, database={client_params['database']}, username={client_params['username']}"
        )

        # Create ClickHouse client
        client = clickhouse_connect.get_client(**client_params)

        try:
            # Execute query
            result = client.query(sql_query)

            # Convert to Data objects
            result_data = []
            column_names = result.column_names

            for row in result.result_rows:
                row_dict = dict(zip(column_names, row, strict=False))

                # Apply null values
                if self.field_mappings:
                    row_dict = self._apply_null_values(row_dict)

                # Apply transformations
                if self.field_mappings:
                    row_dict = self._apply_field_transformations(row_dict)

                result_data.append(Data(data=row_dict))

                # Check max records limit
                if self.max_records > 0 and len(result_data) >= self.max_records:
                    break

            total_records = len(result_data)
            logger.info(f"[TableInput] Returning {total_records} data records from ClickHouse")
            self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
            return result_data

        finally:
            client.close()

    async def _fetch_doris_data(self, datasource_info: dict, sql_query: str) -> list[Data]:
        """Fetch data from Apache Doris using pymysql.

        Args:
            datasource_info: Datasource configuration
            sql_query: SQL query to execute

        Returns:
            List of Data objects
        """
        import pymysql

        # 公共数据源：从 raw_data.dataSourceParam 提取参数
        if datasource_info.get("source") == "public":
            raw_data = datasource_info.get("raw_data", {})
            params = raw_data.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 9030)
            database = params.get("database", "")
            username = params.get("username", "root")
            password = params.get("password", "")
            advanced_config = {}  # 公共数据源的高级配置在 pool 里，不适用于 pymysql
        else:
            # 内置数据源：直接从 datasource_info 提取
            host = datasource_info.get("host", "localhost")
            port = datasource_info.get("port", 9030)
            database = datasource_info.get("database", "")
            username = datasource_info.get("username", "root")
            password = datasource_info.get("password", "")
            advanced_config = datasource_info.get("advanced_config", {})

        if isinstance(advanced_config, str):
            import json

            advanced_config = json.loads(advanced_config)

        # Build connection parameters
        conn_params = {
            "host": host,
            "port": port,
            "user": username,
            "password": password,
            "database": database,
            "charset": advanced_config.get("charset", "utf8"),
            "cursorclass": pymysql.cursors.DictCursor,  # Use DictCursor for dict results
        }

        if advanced_config.get("connect_timeout"):
            conn_params["connect_timeout"] = advanced_config["connect_timeout"]
        if advanced_config.get("read_timeout"):
            conn_params["read_timeout"] = advanced_config["read_timeout"]
        if advanced_config.get("write_timeout"):
            conn_params["write_timeout"] = advanced_config["write_timeout"]

        # SSL configuration
        if advanced_config.get("ssl_enabled"):
            conn_params["ssl"] = {"ssl": True}

        # Create Doris connection
        connection = pymysql.connect(**conn_params)

        try:
            with connection.cursor() as cursor:
                # Execute query with pagination if enabled
                if self.use_pagination:
                    result_data = []
                    offset = 0
                    while True:
                        paginated_query = f"{sql_query} LIMIT {self.page_size} OFFSET {offset}"
                        cursor.execute(paginated_query)
                        rows = cursor.fetchall()

                        if not rows:
                            break

                        for row in rows:
                            # Apply null values
                            if self.field_mappings:
                                row = self._apply_null_values(row)

                            # Apply transformations
                            if self.field_mappings:
                                row = self._apply_field_transformations(row)

                            result_data.append(Data(data=row))

                        offset += self.page_size

                        # Check max records limit
                        if self.max_records > 0 and len(result_data) >= self.max_records:
                            result_data = result_data[: self.max_records]
                            break
                else:
                    # Fetch all data at once
                    cursor.execute(sql_query)
                    rows = cursor.fetchall()

                    result_data = []
                    for row in rows:
                        # Apply null values
                        if self.field_mappings:
                            row = self._apply_null_values(row)

                        # Apply transformations
                        if self.field_mappings:
                            row = self._apply_field_transformations(row)

                        result_data.append(Data(data=row))

                        if self.max_records > 0 and len(result_data) >= self.max_records:
                            break

                total_records = len(result_data)
                logger.info(f"[TableInput] Returning {total_records} data records from Doris")
                self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
                return result_data

        finally:
            connection.close()

    async def _fetch_mongodb_data(self, datasource_info: dict, query_json: str) -> list[Data]:
        """Fetch data from MongoDB using pymongo.

        Args:
            datasource_info: Datasource configuration
            query_json: MongoDB query in JSON format (e.g., '{"collection": "users", "filter": {"age": {"$gt": 18}}}')

        Returns:
            List of Data objects
        """
        import json

        from pymongo import MongoClient

        # Parse query JSON
        try:
            query_dict = json.loads(query_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid MongoDB query JSON: {e}") from e

        collection_name = query_dict.get("collection")
        if not collection_name:
            raise ValueError("MongoDB query must specify 'collection' field")

        mongo_filter = query_dict.get("filter", {})
        projection = query_dict.get("projection")
        sort = query_dict.get("sort")
        limit = query_dict.get("limit", max(0, self.max_records))

        # 公共数据源：从 raw_data.dataSourceParam 提取参数
        if datasource_info.get("source") == "public":
            raw_data = datasource_info.get("raw_data", {})
            params = raw_data.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 27017)
            database = params.get("database", "admin")
            username = params.get("username", "")
            password = params.get("password", "")
            advanced_config = {}  # 公共数据源的高级配置在 pool 里，不适用于 pymongo
        else:
            # 内置数据源：直接从 datasource_info 提取
            host = datasource_info.get("host", "localhost")
            port = datasource_info.get("port", 27017)
            database = datasource_info.get("database", "admin")
            username = datasource_info.get("username", "")
            password = datasource_info.get("password", "")
            advanced_config = datasource_info.get("advanced_config", {})

        if isinstance(advanced_config, str):
            advanced_config = json.loads(advanced_config)

        # Build MongoDB connection parameters
        mongo_params = {
            "host": host,
            "port": port,
            "serverSelectionTimeoutMS": advanced_config.get("serverSelectionTimeoutMS", 10000),
            "connectTimeoutMS": advanced_config.get("connectTimeoutMS", 20000),
        }

        if advanced_config.get("maxPoolSize"):
            mongo_params["maxPoolSize"] = advanced_config["maxPoolSize"]
        if advanced_config.get("tls"):
            mongo_params["tls"] = advanced_config["tls"]
        if advanced_config.get("authSource"):
            mongo_params["authSource"] = advanced_config["authSource"]

        # Add authentication if provided
        if username and password:
            mongo_params["username"] = username
            mongo_params["password"] = password

        # Create MongoDB client
        client = MongoClient(**mongo_params)

        try:
            # Access database and collection
            db = client[database]
            collection = db[collection_name]

            # Build find query
            cursor = collection.find(mongo_filter, projection)

            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)

            # Fetch data
            result_data = []
            for doc in cursor:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

                # Apply null values
                if self.field_mappings:
                    doc = self._apply_null_values(doc)

                # Apply transformations
                if self.field_mappings:
                    doc = self._apply_field_transformations(doc)

                result_data.append(Data(data=doc))

            total_records = len(result_data)
            logger.info(f"[TableInput] Returning {total_records} data records from MongoDB")
            self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
            return result_data

        finally:
            client.close()
