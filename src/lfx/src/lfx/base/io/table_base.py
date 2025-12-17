"""表输入/输出组件的抽象基类

定义所有数据库表输入/输出组件的通用接口和公共功能。
"""

import logging
from abc import ABC, abstractmethod

import pandas as pd

from lfx.base.io import datasource_utils
from lfx.custom.custom_component.component import Component
from lfx.schema import Data

logger = logging.getLogger(__name__)


class BaseTableInputComponent(Component, ABC):
    """所有表输入组件的抽象基类

    封装公共功能：
    1. 数据源元数据加载（builtin + public）
    2. 连接字符串构建框架
    3. 表/集合发现框架
    4. 数据读取框架
    5. 字段类型推断
    """

    # 子类需要设置这个类属性，指定数据源类型
    DATASOURCE_TYPE: str = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_obj = None

    # ==================== 抽象方法（子类必须实现） ====================

    @abstractmethod
    def _build_connection_string(self) -> str:
        """构建特定数据库的连接字符串

        Returns:
            str: SQLAlchemy格式的连接字符串

        Raises:
            NotImplementedError: 子类必须实现
        """

    @abstractmethod
    def _load_tables(self) -> list[str]:
        """加载数据库中的表/集合列表

        Returns:
            list[str]: 表名或集合名列表

        Raises:
            NotImplementedError: 子类必须实现
        """

    @abstractmethod
    async def _read_data(self) -> list[Data]:
        """从表中读取数据

        Returns:
            list[Data]: Data对象列表，每个Data对象包含一行数据的字典

        Raises:
            NotImplementedError: 子类必须实现
        """

    # ==================== 公共方法（所有子类共享） ====================

    def _load_datasource_metadata(self) -> list[dict]:
        """加载数据源元数据（builtin + public）

        使用 datasource_utils 统一加载所有数据源，
        然后根据 DATASOURCE_TYPE 进行过滤。

        Returns:
            list[dict]: 符合当前组件类型的数据源列表
        """
        try:
            # 加载所有数据源
            all_datasources = datasource_utils.load_unified_datasources()

            # 如果没有指定类型，返回所有数据源
            if not self.DATASOURCE_TYPE:
                logger.warning(f"{self.__class__.__name__} does not specify DATASOURCE_TYPE, returning all datasources")
                return all_datasources

            # 过滤出匹配当前组件类型的数据源
            filtered = [ds for ds in all_datasources if ds.get("type", "").lower() == self.DATASOURCE_TYPE.lower()]

            logger.info(
                f"{self.__class__.__name__} loaded {len(filtered)} {self.DATASOURCE_TYPE} datasources "
                f"(out of {len(all_datasources)} total)"
            )
            return filtered

        except Exception as e:
            logger.error(f"Error loading datasource metadata for {self.__class__.__name__}: {e}")
            return []

    def _extract_connection_params(self, datasource: dict) -> dict:
        """从数据源对象提取连接参数

        Args:
            datasource: 数据源字典

        Returns:
            dict: 包含连接参数的字典
        """
        return datasource_utils.extract_connection_params(datasource)

    def _infer_field_types(self, df: pd.DataFrame) -> dict[str, str]:
        """推断 DataFrame 字段类型

        Args:
            df: Pandas DataFrame

        Returns:
            dict: 字段名到类型的映射
        """
        return datasource_utils.infer_pandas_types(df)

    def _get_datasource_by_id(self, datasource_id: str) -> dict | None:
        """根据ID获取数据源对象

        Args:
            datasource_id: 数据源ID

        Returns:
            dict: 数据源字典，如果不存在返回None
        """
        all_datasources = self._load_datasource_metadata()
        for ds in all_datasources:
            if str(ds.get("id")) == str(datasource_id):
                return ds
        return None

    def _validate_required_fields(self, *field_names):
        """验证必填字段

        Args:
            *field_names: 字段名列表

        Raises:
            ValueError: 如果任何字段为空
        """
        for field_name in field_names:
            value = getattr(self, field_name, None)
            if not value:
                raise ValueError(f"Required field '{field_name}' is missing or empty")

    # ==================== 字段推断和SQL分析方法 ====================

    def _get_datasource_id_from_metadata(self, selector_value: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据选择器值获取数据源ID

        Args:
            selector_value: 选择器的值（通常是数据源ID）
            options_metadata: 元数据列表

        Returns:
            数据源ID，如果未找到则返回None
        """
        logger.debug(f"Looking for datasource ID from selector value: '{selector_value}'")
        logger.debug(f"Available metadata entries: {len(options_metadata)}")

        if not options_metadata:
            logger.warning("No options_metadata provided")
            return None

        # selector_value 直接就是ID
        for metadata in options_metadata:
            if metadata.get("id") == selector_value or metadata.get("value") == selector_value:
                logger.info(f"Found valid datasource ID: '{selector_value}'")
                return selector_value

        # 向后兼容：按显示名称查找
        logger.warning(f"Trying legacy lookup by display name for: '{selector_value}'")
        for metadata in options_metadata:
            if metadata.get("display_name") == selector_value:
                datasource_id = metadata.get("id")
                logger.info(f"Found datasource ID '{datasource_id}' for display name '{selector_value}'")
                return datasource_id

        logger.error(f"No metadata found for selector value: '{selector_value}'")
        return None

    def _parse_sql_fields(self, sql: str) -> list[str]:
        """从SQL中解析字段名

        Args:
            sql: SQL查询语句

        Returns:
            字段名列表，如果是SELECT *则返回["*"]
        """
        import sqlparse

        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                logger.warning("SQL parsing returned empty result")
                return []

            stmt = parsed[0]
            fields = []
            in_select = False

            for token in stmt.tokens:
                if token.is_whitespace or isinstance(token, sqlparse.sql.Comment):
                    continue

                if token.ttype is sqlparse.tokens.Keyword.DML and token.value.upper() == "SELECT":
                    in_select = True
                    continue

                if in_select and token.ttype is sqlparse.tokens.Keyword:
                    break

                if in_select:
                    if isinstance(token, sqlparse.sql.IdentifierList):
                        for identifier in token.get_identifiers():
                            field_name = self._extract_field_name(identifier)
                            if field_name and field_name != "*":
                                fields.append(field_name)
                            elif field_name == "*":
                                return ["*"]
                    elif isinstance(token, sqlparse.sql.Identifier):
                        field_name = self._extract_field_name(token)
                        if field_name:
                            fields.append(field_name)
                    elif token.ttype is sqlparse.tokens.Wildcard:
                        return ["*"]

            logger.debug(f"Parsed fields from SQL: {fields}")
            return fields

        except Exception as e:
            logger.error(f"SQL parsing error: {e}")
            return []

    def _extract_field_name(self, identifier) -> str:
        """提取字段名（处理别名）

        Args:
            identifier: sqlparse Identifier对象

        Returns:
            字段名或别名
        """
        try:
            if identifier.has_alias():
                alias = identifier.get_alias()
                logger.debug(f"Field has alias: {alias}")
                return alias

            real_name = identifier.get_real_name()

            if identifier.ttype is None and "(" in str(identifier):
                return str(identifier).strip()

            return real_name
        except Exception as e:
            logger.error(f"Error extracting field name: {e}")
            return str(identifier).strip()

    def _get_connection_string(self, datasource_id: str, datasource_info: dict = None) -> str:
        """获取数据源连接字符串

        Args:
            datasource_id: 数据源ID
            datasource_info: 数据源信息字典（可选）

        Returns:
            连接字符串

        Raises:
            ValueError: 如果缺少必要信息
        """
        if not datasource_info:
            raise ValueError(f"Missing datasource_info for datasource_id: {datasource_id}")

        source = datasource_info.get("source")
        ds_type = datasource_info.get("type", "").lower()

        logger.info(f"Building connection string for {source} datasource (type={ds_type})")

        return datasource_utils.build_connection_string(datasource_info)

    def _map_dtype(self, dtype) -> str:
        """将 pandas dtype 映射到通用类型名

        Args:
            dtype: Pandas dtype对象

        Returns:
            类型名称字符串 ("string", "integer", "float", "boolean", "datetime")
        """
        dtype_str = str(dtype)

        if "int" in dtype_str:
            return "integer"
        if "float" in dtype_str or "double" in dtype_str:
            return "float"
        if "bool" in dtype_str:
            return "boolean"
        if "datetime" in dtype_str or "timestamp" in dtype_str:
            return "datetime"
        return "string"

    def _infer_field_info(self, datasource_id: str, sql: str) -> list[dict]:
        """解析SQL并推断字段信息（执行LIMIT 1查询）

        Args:
            datasource_id: 数据源ID
            sql: SQL查询语句

        Returns:
            字段信息列表，每个元素包含 source_field, data_type, null_value, transformation_rule
        """
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool

        try:
            # 1. 解析SQL字段
            logger.debug(f"Parsing SQL: {sql[:100]}...")
            fields = self._parse_sql_fields(sql)

            if not fields:
                logger.warning("No fields parsed from SQL")
                return []

            # 2. 获取数据库连接
            datasource_info = None
            if hasattr(self, "_current_datasource_info"):
                datasource_info = self._current_datasource_info

            connection_string = self._get_connection_string(datasource_id, datasource_info)

            # 检查数据源类型
            is_mongodb = datasource_info and datasource_info.get("type", "").lower() == "mongodb"
            is_neo4j = datasource_info and datasource_info.get("type", "").lower() == "neo4j"

            if is_mongodb:
                logger.warning("MongoDB does not support SQL - skipping field inference")
                raise ValueError("MongoDB does not support SQL queries. Please use MongoDB query syntax.")

            if is_neo4j:
                logger.warning("Neo4j uses Cypher, not SQL - skipping field inference")
                raise ValueError("Neo4j uses Cypher query language, not SQL. Please use Cypher syntax.")

            # 使用 SQLAlchemy
            engine = create_engine(connection_string, poolclass=NullPool)

            try:
                with engine.connect() as conn:
                    # 3. 如果是 *, 需要执行查询获取实际列名
                    if fields == ["*"]:
                        logger.debug("Wildcard detected, executing LIMIT 0 to get columns")
                        df = pd.read_sql_query(text(f"{sql} LIMIT 0"), conn)
                        fields = df.columns.tolist()
                        logger.debug(f"Actual columns: {fields}")

                    # 4. 执行 LIMIT 1 获取样本数据，推断类型
                    logger.debug("Executing LIMIT 1 to infer types")
                    df_sample = pd.read_sql_query(text(f"{sql} LIMIT 1"), conn)

                    # 5. 为每个字段创建映射配置
                    field_info = []
                    for field in fields:
                        if field in df_sample.columns:
                            dtype = df_sample[field].dtype
                            data_type = self._map_dtype(dtype)
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

                    logger.info(f"Inferred {len(field_info)} fields")
                    return field_info

            finally:
                engine.dispose()

        except Exception as e:
            logger.error(f"Field inference failed: {e}")
            raise


class BaseTableOutputComponent(Component, ABC):
    """所有表输出组件的抽象基类

    封装公共功能：
    1. 数据源元数据加载
    2. 连接字符串构建框架
    3. 表/集合发现框架
    4. 数据写入框架
    5. 写入模式处理（append/overwrite/fail）
    """

    # 子类需要设置这个类属性，指定数据源类型
    DATASOURCE_TYPE: str = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_obj = None

    # ==================== 抽象方法（子类必须实现） ====================

    @abstractmethod
    def _build_connection_string(self) -> str:
        """构建特定数据库的连接字符串

        Returns:
            str: SQLAlchemy格式的连接字符串

        Raises:
            NotImplementedError: 子类必须实现
        """

    @abstractmethod
    def _load_tables(self) -> list[str]:
        """加载数据库中的表/集合列表

        Returns:
            list[str]: 表名或集合名列表

        Raises:
            NotImplementedError: 子类必须实现
        """

    @abstractmethod
    async def _write_data(self, data: Data) -> Data:
        """写入数据到表

        Args:
            data: 要写入的数据

        Returns:
            Data: 写入结果数据

        Raises:
            NotImplementedError: 子类必须实现
        """

    # ==================== 公共方法（所有子类共享） ====================

    def _load_datasource_metadata(self) -> list[dict]:
        """加载数据源元数据（builtin + public）

        使用 datasource_utils 统一加载所有数据源，
        然后根据 DATASOURCE_TYPE 进行过滤。

        Returns:
            list[dict]: 符合当前组件类型的数据源列表
        """
        try:
            # 加载所有数据源
            all_datasources = datasource_utils.load_unified_datasources()

            # 如果没有指定类型，返回所有数据源
            if not self.DATASOURCE_TYPE:
                logger.warning(f"{self.__class__.__name__} does not specify DATASOURCE_TYPE, returning all datasources")
                return all_datasources

            # 过滤出匹配当前组件类型的数据源
            filtered = [ds for ds in all_datasources if ds.get("type", "").lower() == self.DATASOURCE_TYPE.lower()]

            logger.info(
                f"{self.__class__.__name__} loaded {len(filtered)} {self.DATASOURCE_TYPE} datasources "
                f"(out of {len(all_datasources)} total)"
            )
            return filtered

        except Exception as e:
            logger.error(f"Error loading datasource metadata for {self.__class__.__name__}: {e}")
            return []

    def _extract_connection_params(self, datasource: dict) -> dict:
        """从数据源对象提取连接参数

        Args:
            datasource: 数据源字典

        Returns:
            dict: 包含连接参数的字典
        """
        return datasource_utils.extract_connection_params(datasource)

    def _get_datasource_by_id(self, datasource_id: str) -> dict | None:
        """根据ID获取数据源对象

        Args:
            datasource_id: 数据源ID

        Returns:
            dict: 数据源字典，如果不存在返回None
        """
        all_datasources = self._load_datasource_metadata()
        for ds in all_datasources:
            if str(ds.get("id")) == str(datasource_id):
                return ds
        return None

    def _validate_required_fields(self, *field_names):
        """验证必填字段

        Args:
            *field_names: 字段名列表

        Raises:
            ValueError: 如果任何字段为空
        """
        for field_name in field_names:
            value = getattr(self, field_name, None)
            if not value:
                raise ValueError(f"Required field '{field_name}' is missing or empty")

    def _validate_write_mode(self, allowed_modes: list[str] = None):
        """验证写入模式

        Args:
            allowed_modes: 允许的写入模式列表，默认为 ["append", "overwrite", "fail"]

        Raises:
            ValueError: 如果写入模式不在允许列表中
        """
        if allowed_modes is None:
            allowed_modes = ["append", "overwrite", "fail"]

        write_mode = getattr(self, "write_mode", None)
        if write_mode not in allowed_modes:
            raise ValueError(f"Invalid write_mode '{write_mode}'. Allowed modes: {', '.join(allowed_modes)}")
