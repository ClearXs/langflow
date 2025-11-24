"""SQL Script Component for executing SQL statements on selected datasource."""

import asyncio
import re
import threading
from typing import Any
from urllib.parse import unquote

import i18n
import pandas as pd
import sqlparse
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, MessageTextInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# ==================== 专用事件循环线程（用于同步上下文中调用异步HTTP请求） ====================
# 创建独立的事件循环，避免与主事件循环冲突
_http_loop = asyncio.new_event_loop()
_http_thread = threading.Thread(target=_http_loop.run_forever, name="SQLScriptAsyncHTTPRunner", daemon=True)
_http_thread.start()
logger.info("[SQLScript] Started dedicated event loop thread for async HTTP requests")


# Neo4j数据序列化函数 (复制自table_input.py)
def _serialize_neo4j_value(value):
    """Neo4j对象包装函数 - 把复杂对象包装成可序列化的结构。"""
    # 如果已经是原始类型，包装成 {"value": 原始值}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"value": value}

    # 处理Neo4j特殊对象
    try:
        # 检查是否是Neo4j对象
        class_name = value.__class__.__name__
        module_name = getattr(value.__class__, "__module__", "")

        is_neo4j_object = "neo4j" in module_name.lower() or class_name in [
            "Node",
            "Relationship",
            "Path",
            "Record",
        ]

        if is_neo4j_object:
            # Neo4j Node对象
            if class_name == "Node" or (hasattr(value, "labels") and hasattr(value, "properties")):
                node_data = {
                    "_type": "Node",
                    "labels": list(value.labels) if hasattr(value, "labels") else [],
                    "properties": dict(value.items()) if hasattr(value, "items") else {},
                }
                if hasattr(value, "element_id"):
                    node_data["_element_id"] = str(value.element_id)
                return {"value": node_data}

            # Neo4j Relationship对象
            if class_name == "Relationship" or (
                hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node")
            ):
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
                if hasattr(value, "items"):
                    rel_data["properties"] = dict(value.items())
                return {"value": rel_data}

            # 其他Neo4j对象
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

        # 普通复杂对象，JSON序列化
        import json

        json_str = json.dumps(value, ensure_ascii=False)
        if len(json_str) > 500:
            json_str = json_str[:500] + "..."
        return {"value": json_str}

    except (TypeError, ValueError, AttributeError):
        try:
            str_value = str(value)
            if len(str_value) > 500:
                str_value = str_value[:500] + "..."
            return {"value": str_value}
        except Exception:
            return {"value": f"<{value.__class__.__name__} object>"}


def _convert_neo4j_record_to_dict(record):
    """Convert a Neo4j Record to a flat dictionary with serializable values."""
    logger.debug(f"[SQLScript] Converting Neo4j record with keys: {record.keys()}")
    result = {}
    for key in record.keys():
        try:
            value = record[key]
            serialized_value = _serialize_neo4j_value(value)
            result[key] = serialized_value
        except Exception as e:
            error_msg = f"<Error: {e!s}>"
            logger.error(f"[SQLScript] Error serializing field '{key}': {error_msg}")
            result[key] = error_msg

    return result


class ETLSQLScriptComponent(Component):
    """Execute SQL scripts on selected datasource with transaction support."""

    display_name = i18n.t("components.scripts.sql_script.display_name")
    description = i18n.t("components.scripts.sql_script.description")
    icon = "database"
    name = "ETLSQLScript"
    include_universal_input = True

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.scripts.sql_script.datasource_selector.display_name"),
            info=i18n.t("components.scripts.sql_script.datasource_selector.info"),
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
            name="sql_script",
            display_name=i18n.t("components.scripts.sql_script.sql_script.display_name"),
            info=i18n.t("components.scripts.sql_script.sql_script.info"),
            required=True,
            placeholder="-- SQL Script\nCREATE TABLE ...\nINSERT INTO ...\nSELECT * FROM ...",
            advanced=False,
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t("components.scripts.sql_script.enable_transaction.display_name"),
            info=i18n.t("components.scripts.sql_script.enable_transaction.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="statement_separator",
            display_name=i18n.t("components.scripts.sql_script.statement_separator.display_name"),
            info=i18n.t("components.scripts.sql_script.statement_separator.info"),
            value=";",
            advanced=True,
        ),
        BoolInput(
            name="continue_on_error",
            display_name=i18n.t("components.scripts.sql_script.continue_on_error.display_name"),
            info=i18n.t("components.scripts.sql_script.continue_on_error.info"),
            value=False,
            advanced=True,
        ),
        TableInput(
            name="execution_results",
            display_name=i18n.t("components.scripts.sql_script.execution_results.display_name"),
            info=i18n.t("components.scripts.sql_script.execution_results.info"),
            table_schema=[
                {
                    "name": "statement_index",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.statement_index"),
                    "type": "int",
                    "disable_edit": True,
                },
                {
                    "name": "statement_type",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.statement_type"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "rows_affected",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.rows_affected"),
                    "type": "int",
                    "disable_edit": True,
                },
                {
                    "name": "execution_status",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.status"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "error_message",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.error"),
                    "type": "str",
                    "disable_edit": True,
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "execute_script",
                        "label": i18n.t("components.scripts.sql_script.execution_results.execute_button"),
                        "icon": "Play",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="execution_summary",
            display_name=i18n.t("components.scripts.sql_script.outputs.execution_summary"),
            method="execute_sql_script",
            types=["Data"],  # Returns Data object with execution summary
        ),
        Output(
            name="query_results",
            display_name=i18n.t("components.scripts.sql_script.outputs.query_results"),
            method="get_query_results",
            types=["Data"],  # Returns Data object with query results
        ),
        Output(
            name="total_rows_affected",
            display_name=i18n.t("components.scripts.sql_script.outputs.total_rows_affected"),
            method="get_total_rows_affected",
            types=["Data"],  # Returns Data object with row count
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
            f"[SQLScript] update_build_config called - field_name: {field_name}, "
            f"field_value type: {type(field_value).__name__}, action: {action}"
        )

        import os

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        # Load datasources on initial load or refresh
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"[SQLScript] Loading datasources (field_name={field_name})")
            try:
                # 加载统一的数据源列表（内置 + 公共）
                all_datasources = self._load_unified_datasources()

                # 构建显示选项和元数据
                options = []
                options_metadata = []

                # SQL Script 排除 Kafka（Kafka 不支持 SQL）
                excluded_types = {"kafka"}

                for ds in all_datasources:
                    # 过滤：排除 Kafka
                    ds_type = ds.get("type", "").lower()
                    if ds_type in excluded_types:
                        logger.debug(f"[SQLScript] Skipping excluded datasource type: {ds_type} (name={ds['name']})")
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
                logger.debug(f"[SQLScript] Set datasource_selector options: {options} (excluded Kafka)")
                logger.debug(f"[SQLScript] Set options_metadata with {len(options_metadata)} entries")

            except Exception as e:
                logger.error(f"[SQLScript] Error loading unified datasources: {e}")
                # 设置错误选项
                build_config["datasource_selector"]["options"] = ["加载失败"]
                build_config["datasource_selector"]["options_metadata"] = []

        # Handle execute script button click
        if field_name == "execution_results" and action == "execute_script":
            logger.info("[SQLScript] Execute script triggered by action button")

            try:
                current_sql = build_config.get("sql_script", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("[SQLScript] No SQL script provided")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_script")
                    return build_config

                if not current_datasource:
                    logger.warning("[SQLScript] No datasource selected")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_datasource")
                    return build_config

                # Get datasource ID from metadata
                datasource_id = self._get_datasource_id_from_metadata(
                    current_datasource, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if not datasource_id:
                    logger.error(f"[SQLScript] Cannot find datasource ID for: {current_datasource}")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_datasource")
                    return build_config

                # Get datasource info for connection string building
                datasource_info = self._get_datasource_info_from_metadata(
                    datasource_id, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                # Execute the script
                logger.info("[SQLScript] Starting script execution...")
                self.status = i18n.t("components.scripts.sql_script.status.connecting")

                # Get other configuration values
                enable_transaction = build_config.get("enable_transaction", {}).get("value", True)
                continue_on_error = build_config.get("continue_on_error", {}).get("value", False)
                statement_separator = build_config.get("statement_separator", {}).get("value", ";")

                # Execute script and get results
                results = self._execute_script_preview(
                    datasource_id=datasource_id,
                    sql_script=current_sql,
                    enable_transaction=enable_transaction,
                    continue_on_error=continue_on_error,
                    statement_separator=statement_separator,
                    datasource_info=datasource_info,
                )

                # Update execution results table
                build_config["execution_results"]["value"] = results

                success_count = sum(1 for r in results if r["execution_status"] == "success")
                total_count = len(results)

                self.status = self._format_i18n(
                    "components.scripts.sql_script.status.success", success=success_count, total=total_count
                )
                logger.info(f"[SQLScript] Script execution completed: {success_count}/{total_count} successful")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[SQLScript] Script execution failed: {error_msg}")
                self.status = self._format_i18n(
                    "components.scripts.sql_script.errors.execution_failed", error=error_msg
                )

        return build_config

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
                logger.debug(f"[SQLScript] Found valid datasource ID: '{selector_value}'")
                return selector_value

        # 向后兼容：尝试从旧的 "ID|||显示名称" 格式中提取ID
        if "|||" in selector_value:
            datasource_id = selector_value.split("|||")[0]
            logger.warning(f"[SQLScript] Legacy format detected, extracted ID '{datasource_id}' from selector value")
            return datasource_id

        # 再向后兼容：按显示名称查找
        logger.warning(f"[SQLScript] Trying legacy lookup by display name for: '{selector_value}'")
        for metadata in options_metadata:
            meta_display_name = f"{metadata.get('name')} ({metadata.get('type')})"
            if meta_display_name == selector_value or metadata.get("display_name") == selector_value:
                datasource_id = metadata.get("id")
                logger.debug(f"[SQLScript] Found datasource ID '{datasource_id}' for display name '{selector_value}'")
                return datasource_id

        logger.warning(f"[SQLScript] No metadata found for selector value: {selector_value}")
        return None

    def _get_datasource_info_from_metadata(self, datasource_id: str, options_metadata: list[dict]) -> dict | None:
        """从 options_metadata 中根据数据源ID获取完整的数据源信息

        Args:
            datasource_id: 数据源ID
            options_metadata: 元数据列表

        Returns:
            数据源信息字典，如果未找到则返回None
        """
        for metadata in options_metadata:
            if metadata.get("id") == datasource_id or metadata.get("value") == datasource_id:
                logger.debug(f"[SQLScript] Found datasource info for ID: '{datasource_id}'")
                return metadata

        logger.warning(f"[SQLScript] No datasource info found for ID: {datasource_id}")
        return None

    def _format_i18n(self, key: str, **kwargs) -> str:
        """Format i18n text with parameter substitution."""
        text = i18n.t(key)
        for param_key, param_value in kwargs.items():
            text = text.replace(f"{{{param_key}}}", str(param_value))
        return text

    def _load_unified_datasources(self) -> list[dict]:
        """加载统一的数据源列表（内置数据源 + 公共数据源）"""
        try:
            # 获取内置数据源
            builtin_datasources = self._get_builtin_datasources()

            # 获取公共数据源
            try:
                public_datasources = asyncio.run(self._get_public_datasources())
            except Exception as e:
                logger.warning(f"[SQLScript] Failed to get public datasources: {e}")
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
                        "database": ds.get("database"),
                        "host": ds.get("host"),
                        "port": ds.get("port"),
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
                f"[SQLScript] Loaded {len(all_datasources)} datasources ({len(builtin_datasources)} builtin, {len(public_datasources)} public)"
            )
            return all_datasources

        except Exception as e:
            logger.error(f"[SQLScript] Error loading unified datasources: {e}")
            return []

    def _get_builtin_datasources(self) -> list[dict]:
        """获取内置数据源"""
        try:
            import os

            import httpx

            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources")

                if response.status_code == 200:
                    datasources = response.json()
                    logger.debug(f"[SQLScript] Loaded {len(datasources)} builtin datasources from API")

                    builtin_datasources = []
                    for ds in datasources:
                        builtin_datasources.append(
                            {
                                "id": str(ds["id"]),
                                "name": ds["name"],
                                "type": ds["type"],
                                "source": "builtin",
                                "database": ds.get("database"),
                                "host": ds.get("host"),
                                "port": ds.get("port"),
                            }
                        )
                    return builtin_datasources
                logger.warning(f"[SQLScript] Failed to load builtin datasources, status: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"[SQLScript] Error getting builtin datasources: {e}")
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

            logger.info(f"[SQLScript] Got {len(datasource_list)} public datasources from feign API")
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[SQLScript] Error getting public datasources: {e}")
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
            "mongodb": 27017,
            "clickhouse": 8123,
            "doris": 9030,
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

            # 描述信息
            if raw_data.get("description"):
                extra_labels.append(f"[{raw_data['description']}]")

        # 组合显示名称
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

    async def _get_builtin_connection_string_async(self, datasource_id: str) -> str:
        """Get connection string for builtin datasource - 异步版本（使用 httpx.AsyncClient）"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{api_url}/api/v1/datasources/{datasource_id}/connection-string"
                logger.debug(f"[SQLScript] Making async request to: {url}")

                response = await client.get(url)

                if response.status_code != 200:
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError(i18n.t("components.scripts.sql_script.errors.connection_string_empty"))

                logger.debug(f"[SQLScript] Successfully retrieved connection string for datasource: {datasource_id}")
                return connection_string
        except httpx.TimeoutException:
            logger.error(f"[SQLScript] Timeout getting connection string for datasource: {datasource_id}")
            raise ValueError("Connection string request timed out")
        except httpx.RequestError as e:
            logger.error(f"[SQLScript] Network error getting connection string: {e}")
            raise ValueError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"[SQLScript] Error getting builtin connection string: {e}")
            raise

    def _get_builtin_connection_string(self, datasource_id: str) -> str:
        """Get connection string for builtin datasource - 同步包装器

        从同步上下文调用此方法（如 update_build_config、execute_script）。
        使用专用事件循环线程运行异步请求，避免与主事件循环冲突。
        """
        logger.debug(f"[SQLScript] Using dedicated event loop thread for datasource {datasource_id}")

        # 在专用事件循环中调度协程
        future = asyncio.run_coroutine_threadsafe(self._get_builtin_connection_string_async(datasource_id), _http_loop)

        try:
            return future.result(timeout=15)  # 15秒超时（比内部的10秒多一些缓冲）
        except Exception as e:
            logger.error(f"[SQLScript] Error getting connection string for datasource {datasource_id}: {e}")
            raise ValueError(f"Connection string request failed: {e}")

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        # 记录原始数据以便调试
        logger.debug(f"[SQLScript] Building connection string from raw_data with keys: {list(raw_data.keys())}")

        # 获取数据源参数 - 修复：从正确的位置获取参数
        params = raw_data.get("dataSourceParam", {})
        if not params:
            logger.warning(f"[SQLScript] No dataSourceParam found in raw_data, available keys: {list(raw_data.keys())}")
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
            f"[SQLScript] Found type values - dataSourceParam.type: {params.get('type')}, "
            f"type: {raw_data.get('type')}, "
            f"dataSourceType: {raw_data.get('dataSourceType')}, "
            f"dbType: {raw_data.get('dbType')}, "
            f"final: {ds_type}"
        )

        # 如果是空字符串或None，尝试从名称推断
        if not ds_type or (isinstance(ds_type, str) and ds_type.strip() == ""):
            logger.warning(
                f"[SQLScript] Public datasource type is empty, raw_data sample: {dict(list(raw_data.items())[:3])}"
            )
            # 尝试从datasource名称推断（作为最后的后备方案）
            ds_name = raw_data.get("name", "").lower()
            if "pg" in ds_name or "postgres" in ds_name:
                ds_type = "postgresql"
                logger.info(f"[SQLScript] Inferred type 'postgresql' from name: {ds_name}")
            elif "mysql" in ds_name:
                ds_type = "mysql"
                logger.info(f"[SQLScript] Inferred type 'mysql' from name: {ds_name}")
            elif "hive" in ds_name:
                ds_type = "hive"
                logger.info(f"[SQLScript] Inferred type 'hive' from name: {ds_name}")
            elif "neo4j" in ds_name:
                ds_type = "neo4j"
                logger.info(f"[SQLScript] Inferred type 'neo4j' from name: {ds_name}")
            else:
                logger.warning(f"[SQLScript] Cannot infer datasource type from name: {ds_name}")
                ds_type = "unknown"

        ds_type = ds_type.lower() if ds_type else "unknown"
        logger.debug(f"[SQLScript] Using datasource type: {ds_type}")

        # 根据数据源类型构建连接字符串
        if ds_type == "postgresql" or ds_type == "postgres":
            return self._build_postgres_connection_string(params)
        if ds_type == "mysql":
            return self._build_mysql_connection_string(params)
        if ds_type == "hive":
            return self._build_hive_connection_string(params)
        if ds_type == "neo4j":
            return self._build_neo4j_connection_string(params)
        if ds_type == "mongodb":
            return self._build_mongodb_connection_string(params)
        if ds_type == "clickhouse":
            return self._build_clickhouse_connection_string(params)
        if ds_type == "doris":
            return self._build_doris_connection_string(params)
        raise ValueError(f"Unsupported public datasource type: {ds_type}")

    def _build_postgres_connection_string(self, params: dict) -> str:
        """构建PostgreSQL连接字符串"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 5432)
        database = params.get("database", "postgres")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        connection_string = f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        logger.debug(f"[SQLScript] Built PostgreSQL connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _build_mysql_connection_string(self, params: dict) -> str:
        """构建MySQL连接字符串"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 3306)
        database = params.get("database", "mysql")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        connection_string = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        logger.debug(f"[SQLScript] Built MySQL connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _build_hive_connection_string(self, params: dict) -> str:
        """构建Hive连接字符串 - 使用 SQLAlchemy 格式，不是 JDBC 格式"""
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
            f"[SQLScript] Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}"
        )
        return conn_str

    def _build_neo4j_connection_string(self, params: dict) -> str:
        """构建Neo4j连接字符串"""
        from urllib.parse import quote_plus

        # ✅ 修复：优先使用URL中的连接信息
        url = params.get("url", "")
        if url and url.startswith("bolt://"):
            # 从URL解析连接信息：bolt://host:port
            import re

            match = re.match(r"bolt://([^:]+):(\d+)", url)
            if match:
                host = match.group(1)
                port = int(match.group(2))
                logger.debug(f"[SQLScript] Using Neo4j host:port from URL: {host}:{port}")
            else:
                # URL格式不符合预期，使用默认值
                host = params.get("host", "localhost")
                port = params.get("port", 7687)
                logger.warning(f"[SQLScript] Invalid Neo4j URL format: {url}, using host: {host}, port: {port}")
        else:
            # 回退到参数中的host和port
            host = params.get("host", "localhost")
            port = params.get("port", 7687)
            logger.debug(f"[SQLScript] Using Neo4j host:port from params: {host}:{port}")

        username = params.get("username", "")
        password = params.get("password", "")

        # Neo4j bolt连接字符串
        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        connection_string = f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
        logger.debug(f"[SQLScript] Built Neo4j connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _build_mongodb_connection_string(self, params: dict) -> str:
        """构建MongoDB连接字符串"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 27017)
        database = params.get("database", "admin")
        username = params.get("username", "")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if username and password:
            connection_string = f"mongodb://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        else:
            connection_string = f"mongodb://{host}:{port}/{database}"

        logger.debug(f"[SQLScript] Built MongoDB connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _build_clickhouse_connection_string(self, params: dict) -> str:
        """构建ClickHouse连接字符串 - 使用 clickhouse-connect 驱动"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 8123)
        database = params.get("database", "default")
        username = params.get("username", "default")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        connection_string = f"clickhouse+connect://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        logger.debug(f"[SQLScript] Built ClickHouse connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _build_doris_connection_string(self, params: dict) -> str:
        """构建Apache Doris连接字符串 - 使用 MySQL 协议 (pymysql)"""
        from urllib.parse import quote_plus

        host = params.get("host", "localhost")
        port = params.get("port", 9030)
        database = params.get("database", "")
        username = params.get("username", "root")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        connection_string = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        logger.debug(f"[SQLScript] Built Doris connection string: {connection_string.replace(password, '***')}")
        return connection_string

    def _parse_sql_statements(self, sql_script: str, separator: str = ";") -> list[str]:
        """Parse SQL script into individual statements.

        Args:
            sql_script: The SQL script to parse
            separator: Statement separator (default: semicolon)

        Returns:
            List of SQL statements
        """
        try:
            # Use sqlparse to properly handle SQL
            parsed = sqlparse.parse(sql_script)
            statements = []

            for statement in parsed:
                # Remove comments and whitespace
                sql = statement.value.strip()
                if sql and not sql.startswith("--"):
                    statements.append(sql)

            logger.debug(f"[SQLScript] Parsed {len(statements)} statements from script")
            return statements

        except Exception as e:
            logger.error(f"[SQLScript] Failed to parse SQL script: {e}")
            raise ValueError(self._format_i18n("components.scripts.sql_script.errors.parse_failed", error=str(e)))

    def _classify_statement_type(self, statement: str) -> str:
        """Classify SQL statement type.

        Args:
            statement: SQL statement

        Returns:
            Statement type: DDL, DML, DQL, or OTHER
        """
        statement_upper = statement.strip().upper()

        # DDL statements
        if any(statement_upper.startswith(kw) for kw in ["CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"]):
            return "DDL"

        # DML statements
        if any(statement_upper.startswith(kw) for kw in ["INSERT", "UPDATE", "DELETE", "MERGE"]):
            return "DML"

        # DQL statements
        if statement_upper.startswith("SELECT"):
            return "DQL"

        # Other (e.g., SET, USE, etc.)
        return "OTHER"

    def _execute_single_statement(
        self, connection, statement: str, index: int, total: int
    ) -> dict[str, str | int | list]:
        """Execute a single SQL statement.

        Args:
            connection: Database connection
            statement: SQL statement to execute
            index: Statement index (1-based)
            total: Total number of statements

        Returns:
            Execution result dictionary with query_data for SELECT statements
        """
        try:
            stmt_type = self._classify_statement_type(statement)
            logger.debug(f"[SQLScript] Executing statement {index}/{total} ({stmt_type}): {statement[:50]}...")

            self.status = self._format_i18n("components.scripts.sql_script.status.executing", index=index, total=total)

            result = connection.execute(text(statement))

            # Get rows affected
            rows_affected = result.rowcount if hasattr(result, "rowcount") else 0

            # For SELECT queries, fetch the actual data
            query_data = []
            if stmt_type == "DQL":
                try:
                    # Fetch all rows from SELECT query
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())

                    # ✅ 清理 NaN 和 NaT 值，替换为 None（JSON 可序列化）
                    import numpy as np

                    df = df.replace({pd.NaT: None, pd.NA: None, np.nan: None, np.inf: None, -np.inf: None})
                    df = df.where(pd.notna(df), None)  # 将所有 NaN 替换为 None

                    query_data = df.to_dict("records")  # Convert to list of dicts
                    logger.debug(f"[SQLScript] Fetched {len(query_data)} rows from SELECT query (NaN/NaT cleaned)")
                except Exception as fetch_error:
                    logger.warning(f"[SQLScript] Could not fetch query results: {fetch_error}")
                    query_data = []

            return {
                "statement_index": index,
                "statement_type": stmt_type,
                "rows_affected": rows_affected,
                "execution_status": "success",
                "error_message": "",
                "query_data": query_data,  # Add query results
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[SQLScript] Statement {index} failed: {error_msg}")

            return {
                "statement_index": index,
                "statement_type": self._classify_statement_type(statement),
                "rows_affected": 0,
                "execution_status": "failed",
                "error_message": error_msg,
                "query_data": [],
            }

    def _execute_script_preview(
        self,
        datasource_id: str,
        sql_script: str,
        enable_transaction: bool,
        continue_on_error: bool,
        statement_separator: str,
        datasource_info: dict = None,
    ) -> list[dict]:
        """Execute SQL script and return results for preview.

        This is called during configuration to preview execution results.
        """
        try:
            # Resolve variables in SQL script using base Component method
            import asyncio

            resolved_sql = asyncio.run(self.resolve_variables_in_template(sql_script, "sql_script"))
            logger.debug(f"[SQLScript] SQL after variable resolution (preview): {resolved_sql[:100]}...")

            # Parse statements
            self.status = i18n.t("components.scripts.sql_script.status.parsing")
            statements = self._parse_sql_statements(resolved_sql, statement_separator)

            if not statements:
                logger.warning("[SQLScript] No statements to execute")
                return []

            # Get connection
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            # 获取数据源信息以检测类型
            datasource_info = getattr(self, "_current_datasource_info", None)
            is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"
            is_mongodb = datasource_info and datasource_info.get("type", "").lower() == "mongodb"
            is_clickhouse = datasource_info and datasource_info.get("type", "").lower() == "clickhouse"

            logger.debug(
                f"[SQLScript] Datasource type: {datasource_info.get('type') if datasource_info else 'unknown'}, "
                f"is_neo4j={is_neo4j}, is_mongodb={is_mongodb}, is_clickhouse={is_clickhouse}"
            )

            if is_neo4j:
                # 使用Neo4j驱动执行Cypher
                logger.info("[SQLScript] Detected Neo4j datasource, using Neo4j driver")
                results = self._execute_neo4j_script(connection_string, statements, enable_transaction)
                return results

            if is_mongodb:
                # 使用pymongo驱动执行MongoDB命令
                logger.info("[SQLScript] Detected MongoDB datasource, using pymongo driver")
                results = self._execute_mongodb_script(connection_string, statements, enable_transaction)
                return results

            if is_clickhouse:
                # 使用clickhouse-connect驱动执行ClickHouse查询
                logger.info("[SQLScript] Detected ClickHouse datasource, using clickhouse-connect driver")
                results = self._execute_clickhouse_script(connection_string, statements, enable_transaction)
                return results

            # 原有的SQLAlchemy逻辑
            engine = create_engine(connection_string, poolclass=NullPool)

            results = []

            try:
                with engine.connect() as connection:
                    # Start transaction if enabled
                    if enable_transaction:
                        trans = connection.begin()

                    try:
                        # Execute each statement
                        for idx, statement in enumerate(statements, start=1):
                            result = self._execute_single_statement(connection, statement, idx, len(statements))
                            results.append(result)

                            # If error and not continuing, break
                            if result["execution_status"] == "failed" and not continue_on_error:
                                if enable_transaction:
                                    trans.rollback()
                                    logger.info("[SQLScript] Transaction rolled back due to error")
                                break

                        # Commit transaction if all successful
                        if enable_transaction:
                            if all(r["execution_status"] == "success" for r in results):
                                trans.commit()
                                logger.info("[SQLScript] Transaction committed successfully")
                            else:
                                trans.rollback()
                                logger.info("[SQLScript] Transaction rolled back due to errors")

                    except Exception as e:
                        if enable_transaction:
                            trans.rollback()
                        logger.error(f"[SQLScript] Script execution failed: {e}")
                        raise

            finally:
                engine.dispose()

            return results

        except Exception as e:
            logger.error(f"[SQLScript] Preview execution failed: {e}")
            raise

    def _get_datasource_id(self) -> str:
        """Get datasource ID from selected display name."""
        if not self.datasource_selector:
            raise ValueError(i18n.t("components.scripts.sql_script.errors.no_datasource_selected"))

        # 尝试从统一的数据源列表中查找
        try:
            all_datasources = self._load_unified_datasources()
            for ds in all_datasources:
                if ds["id"] == self.datasource_selector or ds["display_name"] == self.datasource_selector:
                    # 保存数据源信息供后续使用
                    self._current_datasource_info = {
                        "id": ds["id"],
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": ds["source"],
                        "display_name": ds["display_name"],
                        "raw_data": ds.get("raw_data"),
                    }

                    logger.debug(
                        f"[SQLScript] Found datasource ID '{ds['id']}' for '{self.datasource_selector}', "
                        f"type={ds['type']}, source={ds['source']}"
                    )
                    return ds["id"]

            logger.warning(
                f"[SQLScript] Datasource '{self.datasource_selector}' not found in unified list, trying legacy method"
            )
        except Exception as e:
            logger.warning(f"[SQLScript] Failed to load unified datasources: {e}, falling back to legacy method")

        # 回退到原有的逻辑（只适用于内置数据源）
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources")
                if response.status_code == 200:
                    datasources = response.json()

                    for ds in datasources:
                        display_name = f"{ds['name']} ({ds['type']})"
                        if display_name == self.datasource_selector:
                            datasource_id = ds["id"]

                            # 保存数据源信息供后续使用
                            self._current_datasource_info = {
                                "id": datasource_id,
                                "name": ds["name"],
                                "type": ds["type"],
                                "source": "builtin",
                                "display_name": display_name,
                            }

                            logger.debug(
                                f"[SQLScript] Found datasource ID '{datasource_id}' for '{self.datasource_selector}', "
                                f"type={ds['type']} (legacy)"
                            )
                            return datasource_id

                    logger.warning(
                        f"[SQLScript] Display name '{self.datasource_selector}' not found, trying as direct ID"
                    )
                    return self.datasource_selector

                logger.error(f"[SQLScript] Failed to load datasources from API, status: {response.status_code}")
                raise ValueError(f"Failed to load datasources: HTTP {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"[SQLScript] HTTP error when fetching datasources: {e}")
            raise ValueError(f"Failed to fetch datasources: {e}")

        except Exception as e:
            logger.error(f"[SQLScript] Unexpected error: {e}")
            raise ValueError(f"Cannot determine datasource ID: {e}")

    def execute_sql_script(self) -> Data:
        """Execute SQL script on selected datasource.

        Returns:
            Execution summary with all statement results
        """
        try:
            logger.info("[SQLScript] execute_sql_script called")
            self.status = i18n.t("components.scripts.sql_script.status.connecting")

            # Validate inputs
            if not self.datasource_selector or not self.sql_script:
                logger.warning("[SQLScript] Missing datasource or SQL script")
                raise ValueError(i18n.t("components.scripts.sql_script.errors.no_datasource"))

            # Resolve variables in SQL script using base Component method
            import asyncio

            resolved_sql = asyncio.run(self.resolve_variables_in_template(self.sql_script, "sql_script"))
            logger.debug(f"[SQLScript] SQL after variable resolution: {resolved_sql[:100]}...")

            # Get datasource ID
            datasource_id = self._get_datasource_id()
            logger.debug(f"[SQLScript] Using datasource ID: {datasource_id}")

            # Parse statements
            self.status = i18n.t("components.scripts.sql_script.status.parsing")
            statements = self._parse_sql_statements(resolved_sql, self.statement_separator)

            if not statements:
                logger.warning("[SQLScript] No statements to execute")
                return Data(
                    data={
                        "total_statements": 0,
                        "successful_statements": 0,
                        "failed_statements": 0,
                        "total_rows_affected": 0,
                        "results": [],
                    }
                )

            # Get connection
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            # 获取数据源信息以检测类型
            datasource_info = getattr(self, "_current_datasource_info", None)
            is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"
            is_mongodb = datasource_info and datasource_info.get("type", "").lower() == "mongodb"
            is_clickhouse = datasource_info and datasource_info.get("type", "").lower() == "clickhouse"

            logger.debug(
                f"[SQLScript] Datasource type: {datasource_info.get('type') if datasource_info else 'unknown'}, "
                f"is_neo4j={is_neo4j}, is_mongodb={is_mongodb}, is_clickhouse={is_clickhouse}"
            )

            if is_neo4j:
                # 使用Neo4j驱动执行Cypher
                logger.info("[SQLScript] Detected Neo4j datasource, using Neo4j driver")
                results = self._execute_neo4j_script(connection_string, statements, self.enable_transaction)

                # 构建summary
                successful_count = sum(1 for r in results if r["execution_status"] == "success")
                failed_count = len(results) - successful_count
                total_rows_affected = sum(r["rows_affected"] for r in results)

                summary_data = {
                    "total_statements": len(statements),
                    "successful_statements": successful_count,
                    "failed_statements": failed_count,
                    "total_rows_affected": total_rows_affected,
                    "results": results,
                }

                self.status = i18n.t("components.scripts.sql_script.status.completed", count=len(statements))
                logger.info(f"[SQLScript] Execution complete: {successful_count} success, {failed_count} failed")
                return Data(data=summary_data)

            if is_mongodb:
                # 使用pymongo驱动执行MongoDB命令
                logger.info("[SQLScript] Detected MongoDB datasource, using pymongo driver")
                results = self._execute_mongodb_script(connection_string, statements, self.enable_transaction)

                # 构建summary
                successful_count = sum(1 for r in results if r["execution_status"] == "success")
                failed_count = len(results) - successful_count
                total_rows_affected = sum(r["rows_affected"] for r in results)

                summary_data = {
                    "total_statements": len(statements),
                    "successful_statements": successful_count,
                    "failed_statements": failed_count,
                    "total_rows_affected": total_rows_affected,
                    "results": results,
                }

                self.status = i18n.t("components.scripts.sql_script.status.completed", count=len(statements))
                logger.info(f"[SQLScript] Execution complete: {successful_count} success, {failed_count} failed")
                return Data(data=summary_data)

            if is_clickhouse:
                # 使用clickhouse-connect驱动执行ClickHouse查询
                logger.info("[SQLScript] Detected ClickHouse datasource, using clickhouse-connect driver")
                results = self._execute_clickhouse_script(connection_string, statements, self.enable_transaction)

                # 构建summary
                successful_count = sum(1 for r in results if r["execution_status"] == "success")
                failed_count = len(results) - successful_count
                total_rows_affected = sum(r["rows_affected"] for r in results)

                summary_data = {
                    "total_statements": len(statements),
                    "successful_statements": successful_count,
                    "failed_statements": failed_count,
                    "total_rows_affected": total_rows_affected,
                    "results": results,
                }

                self.status = i18n.t("components.scripts.sql_script.status.completed", count=len(statements))
                logger.info(f"[SQLScript] Execution complete: {successful_count} success, {failed_count} failed")
                return Data(data=summary_data)

            # 原有的SQLAlchemy逻辑
            engine = create_engine(connection_string, poolclass=NullPool)

            results = []
            total_rows_affected = 0

            try:
                with engine.connect() as connection:
                    # Start transaction if enabled
                    if self.enable_transaction:
                        trans = connection.begin()

                    try:
                        # Execute each statement
                        for idx, statement in enumerate(statements, start=1):
                            result = self._execute_single_statement(connection, statement, idx, len(statements))
                            results.append(result)

                            if result["execution_status"] == "success":
                                total_rows_affected += result["rows_affected"]

                            # If error and not continuing, break
                            if result["execution_status"] == "failed" and not self.continue_on_error:
                                if self.enable_transaction:
                                    trans.rollback()
                                    logger.info("[SQLScript] Transaction rolled back due to error")
                                break

                        # Commit transaction if enabled and all successful
                        if self.enable_transaction:
                            if all(r["execution_status"] == "success" for r in results):
                                self.status = i18n.t("components.scripts.sql_script.status.committing")
                                trans.commit()
                                logger.info("[SQLScript] Transaction committed successfully")
                            else:
                                trans.rollback()
                                logger.info("[SQLScript] Transaction rolled back due to errors")

                    except Exception as e:
                        if self.enable_transaction:
                            trans.rollback()
                        raise e

            finally:
                engine.dispose()

            # Build summary
            successful_count = sum(1 for r in results if r["execution_status"] == "success")
            failed_count = len(results) - successful_count

            summary_data = {
                "total_statements": len(statements),
                "successful_statements": successful_count,
                "failed_statements": failed_count,
                "total_rows_affected": total_rows_affected,
                "results": results,
            }

            self.status = self._format_i18n(
                "components.scripts.sql_script.status.success", success=successful_count, total=len(statements)
            )
            logger.info(f"[SQLScript] Execution completed: {successful_count}/{len(statements)} successful")

            return Data(data=summary_data)

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[SQLScript] execute_sql_script failed: {error_msg}")

            try:
                status_msg = i18n.t("components.scripts.sql_script.errors.execution_failed", error=error_msg)
            except Exception:
                status_msg = f"Script execution failed: {error_msg}"

            self.status = status_msg
            raise ValueError(status_msg) from e

    def get_total_rows_affected(self) -> Data:
        """Get total rows affected by the script execution.

        Returns:
            Data object with total rows affected count
        """
        try:
            summary = self.execute_sql_script()
            total_rows = summary.data.get("total_rows_affected", 0)

            return Data(data={"total_rows_affected": total_rows})

        except Exception as e:
            logger.error(f"[SQLScript] Failed to get total rows affected: {e}")
            return Data(data={"total_rows_affected": 0, "error": str(e)})

    def get_query_results(self) -> list[Data]:
        """Get query results from SELECT statements.

        Returns:
            List of Data objects containing query results from all SELECT statements
        """
        try:
            logger.info("[SQLScript] get_query_results called")
            summary = self.execute_sql_script()

            # Extract query data from all successful DQL statements
            all_query_data = []
            results = summary.data.get("results", [])

            for result in results:
                if result.get("statement_type") == "DQL" and result.get("execution_status") == "success":
                    query_data = result.get("query_data", [])
                    # Convert each row dict to a Data object
                    for row_dict in query_data:
                        all_query_data.append(Data(data=row_dict))

                    logger.debug(
                        f"[SQLScript] Statement {result.get('statement_index')}: "
                        f"Added {len(query_data)} rows to query results"
                    )

            logger.info(f"[SQLScript] Returning {len(all_query_data)} total query result rows")
            return all_query_data

        except Exception as e:
            logger.error(f"[SQLScript] Failed to get query results: {e}")
            return []

    def _execute_neo4j_script(
        self, connection_string: str, statements: list[str], enable_transaction: bool
    ) -> list[dict]:
        """执行Neo4j Cypher脚本"""
        from neo4j import GraphDatabase

        # 解析bolt连接字符串
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

        results = []
        try:
            with driver.session() as session:
                if enable_transaction:
                    tx = session.begin_transaction()
                    try:
                        for idx, stmt in enumerate(statements, 1):
                            result = self._execute_neo4j_statement(tx, stmt, idx, len(statements))
                            results.append(result)
                            if result["execution_status"] == "failed" and not self.continue_on_error:
                                tx.rollback()
                                break
                        else:
                            tx.commit()
                    except Exception:
                        tx.rollback()
                        raise
                else:
                    for idx, stmt in enumerate(statements, 1):
                        result = self._execute_neo4j_statement(session, stmt, idx, len(statements))
                        results.append(result)
                        if result["execution_status"] == "failed" and not self.continue_on_error:
                            break
        finally:
            driver.close()

        return results

    def _execute_neo4j_statement(self, session_or_tx, statement: str, index: int, total: int) -> dict:
        """执行单条Cypher语句"""
        try:
            stmt_type = self._classify_neo4j_statement(statement)
            logger.debug(f"[SQLScript] Executing Neo4j statement {index}/{total} ({stmt_type})")

            result = session_or_tx.run(statement)

            # 对于查询语句，获取数据
            query_data = []
            rows_affected = 0

            if stmt_type == "DQL":
                for record in result:
                    query_data.append(_convert_neo4j_record_to_dict(record))
                rows_affected = len(query_data)
            else:
                summary = result.consume()
                rows_affected = (
                    summary.counters.nodes_created
                    + summary.counters.relationships_created
                    + summary.counters.properties_set
                )

            return {
                "statement_index": index,
                "statement_type": stmt_type,
                "rows_affected": rows_affected,
                "execution_status": "success",
                "error_message": "",
                "query_data": query_data,
            }
        except Exception as e:
            logger.error(f"[SQLScript] Neo4j statement {index} failed: {e}")
            return {
                "statement_index": index,
                "statement_type": self._classify_neo4j_statement(statement),
                "rows_affected": 0,
                "execution_status": "failed",
                "error_message": str(e),
                "query_data": [],
            }

    def _classify_neo4j_statement(self, statement: str) -> str:
        """分类Cypher语句类型"""
        stmt_upper = statement.strip().upper()

        if stmt_upper.startswith(("MATCH", "RETURN", "WITH", "UNWIND")):
            return "DQL"  # 查询
        if stmt_upper.startswith(("CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DETACH")):
            return "DML"  # 数据操作
        if stmt_upper.startswith(("CREATE CONSTRAINT", "DROP CONSTRAINT", "CREATE INDEX", "DROP INDEX")):
            return "DDL"  # Schema操作
        return "OTHER"

    def _execute_mongodb_script(
        self, connection_string: str, statements: list[str], enable_transaction: bool
    ) -> list[dict]:
        """执行MongoDB脚本"""
        # 解析MongoDB连接字符串
        # Format: mongodb://[username:password@]host:port/database
        import re

        from pymongo import MongoClient

        match = re.match(r"mongodb://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError(f"Invalid MongoDB connection string: {connection_string}")

        username, password, host, port, database = match.groups()
        if username:
            username = unquote(username)
        if password:
            password = unquote(password)

        # 构建连接参数
        mongo_params = {
            "host": host,
            "port": int(port),
        }
        if username and password:
            mongo_params["username"] = username
            mongo_params["password"] = password

        client = MongoClient(**mongo_params)

        results = []
        try:
            db = client[database]

            # MongoDB不支持传统事务（仅在副本集/分片集群中支持），这里简化处理
            for idx, stmt in enumerate(statements, 1):
                result = self._execute_mongodb_statement(db, stmt, idx, len(statements))
                results.append(result)
                if result["execution_status"] == "failed" and not self.continue_on_error:
                    break
        finally:
            client.close()

        return results

    def _execute_mongodb_statement(self, db, statement: str, index: int, total: int) -> dict:
        """执行单条MongoDB命令

        支持的MongoDB命令格式:
        1. JSON格式查询: {"collection": "users", "operation": "find", "filter": {"age": {"$gt": 18}}}
        2. JSON格式插入: {"collection": "users", "operation": "insertOne", "document": {"name": "John", "age": 30}}
        3. JSON格式更新: {"collection": "users", "operation": "updateMany", "filter": {}, "update": {"$set": {"status": "active"}}}
        4. JSON格式删除: {"collection": "users", "operation": "deleteMany", "filter": {"age": {"$lt": 18}}}
        5. 聚合查询: {"collection": "users", "operation": "aggregate", "pipeline": [{"$match": {"age": {"$gt": 18}}}, {"$group": {"_id": "$city", "count": {"$sum": 1}}}]}
        """
        try:
            import json

            stmt_type = self._classify_mongodb_statement(statement)
            logger.debug(f"[SQLScript] Executing MongoDB statement {index}/{total} ({stmt_type})")

            # 解析 JSON 格式的 MongoDB 命令
            try:
                cmd = json.loads(statement)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for MongoDB command: {e}") from e

            collection_name = cmd.get("collection")
            if not collection_name:
                raise ValueError("MongoDB command must specify 'collection' field")

            operation = cmd.get("operation", "find")
            collection = db[collection_name]

            query_data = []
            rows_affected = 0

            # 执行不同的操作
            if operation == "find":
                # 查询操作
                mongo_filter = cmd.get("filter", {})
                projection = cmd.get("projection")
                sort = cmd.get("sort")
                limit = cmd.get("limit", 1000)

                cursor = collection.find(mongo_filter, projection)
                if sort:
                    cursor = cursor.sort(list(sort.items()))
                cursor = cursor.limit(limit)

                # 转换为可序列化的格式
                for doc in cursor:
                    # 转换 ObjectId 为字符串
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                    query_data.append(doc)
                rows_affected = len(query_data)

            elif operation == "insertOne":
                # 插入单个文档
                document = cmd.get("document", {})
                result = collection.insert_one(document)
                rows_affected = 1 if result.inserted_id else 0

            elif operation == "insertMany":
                # 插入多个文档
                documents = cmd.get("documents", [])
                result = collection.insert_many(documents)
                rows_affected = len(result.inserted_ids)

            elif operation == "updateOne":
                # 更新单个文档
                mongo_filter = cmd.get("filter", {})
                update = cmd.get("update", {})
                result = collection.update_one(mongo_filter, update)
                rows_affected = result.modified_count

            elif operation == "updateMany":
                # 更新多个文档
                mongo_filter = cmd.get("filter", {})
                update = cmd.get("update", {})
                result = collection.update_many(mongo_filter, update)
                rows_affected = result.modified_count

            elif operation == "replaceOne":
                # 替换单个文档
                mongo_filter = cmd.get("filter", {})
                replacement = cmd.get("replacement", {})
                result = collection.replace_one(mongo_filter, replacement)
                rows_affected = result.modified_count

            elif operation == "deleteOne":
                # 删除单个文档
                mongo_filter = cmd.get("filter", {})
                result = collection.delete_one(mongo_filter)
                rows_affected = result.deleted_count

            elif operation == "deleteMany":
                # 删除多个文档
                mongo_filter = cmd.get("filter", {})
                result = collection.delete_many(mongo_filter)
                rows_affected = result.deleted_count

            elif operation == "aggregate":
                # 聚合查询
                pipeline = cmd.get("pipeline", [])
                cursor = collection.aggregate(pipeline)
                for doc in cursor:
                    # 转换 ObjectId 为字符串
                    if "_id" in doc and hasattr(doc["_id"], "__str__"):
                        doc["_id"] = str(doc["_id"])
                    query_data.append(doc)
                rows_affected = len(query_data)

            elif operation == "countDocuments":
                # 计数文档
                mongo_filter = cmd.get("filter", {})
                count = collection.count_documents(mongo_filter)
                rows_affected = count
                query_data = [{"count": count}]

            else:
                raise ValueError(f"Unsupported MongoDB operation: {operation}")

            return {
                "statement_index": index,
                "statement_type": stmt_type,
                "rows_affected": rows_affected,
                "execution_status": "success",
                "error_message": "",
                "query_data": query_data,
            }
        except Exception as e:
            logger.error(f"[SQLScript] MongoDB statement {index} failed: {e}")
            return {
                "statement_index": index,
                "statement_type": self._classify_mongodb_statement(statement),
                "rows_affected": 0,
                "execution_status": "failed",
                "error_message": str(e),
                "query_data": [],
            }

    def _classify_mongodb_statement(self, statement: str) -> str:
        """分类MongoDB语句类型"""
        try:
            import json

            cmd = json.loads(statement.strip())
            operation = cmd.get("operation", "find")

            # 查询操作
            if operation in ["find", "aggregate", "countDocuments"]:
                return "DQL"
            # 数据操作
            if operation in [
                "insertOne",
                "insertMany",
                "updateOne",
                "updateMany",
                "replaceOne",
                "deleteOne",
                "deleteMany",
            ]:
                return "DML"
            # Schema操作
            if operation in ["createCollection", "dropCollection", "createIndex", "dropIndex"]:
                return "DDL"
            return "OTHER"
        except (json.JSONDecodeError, KeyError):
            # 如果不是有效的JSON或缺少operation字段，尝试从文本判断
            stmt = statement.strip().lower()
            if "find" in stmt or "aggregate" in stmt:
                return "DQL"
            if "insert" in stmt or "update" in stmt or "delete" in stmt or "replace" in stmt:
                return "DML"
            if "createcollection" in stmt or "dropcollection" in stmt or "createindex" in stmt:
                return "DDL"
            return "OTHER"

    def _execute_clickhouse_script(
        self, connection_string: str, statements: list[str], enable_transaction: bool
    ) -> list[dict]:
        """执行ClickHouse脚本"""
        import clickhouse_connect

        # 解析ClickHouse连接字符串
        # Format: clickhouse+connect://username:password@host:port/database
        # 密码可以为空：clickhouse+connect://username:@host:port/database
        match = re.match(r"clickhouse\+connect://([^:]+):([^@]*)@([^:]+):(\d+)/(.+)", connection_string)
        if not match:
            raise ValueError(f"Invalid ClickHouse connection string: {connection_string}")

        username, password, host, port, database = match.groups()
        username = unquote(username)
        password = unquote(password) if password else ""  # 空密码处理

        # 创建ClickHouse客户端
        client = clickhouse_connect.get_client(
            host=host, port=int(port), username=username, password=password, database=database
        )

        results = []
        try:
            # ClickHouse不支持传统ACID事务，这里简化处理
            for idx, stmt in enumerate(statements, 1):
                result = self._execute_clickhouse_statement(client, stmt, idx, len(statements))
                results.append(result)
                if result["execution_status"] == "failed" and not self.continue_on_error:
                    break
        finally:
            client.close()

        return results

    def _execute_clickhouse_statement(self, client, statement: str, index: int, total: int) -> dict:
        """执行单条ClickHouse语句"""
        try:
            stmt_type = self._classify_statement_type(statement)  # 使用通用SQL分类
            logger.debug(f"[SQLScript] Executing ClickHouse statement {index}/{total} ({stmt_type})")

            # 执行查询
            result = client.query(statement)

            query_data = []
            rows_affected = 0

            if stmt_type == "DQL":
                # SELECT查询 - 获取结果数据
                if result.result_rows:
                    # 转换为字典列表
                    column_names = result.column_names
                    for row in result.result_rows:
                        row_dict = dict(zip(column_names, row, strict=False))
                        query_data.append(row_dict)
                    rows_affected = len(query_data)
            else:
                # DML/DDL - 获取影响行数
                rows_affected = result.summary.get("written_rows", 0) if hasattr(result, "summary") else 0

            return {
                "statement_index": index,
                "statement_type": stmt_type,
                "rows_affected": rows_affected,
                "execution_status": "success",
                "error_message": "",
                "query_data": query_data,
            }
        except Exception as e:
            logger.error(f"[SQLScript] ClickHouse statement {index} failed: {e}")
            return {
                "statement_index": index,
                "statement_type": self._classify_statement_type(statement),
                "rows_affected": 0,
                "execution_status": "failed",
                "error_message": str(e),
                "query_data": [],
            }
