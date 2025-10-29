import asyncio
from datetime import datetime
from typing import Any

import i18n

from lfx.base.datasource.manager import DataSourceManager
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema import Data


class ETLCDCStreamInputComponent(Component):
    display_name = i18n.t("components.input_output.cdc_input.display_name")
    description = i18n.t("components.input_output.cdc_input.description")
    icon = "database"
    name = "ETLCDCStreamInput"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_manager = DataSourceManager()

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
        ),
        Output(
            name="change_summary",
            display_name=i18n.t("components.input_output.cdc_input.outputs.change_summary.display_name"),
            method="get_change_summary",
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
                    self.status = i18n.t("components.input_output.cdc_input.status.loading_tables")
                    logger.info(f"[CDCInput] Loading tables for datasource: {datasource_id}")

                    with httpx.Client(timeout=10.0) as client:
                        response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/tables")

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

    def _get_datasource_id_from_metadata(self, display_name: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据显示名称获取数据源ID"""
        for metadata in options_metadata:
            if metadata.get("display_name") == display_name:
                datasource_id = metadata.get("id")
                logger.debug(f"[CDCInput] Found datasource ID '{datasource_id}' for display name '{display_name}'")
                return datasource_id

        logger.warning(f"[CDCInput] No metadata found for display name: {display_name}")
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

    def capture_changes(self) -> list[Data]:
        """Capture database changes using Change Data Capture (CDC) in real-time."""
        try:
            self.status = i18n.t("components.input_output.cdc_input.status.capturing")

            # 验证必需的输入
            if not self.datasource_selector:
                raise ValueError(i18n.t("components.input_output.cdc_input.errors.no_datasource"))
            if not self.table_selector:
                raise ValueError(i18n.t("components.input_output.cdc_input.errors.no_table"))

            # 规范化 CDC 模式
            normalized_mode = self._normalize_cdc_mode(self.cdc_mode)

            if normalized_mode == "Timestamp":
                return self._capture_timestamp_based()
            if normalized_mode == "Log-Based":
                return self._capture_log_based()
            if normalized_mode == "Trigger-Based":
                return self._capture_trigger_based()
            raise ValueError(i18n.t("components.input_output.cdc_input.errors.invalid_mode"))

        except Exception as e:
            error_msg = i18n.t("components.input_output.cdc_input.errors.capture_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

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
                    logger.error(f"Audit table {audit_table} may not exist: {e}")
                    raise ValueError(
                        i18n.t("components.input_output.cdc_input.errors.audit_table_missing", table=audit_table)
                    )

            self.status = i18n.t("components.input_output.cdc_input.status.success", changes=len(result_data))
            return result_data

        finally:
            # 确保引擎被正确释放
            if "engine" in locals():
                engine.dispose()

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

    def _load_unified_datasources(self) -> list[dict]:
        """加载统一的数据源列表（内置 + 公共）"""
        import os

        import httpx

        all_datasources = []

        try:
            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

            # 1. 加载内置数据源（现有逻辑）
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources")

                    if response.status_code == 200:
                        datasources = response.json()
                        logger.debug(f"[CDCInput] Loaded {len(datasources)} built-in datasources from API")

                        for ds in datasources:
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
                        # 构建丰富的显示名称
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
                else:
                    logger.debug("[CDCInput] No public datasources available")
            except Exception as e:
                logger.error(f"[CDCInput] Error loading public datasources: {e}")

            logger.info(f"[CDCInput] Loaded total of {len(all_datasources)} unified datasources")
            return all_datasources

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
