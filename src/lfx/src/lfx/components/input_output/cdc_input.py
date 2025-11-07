import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any

import i18n

from lfx.base.datasource.manager import DataSourceManager
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.streaming import streaming_component


@streaming_component
class ETLCDCStreamInputComponent(Component):
    display_name = i18n.t("components.input_output.cdc_input.display_name")
    description = i18n.t("components.input_output.cdc_input.description")
    icon = "database"
    name = "ETLCDCStreamInput"
    is_streaming_component = True
    include_universal_input = True  # Enable universal input for CDC Input

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_manager = DataSourceManager()
        self._should_stop = False
        # 添加运行时时间戳跟踪
        self._current_last_sync = None  # 跟踪当前实际使用的同步时间

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.cdc_input.datasource_selector.display_name"),
            info=i18n.t("components.input_output.cdc_input.datasource_selector.info"),
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
        DropdownInput(
            name="table_selector",
            display_name=i18n.t("components.input_output.cdc_input.table_selector.display_name"),
            info=i18n.t("components.input_output.cdc_input.table_selector.info"),
            required=True,
            refresh_button=True,
            options=[],  # Will be loaded dynamically based on selected datasource
            real_time_refresh=True,
        ),
        DropdownInput(
            name="cdc_mode",
            display_name=i18n.t("components.input_output.cdc_input.cdc_mode.display_name"),
            info=i18n.t("components.input_output.cdc_input.cdc_mode.info"),
            options=[
                i18n.t("components.input_output.cdc_input.cdc_mode.timestamp"),
                i18n.t("components.input_output.cdc_input.cdc_mode.log_based"),
                i18n.t("components.input_output.cdc_input.cdc_mode.trigger_based"),
            ],
            value=i18n.t("components.input_output.cdc_input.cdc_mode.timestamp"),
        ),
        MessageTextInput(
            name="timestamp_column",
            display_name=i18n.t("components.input_output.cdc_input.timestamp_column.display_name"),
            info=i18n.t("components.input_output.cdc_input.timestamp_column.info"),
            value="updated_at",
            advanced=True,
        ),
        MessageTextInput(
            name="last_sync_time",
            display_name=i18n.t("components.input_output.cdc_input.last_sync_time.display_name"),
            info=i18n.t("components.input_output.cdc_input.last_sync_time.info"),
            placeholder="2024-01-01 00:00:00",
            advanced=True,
        ),
        IntInput(
            name="poll_interval_seconds",
            display_name=i18n.t("components.input_output.cdc_input.poll_interval_seconds.display_name"),
            info=i18n.t("components.input_output.cdc_input.poll_interval_seconds.info"),
            value=5,
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.cdc_input.batch_size.display_name"),
            info=i18n.t("components.input_output.cdc_input.batch_size.info"),
            value=1000,
            advanced=True,
        ),
        BoolInput(
            name="capture_deletes",
            display_name=i18n.t("components.input_output.cdc_input.capture_deletes.display_name"),
            info=i18n.t("components.input_output.cdc_input.capture_deletes.info"),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_change_type",
            display_name=i18n.t("components.input_output.cdc_input.include_change_type.display_name"),
            info=i18n.t("components.input_output.cdc_input.include_change_type.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="primary_keys",
            display_name=i18n.t("components.input_output.cdc_input.primary_keys.display_name"),
            info=i18n.t("components.input_output.cdc_input.primary_keys.info"),
            placeholder="id,uuid",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.cdc_input.outputs.data.display_name"),
            method="capture_changes",
            types=["Data"],
        ),
        Output(
            name="change_summary",
            display_name=i18n.t("components.input_output.cdc_input.outputs.change_summary.display_name"),
            method="get_change_summary",
            types=["Data"],
        ),
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """动态配置更新 - 加载数据源和表列表.

        Args:
            build_config: 当前构建配置
            field_value: 字段值
            field_name: 字段名称
            action: 操作名称
        """
        logger.info(
            f"[CDCInput] update_build_config called - field_name: {field_name}, "
            f"field_value: {field_value}, action: {action}"
        )

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        # 初始加载或刷新数据源选择器
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"[CDCInput] Loading unified datasources (field_name={field_name}, field_value={field_value})")
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
                logger.debug(f"[CDCInput] Set unified datasource_selector options: {options}")
                logger.debug(f"[CDCInput] Set options_metadata with {len(options_metadata)} entries")

            except Exception as e:
                logger.error(f"[CDCInput] Error loading unified datasources: {e}")
                # 设置错误选项
                build_config["datasource_selector"]["options"] = ["加载失败"]
                build_config["datasource_selector"]["options_metadata"] = []

        # 当数据源被选中时，加载该数据源的表列表
        if field_name == "datasource_selector" and field_value:
            logger.debug(f"[CDCInput] Datasource selected: {field_value}")

            try:
                # 从 options_metadata 中获取数据源ID
                datasource_id = self._get_datasource_id_from_metadata(
                    field_value, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if datasource_id:
                    # 获取数据源信息以判断是否为公共数据源
                    datasource_info = None
                    options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                    for metadata in options_metadata:
                        # 使用 value 或 id 字段匹配，而不是 display_name
                        if metadata.get("value") == field_value or metadata.get("id") == field_value:
                            datasource_info = metadata
                            break

                    # 公共数据源：使用新的表加载接口
                    if datasource_info and datasource_info.get("source") == "public":
                        logger.info(f"[CDCInput] Loading tables for public datasource: {field_value}")
                        try:
                            tables = self._load_public_datasource_tables(datasource_info)
                            if tables:
                                build_config["table_selector"]["options"] = sorted(tables)
                                logger.debug(f"[CDCInput] Loaded {len(tables)} tables from public datasource")
                                self.status = i18n.t(
                                    "components.input_output.cdc_input.status.tables_loaded", count=len(tables)
                                )
                            else:
                                build_config["table_selector"]["options"] = []
                                logger.warning(f"[CDCInput] No tables found for public datasource: {field_value}")
                                self.status = i18n.t("components.input_output.cdc_input.status.no_tables_found")
                        except Exception as e:
                            logger.error(f"[CDCInput] Failed to load tables from public datasource: {e}")
                            build_config["table_selector"]["options"] = []
                            self.status = i18n.t("components.input_output.cdc_input.errors.load_tables_failed")
                    else:
                        self.status = i18n.t("components.input_output.cdc_input.status.loading_tables")
                        # 提取纯UUID（移除可能的前缀）
                        clean_datasource_id = self._extract_uuid_from_id(datasource_id)
                        logger.info(
                            f"[CDCInput] Loading tables for datasource: {datasource_id} (cleaned: {clean_datasource_id})"
                        )

                        with httpx.Client(timeout=120.0) as client:
                            response = client.get(f"{api_url}/api/v1/datasources/{clean_datasource_id}/tables")

                            if response.status_code == 200:
                                tables = response.json()
                                logger.debug(f"[CDCInput] Loaded {len(tables)} tables")

                                build_config["table_selector"]["options"] = tables
                                self.status = i18n.t(
                                    "components.input_output.cdc_input.status.tables_loaded", count=len(tables)
                                )
                            else:
                                logger.warning(f"[CDCInput] Failed to load tables, status: {response.status_code}")
                                build_config["table_selector"]["options"] = []
                                self.status = i18n.t("components.input_output.cdc_input.status.no_tables_found")
                else:
                    logger.error(f"[CDCInput] Cannot find datasource ID for: {field_value}")
                    build_config["table_selector"]["options"] = []

            except Exception as e:
                logger.error(f"[CDCInput] Error loading tables: {e}")
                build_config["table_selector"]["options"] = []
                self.status = self._format_i18n(
                    "components.input_output.cdc_input.errors.loading_tables_failed", error=str(e)
                )

        # 当表被选中时，记录选择
        if field_name == "table_selector" and field_value:
            logger.debug(f"[CDCInput] Table selected: {field_value}")
            self.status = i18n.t("components.input_output.cdc_input.status.table_selected", table=field_value)

        # 刷新表选择器
        if field_name == "table_selector" and not field_value:
            current_datasource = build_config.get("datasource_selector", {}).get("value")
            if current_datasource:
                logger.debug(f"[CDCInput] Refreshing tables for: {current_datasource}")
                # 触发表列表重新加载（模拟数据源选中）
                return self.update_build_config(build_config, current_datasource, "datasource_selector", None)
            logger.warning("[CDCInput] Cannot refresh tables - no datasource selected")
            self.status = i18n.t("components.input_output.cdc_input.status.no_datasource")

        logger.debug(f"[CDCInput] Returning build_config with keys: {list(build_config.keys())}")
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
                logger.debug(f"[CDCInput] Found valid datasource ID: '{selector_value}'")
                return selector_value

        # 向后兼容：尝试从旧的 "ID|||显示名称" 格式中提取ID
        if "|||" in selector_value:
            datasource_id = selector_value.split("|||")[0]
            logger.warning(f"[CDCInput] Legacy format detected, extracted ID '{datasource_id}' from selector value")
            return datasource_id

        # 再向后兼容：按显示名称查找
        logger.warning(f"[CDCInput] Trying legacy lookup by display name for: '{selector_value}'")
        for metadata in options_metadata:
            if metadata.get("display_name") == selector_value:
                datasource_id = metadata.get("id")
                logger.debug(f"[CDCInput] Found datasource ID '{datasource_id}' for display name '{selector_value}'")
                return datasource_id

        logger.warning(f"[CDCInput] No metadata found for selector value: {selector_value}")
        return None

    def _format_i18n(self, key: str, **kwargs) -> str:
        """格式化国际化文本，进行参数替换.

        i18n 库的内置参数替换功能不太好用，所以手动进行字符串替换。
        """
        text = i18n.t(key)
        for param_key, param_value in kwargs.items():
            text = text.replace(f"{{{param_key}}}", str(param_value))
        return text

    def _get_datasource_id(self) -> str:
        """从选中的显示名称获取实际的数据源ID（支持内置和公共数据源）"""
        if not self.datasource_selector:
            raise ValueError(i18n.t("components.input_output.cdc_input.errors.no_datasource"))

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
                        f"[CDCInput] Found datasource ID '{datasource_id}' ({source}) for '{self.datasource_selector}'"
                    )
                    return datasource_id

            # 如果没找到匹配的显示名称，尝试直接使用作为ID（向后兼容）
            logger.warning(f"[CDCInput] Display name '{self.datasource_selector}' not found, trying as direct ID")
            return self.datasource_selector

        except Exception as e:
            logger.error(f"[CDCInput] Error getting datasource ID: {e}")
            raise ValueError(self._format_i18n("components.input_output.cdc_input.errors.unexpected", error=str(e)))

    def _get_connection_string(self, datasource_id: str, datasource_info: dict = None) -> str:
        """获取数据源连接字符串，支持内置和公共数据源"""
        if datasource_info and datasource_info.get("source") == "public":
            # 公共数据源：从raw_data构建连接字符串
            return self._build_public_connection_string(datasource_info["raw_data"])
        # 内置数据源：使用现有逻辑
        return self._get_builtin_connection_string(datasource_id)

    def _build_public_connection_string(self, raw_data: dict) -> str:
        """构建公共数据源连接字符串"""
        # 获取数据源参数
        params = raw_data.get("dataSourceParam", {})
        if not params:
            logger.warning("[CDCInput] No dataSourceParam found in raw_data")
            params = {}

        # ✅ 修复：优先从 dataSourceParam.type 获取类型（公共数据源的实际位置）
        ds_type = params.get("type") if isinstance(params, dict) else None

        # 如果 dataSourceParam.type 为空，再尝试其他字段（向后兼容）
        if not ds_type:
            ds_type = raw_data.get("type", "mysql")

        ds_type = ds_type.lower()
        logger.debug(f"[CDCInput] Using datasource type: {ds_type}")

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
                f"[CDCInput] Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}"
            )
            return conn_str

        # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
        return self._build_connection_string_from_params(ds_type, params)

    def _build_connection_string_from_params(self, ds_type: str, params: dict) -> str:
        """从参数构建连接字符串 - Only support MySQL, PostgreSQL (CDC does not support Hive, Neo4j)"""
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
        if ds_type == "neo4j":
            # Neo4j connection - 使用 bolt:// 协议，不是 neo4j://
            neo4j_port = port if port != 3306 else 7687
            if username and password:
                return f"bolt://{username_encoded}:{password_encoded}@{host}:{neo4j_port}"
            return f"bolt://{host}:{neo4j_port}"
        raise ValueError(f"Unsupported database type: {ds_type}")

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
                    logger.debug(f"[CDCInput] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                    return uuid_part

        # 如果没有前缀或不符合UUID格式，直接返回
        return datasource_id

    def _get_builtin_connection_string(self, datasource_id: str) -> str:
        """获取内置数据源连接字符串"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            # 提取纯UUID（移除可能的前缀）
            clean_datasource_id = self._extract_uuid_from_id(datasource_id)
            logger.debug(
                f"[CDCInput] Getting connection string for datasource ID: {datasource_id} (cleaned: {clean_datasource_id})"
            )

            with httpx.Client(timeout=120.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{clean_datasource_id}/connection-string")

                if response.status_code != 200:
                    raise ValueError(
                        self._format_i18n(
                            "components.input_output.cdc_input.errors.connection_failed", status=response.status_code
                        )
                    )

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError(i18n.t("components.input_output.cdc_input.errors.empty_connection"))

                return connection_string
        except Exception as e:
            logger.error(f"[CDCInput] Error getting builtin connection string: {e}")
            raise

    def _normalize_cdc_mode(self, mode_value: str) -> str:
        """规范化 CDC 模式值，将 i18n 翻译值映射回标准值.

        Args:
            mode_value: CDC 模式值 (可能是翻译后的值)

        Returns:
            标准 CDC 模式值 ("Timestamp", "Log-Based", "Trigger-Based")
        """
        # 获取所有翻译的模式值
        timestamp_text = i18n.t("components.input_output.cdc_input.cdc_mode.timestamp")
        log_based_text = i18n.t("components.input_output.cdc_input.cdc_mode.log_based")
        trigger_based_text = i18n.t("components.input_output.cdc_input.cdc_mode.trigger_based")

        # 映射翻译值到标准值
        mode_mapping = {
            timestamp_text: "Timestamp",
            log_based_text: "Log-Based",
            trigger_based_text: "Trigger-Based",
            # 兼容旧的英文值
            "Timestamp": "Timestamp",
            "Log-Based": "Log-Based",
            "Trigger-Based": "Trigger-Based",
            # 兼容可能的变体
            "Timestamp-Based": "Timestamp",
            "timestamp": "Timestamp",
            "log_based": "Log-Based",
            "trigger_based": "Trigger-Based",
        }

        normalized = mode_mapping.get(mode_value, mode_value)
        logger.debug(f"[CDCInput] Normalized CDC mode '{mode_value}' to '{normalized}'")
        return normalized

    async def capture_changes(self) -> AsyncGenerator[Data, None]:
        """实时流式捕获数据库变更，一条一条地yield（异步版本）.

        使用Change Data Capture (CDC)实时捕获数据库变更。
        """
        try:
            self._should_stop = False
            self.status = i18n.t("components.input_output.cdc_input.status.capturing")

            # 验证必需的输入
            if not self.datasource_selector:
                raise ValueError(i18n.t("components.input_output.cdc_input.errors.no_datasource"))
            if not self.table_selector:
                raise ValueError(i18n.t("components.input_output.cdc_input.errors.no_table"))

            # 规范化 CDC 模式
            normalized_mode = self._normalize_cdc_mode(self.cdc_mode)

            if normalized_mode == "Timestamp":
                async for data in self._capture_timestamp_based_streaming_async():
                    yield data
            elif normalized_mode == "Log-Based":
                async for data in self._capture_log_based_streaming_async():
                    yield data
            elif normalized_mode == "Trigger-Based":
                async for data in self._capture_trigger_based_streaming_async():
                    yield data
            else:
                raise ValueError(i18n.t("components.input_output.cdc_input.errors.invalid_mode"))

        except Exception as e:
            error_msg = i18n.t("components.input_output.cdc_input.errors.capture_failed", error=str(e))
            self.status = error_msg
            logger.error(f"CDC捕获失败: {error_msg}")
            raise ValueError(error_msg) from e

    def _capture_timestamp_based_streaming(self) -> Generator[Data, None, None]:
        """流式捕获基于时间戳的变更，一条一条yield."""
        import time

        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = None
        try:
            # 获取数据源ID和连接字符串
            datasource_id = self._get_datasource_id()
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            engine = create_engine(connection_string, poolclass=NullPool)

            # 持续轮询变更
            last_sync = self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00"
            changes_count = 0

            while not self._should_stop:
                with engine.connect() as connection:
                    # 构建查询语句
                    query = f"""
                        SELECT * FROM {self.table_selector}
                        WHERE {self.timestamp_column} > '{last_sync}'
                        ORDER BY {self.timestamp_column}
                        LIMIT {self.batch_size}
                    """

                    df = pd.read_sql_query(text(query), connection)

                    # 如果有新数据，一条一条yield
                    if not df.empty:
                        for _, row in df.iterrows():
                            if self._should_stop:
                                logger.info("CDC流式捕获被停止")
                                break

                            row_dict = row.to_dict()

                            if self.include_change_type:
                                row_dict["_change_type"] = "INSERT/UPDATE"
                                row_dict["_capture_time"] = datetime.now().isoformat()

                            changes_count += 1
                            logger.debug(f"CDC捕获到变更 #{changes_count}")

                            yield Data(data=row_dict)

                            # 更新last_sync为当前行的时间戳
                            if self.timestamp_column in row_dict:
                                last_sync = str(row_dict[self.timestamp_column])

                    # 如果没有新数据或处理完当前批次，等待一段时间再查询
                    if not self._should_stop:
                        time.sleep(self.poll_interval_seconds)

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=changes_count)
            logger.info(f"CDC流式捕获完成，共捕获 {changes_count} 条变更")

        finally:
            # 确保引擎被正确释放
            if engine:
                engine.dispose()

    def _capture_log_based_streaming(self) -> Generator[Data, None, None]:
        """流式捕获基于日志的变更."""
        # Log-based CDC需要集成Debezium等工具
        # 这里提供占位符实现
        logger.info("Log-based CDC需要集成Debezium或类似工具")

        info = {
            "message": i18n.t("components.input_output.cdc_input.info.log_based_requirement"),
            "table": self.table_selector,
            "datasource": self.datasource_selector,
            "mode": "log-based",
        }
        yield Data(data=info)

        self.status = i18n.t("components.input_output.cdc_input.status.log_based_placeholder")

    def _capture_trigger_based_streaming(self) -> Generator[Data, None, None]:
        """流式捕获基于触发器的变更，一条一条yield."""
        import time

        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = None
        try:
            # 获取数据源ID和连接字符串
            datasource_id = self._get_datasource_id()
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            engine = create_engine(connection_string, poolclass=NullPool)

            # 审计表名称
            audit_table = f"{self.table_selector}_audit"

            # 首先检查审计表是否存在
            with engine.connect() as connection:
                if not self._check_table_exists(connection, audit_table):
                    error_msg = self._format_i18n(
                        "components.input_output.cdc_input.errors.audit_table_not_found",
                        table=self.table_selector,
                        audit_table=audit_table,
                    )
                    logger.error(f"[CDCInput] {error_msg}")
                    self.status = error_msg
                    raise ValueError(error_msg)

            # 持续轮询变更
            last_sync = self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00"
            changes_count = 0

            while not self._should_stop:
                with engine.connect() as connection:
                    query = f"""
                        SELECT * FROM {audit_table}
                        WHERE audit_timestamp > '{last_sync}'
                        ORDER BY audit_timestamp
                        LIMIT {self.batch_size}
                    """

                    try:
                        df = pd.read_sql_query(text(query), connection)

                        # 如果有新数据，一条一条yield
                        if not df.empty:
                            for _, row in df.iterrows():
                                if self._should_stop:
                                    logger.info("CDC流式捕获被停止")
                                    break

                                row_dict = row.to_dict()

                                if self.include_change_type:
                                    row_dict["_change_type"] = row_dict.get("operation_type", "UNKNOWN")
                                    row_dict["_capture_time"] = datetime.now().isoformat()

                                changes_count += 1
                                logger.debug(f"CDC审计表捕获到变更 #{changes_count}")

                                yield Data(data=row_dict)

                                # 更新last_sync为当前行的审计时间戳
                                if "audit_timestamp" in row_dict:
                                    last_sync = str(row_dict["audit_timestamp"])

                    except Exception as e:
                        logger.error(f"[CDCInput] 查询审计表 {audit_table} 出错: {e}")
                        raise ValueError(
                            self._format_i18n(
                                "components.input_output.cdc_input.errors.audit_query_failed",
                                audit_table=audit_table,
                                error=str(e),
                            )
                        )

                # 如果没有新数据或处理完当前批次，等待一段时间再查询
                if not self._should_stop:
                    time.sleep(self.poll_interval_seconds)

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=changes_count)
            logger.info(f"CDC审计表流式捕获完成，共捕获 {changes_count} 条变更")

        finally:
            # 确保引擎被正确释放
            if engine:
                engine.dispose()

    async def _capture_timestamp_based_streaming_async(self) -> AsyncGenerator[Data, None]:
        """异步流式捕获基于时间戳的变更，一条一条yield."""
        import asyncio

        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = None
        try:
            # ✅ 在线程池中获取数据源ID和连接字符串（避免阻塞）
            def get_connection_setup():
                datasource_id = self._get_datasource_id()
                datasource_info = getattr(self, "_current_datasource_info", None)
                connection_string = self._get_connection_string(datasource_id, datasource_info)
                return connection_string

            logger.info("[CDCInput] Getting connection string (may take up to 60s)...")
            connection_string = await asyncio.to_thread(get_connection_setup)
            logger.info("[CDCInput] Connection string obtained successfully")

            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                pool_pre_ping=True,  # 自动检查连接
                connect_args={
                    "connect_timeout": 60  # 连接超时60秒
                },
            )

            # 持续轮询变更
            # 使用运行时状态，如果存在则使用，否则使用配置值
            last_sync = (
                self._current_last_sync
                if self._current_last_sync
                else (self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00")
            )
            changes_count = 0
            logger.info(
                f"[CDCInput] Starting streaming with timestamp_column='{self.timestamp_column}', last_sync='{last_sync}'"
            )

            while not self._should_stop:
                # ✅ 在线程池中执行阻塞的数据库查询
                def query_changes():
                    with engine.connect() as connection:
                        # 使用参数化查询，确保时间戳比较正确
                        query = text(f"""
                            SELECT * FROM {self.table_selector}
                            WHERE {self.timestamp_column} > :last_sync
                            ORDER BY {self.timestamp_column}
                            LIMIT :batch_size
                        """)
                        logger.debug(
                            f"[CDCInput] Executing query with last_sync='{last_sync}' (type: {type(last_sync)})"
                        )
                        return pd.read_sql_query(
                            query, connection, params={"last_sync": last_sync, "batch_size": self.batch_size}
                        )

                df = await asyncio.to_thread(query_changes)

                # 如果有新数据，一条一条yield
                if not df.empty:
                    for _, row in df.iterrows():
                        if self._should_stop:
                            logger.info("CDC流式捕获被停止")
                            break

                        row_dict = row.to_dict()

                        if self.include_change_type:
                            row_dict["_change_type"] = "INSERT/UPDATE"
                            row_dict["_capture_time"] = datetime.now().isoformat()

                        changes_count += 1
                        logger.debug(f"CDC捕获到变更 #{changes_count}")

                        yield Data(data=row_dict)

                        # 更新last_sync为当前行的时间戳，并保存到组件属性
                        if self.timestamp_column in row_dict:
                            # 保持原始时间戳格式，不进行任何转换
                            original_timestamp = row_dict[self.timestamp_column]
                            last_sync = str(original_timestamp)
                            self._current_last_sync = last_sync  # 持久化到组件属性
                            logger.info(
                                f"[CDCInput] Updated last_sync to '{last_sync}' (type: {type(original_timestamp)}) from column '{self.timestamp_column}'"
                            )

                        # ✅ 让出控制权
                        await asyncio.sleep(0)

                # 如果没有新数据或处理完当前批次，等待一段时间再查询
                if not self._should_stop:
                    # ✅ 使用 asyncio.sleep 而非 time.sleep
                    await asyncio.sleep(self.poll_interval_seconds)

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=changes_count)
            logger.info(f"CDC流式捕获完成，共捕获 {changes_count} 条变更")

        finally:
            # 确保引擎被正确释放
            if engine:
                engine.dispose()

    async def _capture_log_based_streaming_async(self) -> AsyncGenerator[Data, None]:
        """异步流式捕获基于日志的变更."""
        import asyncio

        # Log-based CDC需要集成Debezium等工具
        # 这里提供占位符实现
        logger.info("Log-based CDC需要集成Debezium或类似工具")

        info = {
            "message": i18n.t("components.input_output.cdc_input.info.log_based_requirement"),
            "table": self.table_selector,
            "datasource": self.datasource_selector,
            "mode": "log-based",
        }
        yield Data(data=info)

        # ✅ 让出控制权
        await asyncio.sleep(0)

        self.status = i18n.t("components.input_output.cdc_input.status.log_based_placeholder")

    async def _capture_trigger_based_streaming_async(self) -> AsyncGenerator[Data, None]:
        """异步流式捕获基于触发器的变更，一条一条yield."""
        import asyncio

        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        engine = None
        try:
            # ✅ 在线程池中获取数据源ID和连接字符串（避免阻塞）
            def get_connection_setup():
                datasource_id = self._get_datasource_id()
                datasource_info = getattr(self, "_current_datasource_info", None)
                connection_string = self._get_connection_string(datasource_id, datasource_info)
                return connection_string

            logger.info("[CDCInput] Getting connection string (may take up to 60s)...")
            connection_string = await asyncio.to_thread(get_connection_setup)
            logger.info("[CDCInput] Connection string obtained successfully")

            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                pool_pre_ping=True,  # 自动检查连接
                connect_args={
                    "connect_timeout": 60  # 连接超时60秒
                },
            )

            # 审计表名称
            audit_table = f"{self.table_selector}_audit"

            # 首先检查审计表是否存在（在线程池中执行）
            def check_table():
                with engine.connect() as connection:
                    return self._check_table_exists(connection, audit_table)

            table_exists = await asyncio.to_thread(check_table)

            if not table_exists:
                error_msg = self._format_i18n(
                    "components.input_output.cdc_input.errors.audit_table_not_found",
                    table=self.table_selector,
                    audit_table=audit_table,
                )
                logger.error(f"[CDCInput] {error_msg}")
                self.status = error_msg
                raise ValueError(error_msg)

            # 持续轮询变更
            # 使用运行时状态，如果存在则使用，否则使用配置值
            last_sync = (
                self._current_last_sync
                if self._current_last_sync
                else (self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00")
            )
            changes_count = 0

            while not self._should_stop:
                # ✅ 在线程池中执行阻塞的数据库查询
                def query_audit():
                    with engine.connect() as connection:
                        query = f"""
                            SELECT * FROM {audit_table}
                            WHERE audit_timestamp > '{last_sync}'
                            ORDER BY audit_timestamp
                            LIMIT {self.batch_size}
                        """
                        return pd.read_sql_query(text(query), connection)

                try:
                    df = await asyncio.to_thread(query_audit)

                    # 如果有新数据，一条一条yield
                    if not df.empty:
                        for _, row in df.iterrows():
                            if self._should_stop:
                                logger.info("CDC流式捕获被停止")
                                break

                            row_dict = row.to_dict()

                            if self.include_change_type:
                                row_dict["_change_type"] = row_dict.get("operation_type", "UNKNOWN")
                                row_dict["_capture_time"] = datetime.now().isoformat()

                            changes_count += 1
                            logger.debug(f"CDC审计表捕获到变更 #{changes_count}")

                            yield Data(data=row_dict)

                            # 更新last_sync为当前行的审计时间戳，并保存到组件属性
                            if "audit_timestamp" in row_dict:
                                last_sync = str(row_dict["audit_timestamp"])
                                self._current_last_sync = last_sync  # 持久化到组件属性

                            # ✅ 让出控制权
                            await asyncio.sleep(0)

                except Exception as e:
                    logger.error(f"[CDCInput] 查询审计表 {audit_table} 出错: {e}")
                    raise ValueError(
                        self._format_i18n(
                            "components.input_output.cdc_input.errors.audit_query_failed",
                            audit_table=audit_table,
                            error=str(e),
                        )
                    )

                # 如果没有新数据或处理完当前批次，等待一段时间再查询
                if not self._should_stop:
                    # ✅ 使用 asyncio.sleep 而非 time.sleep
                    await asyncio.sleep(self.poll_interval_seconds)

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=changes_count)
            logger.info(f"CDC审计表流式捕获完成，共捕获 {changes_count} 条变更")

        finally:
            # 确保引擎被正确释放
            if engine:
                engine.dispose()

    def _capture_timestamp_based(self) -> list[Data]:
        """Capture changes using timestamp-based tracking."""
        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        try:
            # 获取数据源ID和连接字符串
            datasource_id = self._get_datasource_id()
            # 使用保存的数据源信息
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            engine = create_engine(connection_string, poolclass=NullPool)
            result_data = []

            with engine.connect() as connection:
                # Build query to fetch changes since last sync
                last_sync = self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00"

                query = f"""
                    SELECT * FROM {self.table_selector}
                    WHERE {self.timestamp_column} > '{last_sync}'
                    ORDER BY {self.timestamp_column}
                    LIMIT {self.batch_size}
                """

                df = pd.read_sql_query(text(query), connection)

                for _, row in df.iterrows():
                    row_dict = row.to_dict()

                    if self.include_change_type:
                        row_dict["_change_type"] = "INSERT/UPDATE"
                        row_dict["_capture_time"] = datetime.now().isoformat()

                    result_data.append(Data(data=row_dict))

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=len(result_data))
            return result_data

        finally:
            # 确保引擎被正确释放
            if "engine" in locals():
                engine.dispose()

    def _capture_log_based(self) -> list[Data]:
        """Capture changes using database transaction logs."""
        # This would typically integrate with tools like Debezium, Maxwell, etc.
        # For now, provide a placeholder implementation
        logger.info("Log-based CDC requires integration with Debezium or similar tools")

        result_data = []
        info = {
            "message": i18n.t("components.input_output.cdc_input.info.log_based_requirement"),
            "table": self.table_selector,
            "datasource": self.datasource_selector,
            "mode": "log-based",
        }
        result_data.append(Data(data=info))

        self.status = i18n.t("components.input_output.cdc_input.status.log_based_placeholder")
        return result_data

    def _capture_trigger_based(self) -> list[Data]:
        """Capture changes using database triggers and audit tables."""
        import pandas as pd
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        try:
            # 获取数据源ID和连接字符串
            datasource_id = self._get_datasource_id()
            # 使用保存的数据源信息
            datasource_info = getattr(self, "_current_datasource_info", None)
            connection_string = self._get_connection_string(datasource_id, datasource_info)

            engine = create_engine(connection_string, poolclass=NullPool)
            result_data = []

            # Assume audit table exists with naming convention: {table_name}_audit
            audit_table = f"{self.table_selector}_audit"

            with engine.connect() as connection:
                # 首先检查审计表是否存在
                if not self._check_table_exists(connection, audit_table):
                    error_msg = self._format_i18n(
                        "components.input_output.cdc_input.errors.audit_table_not_found",
                        table=self.table_selector,
                        audit_table=audit_table,
                    )
                    logger.error(f"[CDCInput] {error_msg}")
                    self.status = error_msg
                    raise ValueError(error_msg)

                last_sync = self.last_sync_time if self.last_sync_time else "1970-01-01 00:00:00"

                query = f"""
                    SELECT * FROM {audit_table}
                    WHERE audit_timestamp > '{last_sync}'
                    ORDER BY audit_timestamp
                    LIMIT {self.batch_size}
                """

                try:
                    df = pd.read_sql_query(text(query), connection)

                    for _, row in df.iterrows():
                        row_dict = row.to_dict()

                        if self.include_change_type:
                            row_dict["_change_type"] = row_dict.get("operation_type", "UNKNOWN")
                            row_dict["_capture_time"] = datetime.now().isoformat()

                        result_data.append(Data(data=row_dict))

                except Exception as e:
                    logger.error(f"[CDCInput] Error querying audit table {audit_table}: {e}")
                    raise ValueError(
                        self._format_i18n(
                            "components.input_output.cdc_input.errors.audit_query_failed",
                            audit_table=audit_table,
                            error=str(e),
                        )
                    )

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=len(result_data))
            return result_data

        finally:
            # 确保引擎被正确释放
            if "engine" in locals():
                engine.dispose()

    def _check_table_exists(self, connection, table_name: str) -> bool:
        """检查表是否存在"""
        from sqlalchemy import text

        try:
            # PostgreSQL 检查
            query = text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """
            )
            result = connection.execute(query, {"table_name": table_name})
            return result.scalar()
        except Exception as e:
            logger.warning(f"[CDCInput] Could not check if table exists: {e}")
            # 如果检查失败，假设表存在，让后续查询来处理
            return True

    def get_change_summary(self) -> Data:
        """Get summary of captured changes."""
        try:
            changes = self.capture_changes()
            summary = {
                "datasource": self.datasource_selector,
                "table_name": self.table_selector,
                "cdc_mode": self._normalize_cdc_mode(self.cdc_mode),
                "total_changes": len(changes),
                "capture_time": datetime.now().isoformat(),
            }
            return Data(data=summary)
        except Exception as e:
            # 如果捕获变更失败，返回错误摘要
            error_summary = {
                "datasource": getattr(self, "datasource_selector", None),
                "table_name": getattr(self, "table_selector", None),
                "cdc_mode": self._normalize_cdc_mode(getattr(self, "cdc_mode", "Unknown")),
                "total_changes": 0,
                "capture_time": datetime.now().isoformat(),
                "error": str(e),
            }
            return Data(data=error_summary)

    def _load_public_datasource_tables(self, datasource_info: dict) -> list[str]:
        """为公共数据源加载表列表，直接通过连接信息查询数据库"""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.pool import NullPool

        try:
            # 从datasource_info获取raw_data
            raw_data = datasource_info.get("raw_data", datasource_info)

            # 构建连接字符串
            connection_string = self._build_public_connection_string(raw_data)
            logger.debug("[CDCInput] Loading tables for public datasource with connection string")

            # 获取数据源类型
            params = raw_data.get("dataSourceParam", {})
            ds_type = params.get("type") if isinstance(params, dict) else None
            if not ds_type:
                ds_type = raw_data.get("type") or raw_data.get("dataSourceType") or raw_data.get("dbType") or "mysql"
            ds_type = ds_type.lower()
            logger.debug(f"[CDCInput] Public datasource type: {ds_type}")

            # CDC只支持MySQL和PostgreSQL，不支持Neo4j
            if ds_type not in ["mysql", "postgresql", "postgres"]:
                logger.warning(f"[CDCInput] CDC does not support datasource type: {ds_type}")
                return []

            # 使用SQLAlchemy获取表列表
            engine = create_engine(connection_string, poolclass=NullPool)

            with engine.connect() as conn:
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                logger.info(f"[CDCInput] Loaded {len(tables)} tables from public datasource")
                return tables

        except Exception as e:
            logger.error(f"[CDCInput] Failed to load tables from public datasource: {e}")
            import traceback

            logger.error(f"[CDCInput] Traceback: {traceback.format_exc()}")
            raise
        finally:
            if "engine" in locals():
                engine.dispose()

    def _load_unified_datasources(self) -> list[dict]:
        """加载统一的数据源列表（内置 + 公共）"""
        import os

        import httpx

        all_datasources = []

        try:
            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

            # 1. 加载内置数据源（现有逻辑）
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources")

                    if response.status_code == 200:
                        datasources = response.json()
                        logger.debug(f"[CDCInput] Loaded {len(datasources)} built-in datasources from API")

                        for ds in datasources:
                            # 提取纯UUID（移除可能的前缀）
                            datasource_id = self._extract_uuid_from_id(str(ds["id"]))
                            display_name = f"{ds['name']} ({ds['type']}) [自定义]"
                            all_datasources.append(
                                {
                                    "id": datasource_id,
                                    "name": ds["name"],
                                    "type": ds["type"],
                                    "source": "builtin",
                                    "display_name": display_name,
                                    "database": ds.get("database"),  # 保留 database 字段
                                    "host": ds.get("host"),
                                    "port": ds.get("port"),
                                }
                            )
                    else:
                        logger.warning(
                            f"[CDCInput] Failed to load built-in datasources, status: {response.status_code}"
                        )
            except Exception as e:
                logger.error(f"[CDCInput] Error loading built-in datasources: {e}")

            # 2. 加载公共数据源（通过feign接口）
            try:
                public_datasources = asyncio.run(self._get_public_datasources())
                if public_datasources:
                    logger.debug(f"[CDCInput] Loaded {len(public_datasources)} public datasources from feign API")

                    for ds in public_datasources:
                        # ✅ 修复：获取正确的数据源类型（优先从 dataSourceParam.type）
                        params = ds.get("dataSourceParam", {})
                        ds_type = params.get("type") if isinstance(params, dict) else None
                        if not ds_type:
                            ds_type = ds.get("type") or ds.get("dataSourceType") or ds.get("dbType") or "mysql"

                        # 构建丰富的显示名称
                        # 使用修正后的type构建新的ds对象
                        ds_with_type = {**ds, "type": ds_type}
                        display_name = self._build_display_name(ds_with_type, "public")
                        all_datasources.append(
                            {
                                "id": str(ds["id"]),
                                "name": ds["name"],
                                "type": ds_type,  # ✅ 使用修正后的type
                                "source": "public",
                                "display_name": display_name,
                                "raw_data": ds,
                            }
                        )
                else:
                    logger.debug("[CDCInput] No public datasources available")
            except Exception as e:
                logger.error(f"[CDCInput] Error loading public datasources: {e}")

            # 过滤掉Neo4j和Hive数据源（CDC不支持这两种类型）
            filtered_datasources = [ds for ds in all_datasources if ds["type"].lower() not in ["neo4j", "hive"]]

            logger.info(
                f"[CDCInput] Loaded {len(filtered_datasources)} datasources "
                f"(excluded {len(all_datasources) - len(filtered_datasources)} Neo4j/Hive datasources, CDC not supported)"
            )
            return filtered_datasources

        except Exception as e:
            logger.error(f"[CDCInput] Error in _load_unified_datasources: {e}")
            return []

    async def _get_public_datasources(self) -> list[dict]:
        """通过feign接口获取公共数据源"""
        try:
            from lfx.services.deps import get_feign_service

            feign_service = get_feign_service()
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            client = DataConstructionFeignClient(feign_service)

            # 调用feign接口获取数据源列表
            datasource_list = await client.get_datasource_list()

            logger.debug(f"[CDCInput] Got {len(datasource_list)} public datasources from feign API")
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[CDCInput] Failed to get public datasources: {e}")
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
