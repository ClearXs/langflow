import asyncio
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


def _serialize_neo4j_value(value):
    """Neo4j对象包装函数 - 把复杂对象包装成React可以渲染的简单结构。

    核心原则：保持原始数据结构不变，只是在表格显示时包装成 {"value": ""} 格式。
    """
    # 如果已经是原始类型，包装成 {"value": 原始值}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"value": value}

    # 处理Neo4j特殊对象
    try:
        # 检查是否是Neo4j对象 - 更宽松的检测
        class_name = value.__class__.__name__
        module_name = getattr(value.__class__, "__module__", "")

        # 检查是否是Neo4j对象（通过类名或模块名）
        is_neo4j_object = ("neo4j" in module_name.lower() or
                          class_name in ["Node", "Relationship", "Path", "Record"])

        if is_neo4j_object:
            # Neo4j Node对象
            if (class_name == "Node" or
                (hasattr(value, "labels") and hasattr(value, "properties"))):
                node_data = {
                    "_type": "Node",
                    "labels": list(value.labels) if hasattr(value, "labels") else [],
                    "properties": dict(value.properties) if hasattr(value, "properties") else {}
                }
                if hasattr(value, "element_id"):
                    node_data["_element_id"] = str(value.element_id)
                return {"value": node_data}

            # Neo4j Relationship对象
            if (class_name == "Relationship" or
                  (hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"))):
                rel_data = {
                    "_type": "Relationship",
                    "type": str(value.type) if hasattr(value, "type") else "",
                }
                if hasattr(value, "element_id"):
                    rel_data["_element_id"] = str(value.element_id)
                if hasattr(value, "start_node") and hasattr(value.start_node, "element_id"):
                    rel_data["start_node_id"] = str(value.start_node.element_id)
                if hasattr(value, "end_node") and hasattr(value.end_node, "element_id"):
                    rel_data["end_node_id"] = str(value.end_node.element_id)
                if hasattr(value, "properties"):
                    rel_data["properties"] = dict(value.properties)
                return {"value": rel_data}

            # 其他Neo4j对象，提取所有可用属性
            neo4j_data = {"_type": class_name}
            for attr in dir(value):
                if not attr.startswith("_") and not callable(getattr(value, attr)):
                    try:
                        attr_value = getattr(value, attr)
                        if isinstance(attr_value, (str, int, float, bool, list, dict)) or attr_value is None:
                            if isinstance(attr_value, frozenset):
                                neo4j_data[attr] = list(attr_value)
                            else:
                                neo4j_data[attr] = attr_value
                    except Exception:
                        continue
            return {"value": neo4j_data}

        # 普通复牚对象（字典、列表等），直接JSON序列化
        import json
        json_str = json.dumps(value, ensure_ascii=False)
        # 限制长度避免UI问题
        if len(json_str) > 500:
            json_str = json_str[:500] + "..."
        return {"value": json_str}

    except (TypeError, ValueError, AttributeError):
        # 如果JSON序列化失败，用字符串表示
        try:
            str_value = str(value)
            if len(str_value) > 500:
                str_value = str_value[:500] + "..."
            return {"value": str_value}
        except Exception:
            return {"value": f"<{value.__class__.__name__} object>"}


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

                for ds in all_datasources:
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
                logger.debug(f"[TableInput] Set datasource_selector options: {options}")
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
                    if metadata.get("display_name") == current_datasource:
                        datasource_info = metadata
                        break

                # 如果在 options_metadata 中找不到，尝试重新加载数据源列表
                if not datasource_info:
                    logger.warning("[TableInput] Datasource info not found in options_metadata, reloading datasources")
                    all_datasources = self._load_unified_datasources()
                    for ds in all_datasources:
                        if ds["display_name"] == current_datasource:
                            datasource_info = {
                                "id": ds["id"],
                                "name": ds["name"],
                                "type": ds["type"],
                                "source": ds["source"],
                                "display_name": ds["display_name"],
                                "raw_data": ds.get("raw_data"),
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

                # 如果在 options_metadata 中找不到，尝试重新加载数据源列表
                if not datasource_info:
                    logger.warning(
                        "[TableInput] Datasource info not found in options_metadata for preview, reloading datasources"
                    )
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
                            }
                            break

                # 保存数据源信息供后续使用
                self._current_datasource_info = datasource_info

                # 添加调试日志
                if datasource_info:
                    logger.debug(
                        f"[TableInput] Found datasource info: type={datasource_info.get('type')}, "
                        f"name={datasource_info.get('name')}, id={datasource_info.get('id')}"
                    )
                else:
                    logger.warning("[TableInput] datasource_info is None!")

                connection_string = self._get_connection_string(datasource_id, datasource_info)

                # Check if this is a Neo4j datasource
                is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"
                logger.debug(
                    f"[TableInput] is_neo4j={is_neo4j}, datasource type={datasource_info.get('type') if datasource_info else 'N/A'}"
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
                public_datasources = asyncio.run(self._get_public_datasources())
            except Exception as e:
                logger.warning(f"[TableInput] Failed to get public datasources: {e}")
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
                # ✅ 修复：从 dataSourceParam.type 获取正确的类型
                params = ds.get("dataSourceParam", {})
                ds_type = params.get("type") if isinstance(params, dict) else None
                if not ds_type:
                    ds_type = (
                        ds.get("type")
                        or ds.get("dataSourceType")
                        or ds.get("dbType")
                        or "mysql"
                    )

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
        """获取内置数据源"""
        try:
            datasources = asyncio.run(self.datasource_manager.get_datasources())
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

            return builtin_datasources

        except Exception as e:
            logger.error(f"[TableInput] Error getting builtin datasources: {e}")
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

        return {
            "type": ds_type.lower(),
            "database": database,
            "host": host,
            "port": port
        }

    def _get_default_port(self, ds_type: str) -> int:
        """获取数据源的默认端口"""
        default_ports = {
            "mysql": 3306,
            "postgresql": 5432,
            "hive": 10000,
            "neo4j": 7687,
            "oracle": 1521,
            "sqlserver": 1433
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
        """获取数据源连接字符串，支持内置和公共数据源"""
        if datasource_info and datasource_info.get("source") == "public":
            # 公共数据源：从raw_data构建连接字符串
            return self._build_public_connection_string(datasource_info["raw_data"])
        # 内置数据源：使用现有逻辑
        return self._get_builtin_connection_string(datasource_id)

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        # 记录原始数据以便调试
        logger.debug(f"[TableInput] Building connection string from raw_data with keys: {list(raw_data.keys())}")

        # 获取数据源参数
        params = raw_data.get("dataSourceParam", {}) or raw_data.get("parameters", {})
        if not params:
            logger.warning("[TableInput] No dataSourceParam found in raw_data")
            params = {}

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

            logger.debug(f"[TableInput] Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}")
            return conn_str

        # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
        return self._build_connection_string_from_params(ds_type, params)

    def _build_connection_string_from_params(self, ds_type: str, params: dict) -> str:
        """从参数构建连接字符串 - Only support MySQL, PostgreSQL, Hive, Neo4j"""
        from urllib.parse import quote_plus

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
            # Hive connection - username/password optional
            hive_port = port if port != 3306 else 10000
            hive_database = database or "default"
            conn_str = f"hive://{host}:{hive_port}/{hive_database}"
            if username:
                conn_str += f"?auth={username}"
                if password:
                    conn_str += f"&pwd={password_encoded}"
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
                f"[TableInput] Getting connection string for builtin datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
            )
            logger.debug(f"[TableInput] Using API URL: {api_url}")

            with httpx.Client(timeout=10.0) as client:
                url = f"{api_url}/api/v1/datasources/{clean_datasource_id}/connection-string"
                logger.debug(f"[TableInput] Making request to: {url}")

                response = client.get(url)

                if response.status_code != 200:
                    # 增强错误记录，包含响应内容
                    try:
                        error_content = response.text
                        logger.error(f"[TableInput] API request failed. Status: {response.status_code}, URL: {url}")
                        logger.error(f"[TableInput] Response content: {error_content}")
                    except Exception:
                        logger.error(f"[TableInput] API request failed. Status: {response.status_code}, URL: {url}")

                    # 根据状态码提供更具体的错误信息
                    if response.status_code == 422:
                        raise ValueError(
                            f"Invalid datasource ID '{datasource_id}' or datasource configuration. Status: {response.status_code}"
                        )
                    if response.status_code == 404:
                        raise ValueError(
                            f"Datasource with ID '{datasource_id}' not found. Status: {response.status_code}"
                        )
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    logger.error(f"[TableInput] Empty connection string in response: {connection_data}")
                    raise ValueError(i18n.t("components.input_output.table_input.errors.connection_string_empty"))

                logger.debug(f"[TableInput] Successfully retrieved connection string for datasource: {datasource_id}")
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
            engine = create_engine(connection_string, poolclass=NullPool)

            field_info = []

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
                if (ds["display_name"] == self.datasource_selector or
                    ds["id"] == self.datasource_selector or
                    ds.get("value") == self.datasource_selector):

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

    def load_data(self) -> list[Data]:
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
                connection_string = self._get_connection_string(datasource_id, datasource_info)
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

            # Check if this is a Neo4j datasource
            datasource_info = getattr(self, "_current_datasource_info", None)
            is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"

            if is_neo4j:
                # Neo4j-specific handling
                import re
                from urllib.parse import unquote

                from neo4j import GraphDatabase

                # Parse bolt URI
                match = re.match(r"bolt://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", connection_string)
                if not match:
                    raise ValueError(f"Invalid Neo4j connection string format: {connection_string}")

                username, password, host, port = match.groups()

                # URL decode username and password (they are URL-encoded in the connection string)
                if username:
                    username = unquote(username)
                if password:
                    password = unquote(password)

                uri = f"bolt://{host}:{port}"

                driver = GraphDatabase.driver(uri, auth=(username, password) if username else None)
                try:
                    with driver.session() as session:
                        # Execute Cypher query
                        result = session.run(sql_query)
                        result_data = []
                        for record in result:
                            result_data.append(Data(data=_convert_neo4j_record_to_table_format(record)))
                        total_records = len(result_data)
                finally:
                    driver.close()

                logger.info(f"[TableInput] Returning {len(result_data)} data records from Neo4j")
                self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
                return result_data

            # For SQL databases, use SQLAlchemy
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

    def get_row_count(self) -> Data:
        """Get the count of extracted rows."""
        data = self.load_data()
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
