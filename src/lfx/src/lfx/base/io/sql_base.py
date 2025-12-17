"""SQL 数据库输入/输出组件的中间基类

为标准 SQL 数据库（PostgreSQL、MySQL、Oracle、SQL Server、Doris 等）
提供通用的表发现、数据读取和写入实现。

这些数据库共享相同的模式：
1. 使用 SQLAlchemy 连接
2. 使用 inspect 发现表
3. 使用 pd.read_sql 读取数据
4. 使用 pd.to_sql 写入数据
"""

import logging
from abc import ABC

import i18n
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from lfx.base.io.table_base import BaseTableInputComponent, BaseTableOutputComponent
from lfx.schema import Data

logger = logging.getLogger(__name__)

# Transformation rule options (for Input components)
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

# Update options (for Output components)
UPDATE_OPTION_VALUES_KEYS = [
    "components.input_output.databases.field_mappings.update_options.sync_update",
    "components.input_output.databases.field_mappings.update_options.insert_only",
    "components.input_output.databases.field_mappings.update_options.update_when_has_value",
    "components.input_output.databases.field_mappings.update_options.update_when_not_empty",
    "components.input_output.databases.field_mappings.update_options.cumulative_update",
    "components.input_output.databases.field_mappings.update_options.prohibit_update",
]

# Mapping from internal values to translation keys (for both options and options_metadata)
UPDATE_OPTION_VALUE_MAPPING = {
    "sync_update": "components.input_output.databases.field_mappings.update_options.sync_update",
    "insert_only": "components.input_output.databases.field_mappings.update_options.insert_only",
    "update_when_has_value": "components.input_output.databases.field_mappings.update_options.update_when_has_value",
    "update_when_not_empty": "components.input_output.databases.field_mappings.update_options.update_when_not_empty",
    "cumulative_update": "components.input_output.databases.field_mappings.update_options.cumulative_update",
    "prohibit_update": "components.input_output.databases.field_mappings.update_options.prohibit_update",
}


def get_update_option_metadata():
    """生成 update_option 的 options_metadata（动态翻译）

    返回格式：[{"value": "sync_update", "label": "同步更新"}, ...]
    这样前端可以正确显示翻译后的文本
    """
    return [
        {"value": "sync_update", "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["sync_update"])},
        {"value": "insert_only", "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["insert_only"])},
        {
            "value": "update_when_has_value",
            "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["update_when_has_value"]),
        },
        {
            "value": "update_when_not_empty",
            "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["update_when_not_empty"]),
        },
        {"value": "cumulative_update", "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["cumulative_update"])},
        {"value": "prohibit_update", "label": i18n.t(UPDATE_OPTION_VALUE_MAPPING["prohibit_update"])},
    ]


class BaseSQLInputComponent(BaseTableInputComponent, ABC):
    """SQL 数据库输入的中间基类

    实现标准 SQL 数据库的通用功能：
    - 使用 SQLAlchemy inspect 发现表
    - 使用 pandas read_sql 读取数据

    子类只需实现 _build_connection_string() 方法
    """

    def _load_tables(self) -> list[str]:
        """使用 SQLAlchemy inspect 加载表列表

        Returns:
            list[str]: 表名列表

        Raises:
            Exception: 如果连接失败或表发现失败
        """
        try:
            conn_str = self._build_connection_string()
            engine = create_engine(conn_str, poolclass=NullPool)

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            logger.info(f"{self.__class__.__name__} found {len(tables)} tables")
            return tables

        except Exception as e:
            logger.error(f"Error loading tables for {self.__class__.__name__}: {e}")
            raise

    async def _read_data(self) -> list[Data]:
        """使用 pandas read_sql 从 SQL 表读取数据

        Returns:
            list[Data]: Data对象列表，每个Data对象包含一行数据的字典

        Raises:
            Exception: 如果读取失败
        """
        try:
            # 验证必填字段
            self._validate_required_fields("sql_query")

            # 构建连接
            conn_str = self._build_connection_string()
            engine = create_engine(conn_str, poolclass=NullPool)

            # 获取查询语句
            query = getattr(self, "sql_query", "")
            if not query.strip():
                raise ValueError("SQL query cannot be empty")

            logger.info(f"{self.__class__.__name__} executing query: {query[:100]}...")

            # 读取数据
            df = pd.read_sql(query, engine)

            # 清理 NaN 和 NaT 值，替换为 None（JSON 可序列化）
            import numpy as np

            df = df.replace({pd.NaT: None, pd.NA: None, np.nan: None, np.inf: None, -np.inf: None})
            df = df.where(pd.notna(df), None)

            # 将每一行转换为 Data 对象
            result_data = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            logger.info(f"{self.__class__.__name__} read {len(result_data)} rows")
            return result_data

        except Exception as e:
            logger.error(f"Error reading data for {self.__class__.__name__}: {e}")
            raise

    def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ):
        """动态更新配置 - 加载数据源列表和处理 Action 按钮

        Args:
            build_config: 当前构建配置
            field_value: 变化字段的值
            field_name: 变化字段的名称
            action: 按钮操作名称（如果是按钮触发）

        Returns:
            dict: 更新后的构建配置
        """
        logger.info(f"{self.__class__.__name__} update_build_config - field_name: {field_name}, action: {action}")

        # 1. 加载数据源列表（初始加载或刷新时）
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"Loading datasources (field_name={field_name}, field_value={field_value})")
            try:
                datasources = self._load_datasource_metadata()
                options = [ds["id"] for ds in datasources]
                options_metadata = [
                    {
                        "value": ds["id"],
                        "label": ds["display_name"],
                        "id": ds["id"],
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": ds["source"],
                        "display_name": ds["display_name"],
                        "raw_data": ds.get("raw_data"),
                    }
                    for ds in datasources
                ]

                build_config["datasource_selector"]["options"] = options
                build_config["datasource_selector"]["options_metadata"] = options_metadata
                logger.debug(f"Set datasource_selector options: {options}")

            except Exception as e:
                logger.error(f"Error loading unified datasources: {e}")
                build_config["datasource_selector"]["options"] = ["加载失败"]
                build_config["datasource_selector"]["options_metadata"] = []

        # 2. 处理 "分析SQL" 按钮点击（从 field_mappings 表触发）
        if field_name == "field_mappings" and action == "analyze_sql":
            logger.info("SQL analysis triggered by action button")

            try:
                # 获取当前SQL和数据源
                current_sql = build_config.get("sql_query", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("No SQL query provided")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_sql")
                    return build_config

                if not current_datasource:
                    logger.warning("No datasource selected")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_datasource")
                    return build_config

                # 从 options_metadata 中获取数据源ID
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_id = self._get_datasource_id_from_metadata(current_datasource, options_metadata)

                if not datasource_id:
                    logger.error(f"Cannot find datasource ID for: {current_datasource}")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_datasource")
                    return build_config

                # 获取数据源详细信息
                datasource_info = None
                for metadata in options_metadata:
                    if (
                        metadata.get("id") == current_datasource
                        or metadata.get("value") == current_datasource
                        or metadata.get("display_name") == current_datasource
                    ):
                        datasource_info = metadata
                        break

                # 如果 options_metadata 中的数据不完整，重新加载
                if datasource_info:
                    source = datasource_info.get("source")
                    ds_type = datasource_info.get("type", "").lower()
                    needs_reload = False

                    if source == "builtin" and ds_type != "neo4j":
                        if not datasource_info.get("host") or not datasource_info.get("port"):
                            logger.warning("Cached datasource_info missing connection params, reloading")
                            needs_reload = True
                    elif source == "public":
                        if not datasource_info.get("raw_data"):
                            logger.warning("Cached datasource_info missing raw_data, reloading")
                            needs_reload = True

                    if needs_reload:
                        all_datasources = self._load_datasource_metadata()
                        for ds in all_datasources:
                            if ds["id"] == current_datasource or ds["display_name"] == current_datasource:
                                datasource_info = {
                                    "id": ds["id"],
                                    "name": ds["name"],
                                    "type": ds["type"],
                                    "source": ds["source"],
                                    "display_name": ds["display_name"],
                                    "raw_data": ds.get("raw_data"),
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

                # 执行SQL分析
                logger.info("Starting SQL field inference...")
                self.status = i18n.t("components.input_output.databases.postgresql_input.status.analyzing_sql")

                field_info = self._infer_field_info(datasource_id, current_sql)

                if field_info:
                    build_config["field_mappings"]["value"] = field_info
                    logger.info(f"SQL analysis completed, generated {len(field_info)} field mappings")
                    self.status = i18n.t(
                        "components.input_output.databases.postgresql_input.status.analysis_success",
                        count=len(field_info),
                    )
                else:
                    logger.warning("No fields inferred from SQL")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.status.no_fields_found")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"SQL analysis failed: {error_msg}")
                self.status = i18n.t(
                    "components.input_output.databases.postgresql_input.errors.analysis_failed", error=error_msg
                )

        # 3. 处理 "预览数据" 按钮点击（从 preview_table 表触发）
        if field_name == "preview_table" and action == "preview_data":
            logger.info("Data preview triggered by action button")

            try:
                # 获取当前SQL和数据源
                current_sql = build_config.get("sql_query", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("No SQL query provided for preview")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_sql")
                    return build_config

                if not current_datasource:
                    logger.warning("No datasource selected for preview")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_datasource")
                    return build_config

                # 从 options_metadata 中获取数据源ID
                datasource_id = self._get_datasource_id_from_metadata(
                    current_datasource, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if not datasource_id:
                    logger.error(f"Cannot find datasource ID for preview: {current_datasource}")
                    self.status = i18n.t("components.input_output.databases.postgresql_input.errors.no_datasource")
                    return build_config

                # 获取数据源信息
                options_metadata = build_config.get("datasource_selector", {}).get("options_metadata", [])
                datasource_info = None
                for metadata in options_metadata:
                    if (
                        metadata.get("display_name") == current_datasource
                        or metadata.get("id") == current_datasource
                        or metadata.get("value") == current_datasource
                    ):
                        datasource_info = metadata
                        break

                # 检查并重新加载数据源信息（与SQL分析相同的逻辑）
                if datasource_info:
                    source = datasource_info.get("source")
                    ds_type = datasource_info.get("type", "").lower()
                    needs_reload = False

                    if source == "builtin" and ds_type != "neo4j":
                        if not datasource_info.get("host") or not datasource_info.get("port"):
                            logger.warning("Preview: Cached datasource_info missing connection params, reloading")
                            needs_reload = True
                    elif source == "public":
                        if not datasource_info.get("raw_data"):
                            logger.warning("Preview: Cached datasource_info missing raw_data, reloading")
                            needs_reload = True

                    if needs_reload:
                        all_datasources = self._load_datasource_metadata()
                        for ds in all_datasources:
                            if ds["display_name"] == current_datasource or ds["id"] == current_datasource:
                                datasource_info = {
                                    "id": ds["id"],
                                    "name": ds["name"],
                                    "type": ds["type"],
                                    "source": ds["source"],
                                    "display_name": ds["display_name"],
                                    "raw_data": ds.get("raw_data"),
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

                # 执行预览查询（最多100行）
                logger.info("Starting data preview (first 100 rows)...")
                self.status = i18n.t("components.input_output.databases.postgresql_input.status.previewing_data")

                connection_string = self._get_connection_string(datasource_id, datasource_info)

                # 使用 SQLAlchemy 查询
                engine = create_engine(connection_string, poolclass=NullPool)
                try:
                    with engine.connect() as conn:
                        # 执行查询（限制100行）
                        preview_query = f"{current_sql} LIMIT 100"
                        df = pd.read_sql_query(text(preview_query), conn)

                        # 生成 table_schema（列定义）
                        table_schema = []
                        for col in df.columns:
                            table_schema.append(
                                {
                                    "name": str(col),
                                    "display_name": str(col),
                                    "type": "str",
                                    "disable_edit": True,
                                }
                            )

                        # 将 DataFrame 转换为字典列表格式（TableInput 要求的格式）
                        preview_data = []
                        if not df.empty:
                            # 填充空值并转换为字典列表
                            preview_data = df.fillna("").to_dict("records")

                        # 更新 preview_table 配置
                        build_config["preview_table"]["table_schema"] = table_schema
                        build_config["preview_table"]["value"] = preview_data

                        logger.info(f"Data preview completed, retrieved {len(df)} rows")
                        self.status = i18n.t(
                            "components.input_output.databases.postgresql_input.status.preview_success", rows=len(df)
                        )

                finally:
                    engine.dispose()

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Data preview failed: {error_msg}")
                self.status = i18n.t(
                    "components.input_output.databases.postgresql_input.errors.preview_failed", error=error_msg
                )

        return build_config


class BaseSQLOutputComponent(BaseTableOutputComponent, ABC):
    """SQL 数据库输出的中间基类

    实现标准 SQL 数据库的通用功能：
    - 使用 SQLAlchemy inspect 发现表
    - 使用 pandas to_sql 写入数据
    - 支持不同写入模式（append/overwrite/fail）

    子类只需实现 _build_connection_string() 方法
    """

    def _load_tables(self) -> list[str]:
        """使用 SQLAlchemy inspect 加载表列表

        Returns:
            list[str]: 表名列表

        Raises:
            Exception: 如果连接失败或表发现失败
        """
        try:
            conn_str = self._build_connection_string()
            engine = create_engine(conn_str, poolclass=NullPool)

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            logger.info(f"{self.__class__.__name__} found {len(tables)} tables")
            return tables

        except Exception as e:
            logger.error(f"Error loading tables for {self.__class__.__name__}: {e}")
            raise

    async def _write_data(self, data: Data) -> Data:
        """使用 pandas to_sql 写入数据到 SQL 表

        Args:
            data: 要写入的数据

        Returns:
            Data: 写入结果数据

        Raises:
            Exception: 如果写入失败
        """
        try:
            # 验证必填字段
            self._validate_required_fields("table_name", "data_input")

            # 获取输入数据
            input_data = getattr(self, "data_input", None)
            if not input_data or not hasattr(input_data, "data"):
                raise ValueError("Invalid input data")

            df = input_data.data
            if not isinstance(df, pd.DataFrame):
                raise ValueError("Input data must be a pandas DataFrame")

            # 获取表名和写入模式
            table_name = getattr(self, "table_name", "")
            write_mode = getattr(self, "write_mode", "append")

            # 验证写入模式
            self._validate_write_mode(["append", "overwrite", "fail"])

            # 构建连接
            conn_str = self._build_connection_string()
            engine = create_engine(conn_str, poolclass=NullPool)

            # 处理写入模式
            if write_mode == "append":
                if_exists = "append"
            elif write_mode == "overwrite":
                if_exists = "replace"
            else:  # fail
                if_exists = "fail"

            # 获取批次大小（如果组件定义了）
            batch_size = getattr(self, "batch_size", 1000)

            logger.info(
                f"{self.__class__.__name__} writing {len(df)} rows to table '{table_name}' "
                f"with mode '{write_mode}' (batch_size={batch_size})"
            )

            # 写入数据
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists=if_exists,
                index=False,
                chunksize=batch_size,
            )

            logger.info(f"{self.__class__.__name__} successfully wrote {len(df)} rows to '{table_name}'")

            # 返回写入的数据
            return Data(
                data=df,
                metadata={
                    "table_name": table_name,
                    "rows_written": len(df),
                    "write_mode": write_mode,
                },
            )

        except Exception as e:
            logger.error(f"Error writing data for {self.__class__.__name__}: {e}")
            raise

    def _clear_table(self, table_name: str):
        """清空表数据（保留表结构）

        Args:
            table_name: 表名

        Raises:
            Exception: 如果清空失败
        """
        try:
            conn_str = self._build_connection_string()
            engine = create_engine(conn_str, poolclass=NullPool)

            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {table_name}"))
                conn.commit()

            logger.info(f"{self.__class__.__name__} cleared table '{table_name}'")

        except Exception as e:
            logger.error(f"Error clearing table '{table_name}': {e}")
            raise
