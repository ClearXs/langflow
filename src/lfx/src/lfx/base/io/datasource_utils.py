"""数据源公共工具模块

提供数据源加载、连接字符串构建等通用功能，
供所有表输入/输出组件使用。
"""

import asyncio
import concurrent.futures
import logging
import re
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def load_unified_datasources(datasource_manager=None) -> list[dict]:
    """加载统一的数据源列表（内置数据源 + 公共数据源）

    Args:
        datasource_manager: 数据源管理器（可选，用于legacy模式）

    Returns:
        list[dict]: 包含所有数据源的列表，每个数据源包含id、name、type、source等字段
    """
    try:
        # 获取内置数据源
        builtin_datasources = load_builtin_datasources()

        # 获取公共数据源
        try:
            # Use asyncio.get_event_loop().run_until_complete() to handle nested event loops
            try:
                loop = asyncio.get_running_loop()
                # Already in event loop, use ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, load_public_datasources())
                    public_datasources = future.result(timeout=5)
            except RuntimeError:
                # No running event loop, use asyncio.run()
                public_datasources = asyncio.run(load_public_datasources())
        except Exception as e:
            logger.warning(f"Failed to get public datasources: {e}")
            public_datasources = []

        # 合并数据源列表
        all_datasources = []

        # 添加内置数据源 - 包含完整连接参数（包括密码），用于本地构建连接字符串
        for ds in builtin_datasources:
            display_name = f"{ds['name']} ({ds['type']}) [自定义]"

            logger.debug(
                f"Adding builtin datasource {ds['name']}: "
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
                    # 包含预构建的连接字符串和参数，避免API调用
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
            # 从 dataSourceParam.type 获取正确的类型
            params = ds.get("dataSourceParam", {})
            ds_type = params.get("type") if isinstance(params, dict) else None
            if not ds_type:
                ds_type = ds.get("type") or ds.get("dataSourceType") or ds.get("dbType") or "mysql"

            display_name = build_display_name(ds, "public")
            all_datasources.append(
                {
                    "id": str(ds["id"]),
                    "name": ds["name"],
                    "type": ds_type,
                    "source": "public",
                    "display_name": display_name,
                    "raw_data": ds,
                }
            )

        logger.info(
            f"Loaded {len(all_datasources)} datasources "
            f"({len(builtin_datasources)} builtin, {len(public_datasources)} public)"
        )
        return all_datasources

    except Exception as e:
        logger.error(f"Error loading unified datasources: {e}")
        return []


def load_builtin_datasources() -> list[dict]:
    """获取内置数据源 - 直接从数据库读取，包含完整连接信息

    Returns:
        list[dict]: 内置数据源列表
    """
    logger.info("Loading builtin datasources from database")
    try:
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

                    logger.debug(f"Fetched {len(datasources)} datasources from database")

                    builtin_list = []
                    for ds in datasources:
                        logger.debug(
                            f"DB datasource {ds.name}: "
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
                logger.error(f"Error fetching datasources from database: {e}")
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

        logger.debug(f"Got {len(builtin_datasources)} builtin datasources from database")
        return builtin_datasources

    except Exception as e:
        logger.error(f"Error getting builtin datasources: {e}")
        return []


async def load_public_datasources() -> list[dict]:
    """通过feign接口获取公共数据源

    Returns:
        list[dict]: 公共数据源列表
    """
    try:
        from lfx.services.deps import get_feign_service
        from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

        feign_service = get_feign_service()
        client = DataConstructionFeignClient(feign_service)

        # 调用feign接口
        datasource_list = await client.get_datasource_list()

        logger.info(f"Got {len(datasource_list)} public datasources from feign API")
        return datasource_list if isinstance(datasource_list, list) else []

    except Exception as e:
        logger.error(f"Error getting public datasources: {e}")
        return []


def extract_connection_params(datasource: dict) -> dict:
    """从数据源对象提取连接参数

    Args:
        datasource: 数据源字典，可能是builtin或public类型

    Returns:
        dict: 包含host、port、database、username、password等连接参数
    """
    source = datasource.get("source", "builtin")

    if source == "builtin":
        # 内置数据源：直接返回已有参数
        return {
            "host": datasource.get("host"),
            "port": datasource.get("port"),
            "database": datasource.get("database"),
            "username": datasource.get("username"),
            "password": datasource.get("password"),
            "type": datasource.get("type"),
            "advanced_config": datasource.get("advanced_config"),
        }
    # 公共数据源：从raw_data中提取
    raw_data = datasource.get("raw_data", {})
    params = raw_data.get("dataSourceParam", {}) or raw_data.get("parameters", {})

    return {
        "host": params.get("host"),
        "port": params.get("port"),
        "database": params.get("database"),
        "username": params.get("username"),
        "password": params.get("password"),
        "type": params.get("type") or datasource.get("type"),
        "url": params.get("url"),  # Neo4j使用
    }


def build_connection_string(datasource: dict) -> str:
    """构建数据库连接字符串

    Args:
        datasource: 数据源字典

    Returns:
        str: SQLAlchemy格式的连接字符串
    """
    source = datasource.get("source", "builtin")
    ds_type = datasource.get("type", "").lower()

    if source == "builtin":
        # 内置数据源：直接使用已有参数构建
        params = extract_connection_params(datasource)
        return build_connection_string_from_params(ds_type, params)
    # 公共数据源：从raw_data构建
    raw_data = datasource.get("raw_data", {})
    return build_public_connection_string(raw_data)


def build_public_connection_string(raw_data: dict) -> str:
    """构建公共数据源连接字符串

    Args:
        raw_data: 公共数据源的原始数据

    Returns:
        str: 连接字符串
    """
    logger.debug(f"Building connection string from raw_data with keys: {list(raw_data.keys())}")

    # 获取数据源参数
    params = raw_data.get("dataSourceParam", {}) or raw_data.get("parameters", {})
    if not params:
        logger.warning("No dataSourceParam found in raw_data")
        params = {}

    logger.debug(f"Extracted params keys: {list(params.keys()) if isinstance(params, dict) else 'NOT A DICT'}")

    # 优先从 dataSourceParam.type 获取类型（公共数据源的实际位置）
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

    # 如果是空字符串或None，尝试从名称推断
    if not ds_type or (isinstance(ds_type, str) and ds_type.strip() == ""):
        logger.warning(f"Public datasource type is empty, raw_data sample: {dict(list(raw_data.items())[:3])}")
        # 尝试从datasource名称推断（作为最后的后备方案）
        ds_name = raw_data.get("name", "").lower()
        if "pg" in ds_name or "postgres" in ds_name:
            ds_type = "postgresql"
            logger.info(f"Inferred type 'postgresql' from name: {ds_name}")
        elif "mysql" in ds_name:
            ds_type = "mysql"
            logger.info(f"Inferred type 'mysql' from name: {ds_name}")
        elif "hive" in ds_name:
            ds_type = "hive"
            logger.info(f"Inferred type 'hive' from name: {ds_name}")
        else:
            # 最后的默认值
            ds_type = "postgresql"
            logger.warning("Cannot infer type, using default: postgresql")

    ds_type = ds_type.lower().strip()
    logger.info(f"Using datasource type: {ds_type}")

    if ds_type == "hive":
        # Hive连接字符串构建 - 使用 SQLAlchemy 格式
        host = params.get("host", "localhost")
        port = params.get("port", 10000)
        database = params.get("database", "default")
        username = params.get("username", "hive")
        password = params.get("password", "")

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if username and password:
            conn_str = f"hive://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        elif username:
            conn_str = f"hive://{username_encoded}@{host}:{port}/{database}"
        else:
            conn_str = f"hive://{host}:{port}/{database}"

        logger.debug(f"Built Hive connection string (SQLAlchemy format): {conn_str.replace(password, '***')}")
        return conn_str

    # 其他数据源类型的连接字符串构建（MySQL, PostgreSQL等）
    return build_connection_string_from_params(ds_type, params)


def build_connection_string_from_params(ds_type: str, params: dict) -> str:
    """从参数构建连接字符串

    支持的数据库类型: MySQL, PostgreSQL, Hive, Neo4j, MongoDB, ClickHouse, Doris, Oracle, SQLServer

    Args:
        ds_type: 数据库类型（小写）
        params: 连接参数字典

    Returns:
        str: SQLAlchemy格式的连接字符串
    """
    logger.debug(f"Building connection string for type={ds_type}, params keys={list(params.keys())}")

    # Neo4j特殊处理：使用URL而不是host/port
    if ds_type == "neo4j":
        url = params.get("url", "")
        username = params.get("username", "")
        password = params.get("password", "")

        if not url:
            raise ValueError(
                f"Missing required 'url' parameter for Neo4j datasource. Available params: {list(params.keys())}"
            )

        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        # 从URL中提取host和port（用于连接字符串构建）
        match = re.match(r"bolt://([^:]+):(\d+)", url)
        if not match:
            raise ValueError(f"Invalid Neo4j URL format: {url}. Expected: bolt://host:port")

        host = match.group(1)
        port = int(match.group(2))

        if username and password:
            conn_str = f"bolt://{username_encoded}:{password_encoded}@{host}:{port}"
        else:
            conn_str = f"bolt://{host}:{port}"

        logger.info(f"Built Neo4j connection string: bolt://{username_encoded}:***@{host}:{port}")
        return conn_str

    # 其他数据源：验证必填字段host和port
    if not params.get("host"):
        raise ValueError(
            f"Missing required 'host' parameter for {ds_type} datasource. Available params: {list(params.keys())}"
        )
    if not params.get("port"):
        raise ValueError(
            f"Missing required 'port' parameter for {ds_type} datasource. Available params: {list(params.keys())}"
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
    elif ds_type == "oracle":
        # Oracle connection using cx_Oracle driver
        conn_str = f"oracle+cx_oracle://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
    elif ds_type == "sqlserver":
        # SQL Server connection using pyodbc driver
        conn_str = f"mssql+pyodbc://{username_encoded}:{password_encoded}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {ds_type}")

    # 记录构建的连接字符串（隐藏密码）
    safe_conn_str = re.sub(r"://([^:]+):([^@]*)@", r"://\1:***@", conn_str)
    logger.info(f"Built connection string for {ds_type}: {safe_conn_str}")

    return conn_str


def get_default_port(ds_type: str) -> int:
    """获取数据源的默认端口

    Args:
        ds_type: 数据库类型

    Returns:
        int: 默认端口号
    """
    default_ports = {
        "mysql": 3306,
        "postgresql": 5432,
        "hive": 10000,
        "neo4j": 7687,
        "oracle": 1521,
        "sqlserver": 1433,
        "clickhouse": 8123,
        "mongodb": 27017,
        "doris": 9030,
    }
    return default_ports.get(ds_type.lower(), 3306)


def build_display_name(datasource: dict, source: str) -> str:
    """构建数据源的显示名称

    Args:
        datasource: 数据源字典
        source: 数据源类型（"builtin" 或 "public"）

    Returns:
        str: 格式化的显示名称
    """
    base_name = f"{datasource['name']} ({datasource['type']})"

    # 来源标识
    if source == "public":
        return f"{base_name} [公共]"
    if source == "builtin":
        return f"{base_name} [自定义]"
    return base_name


def extract_uuid_from_id(datasource_id: str) -> str:
    """从数据源ID中提取纯UUID，移除可能的前缀

    Args:
        datasource_id: 数据源ID（可能包含前缀）

    Returns:
        str: 提取后的UUID
    """
    if not datasource_id:
        return datasource_id

    # 检查是否有前缀（如 custom_, enterprise_ 等）
    if "_" in datasource_id:
        parts = datasource_id.split("_", 1)
        if len(parts) == 2:
            prefix, uuid_part = parts
            # 验证uuid_part是否符合UUID格式（包含-字符且长度正确）
            if "-" in uuid_part and len(uuid_part) == 36:  # UUID标准格式长度为36个字符
                logger.debug(f"Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                return uuid_part

    return datasource_id


def infer_pandas_types(df: Any) -> dict[str, str]:
    """推断 Pandas DataFrame 的字段类型（支持 GeoDataFrame 空间类型）

    Args:
        df: Pandas DataFrame 或 GeoDataFrame

    Returns:
        dict: 字段名到类型的映射
    """
    import pandas as pd

    type_mapping = {}

    for col in df.columns:
        dtype = df[col].dtype

        # ===== 新增：检测 GeoDataFrame 几何列 =====
        # 检查是否为 GeoDataFrame 并且当前列是几何列
        if hasattr(df, "geometry") and col == getattr(df, "_geometry_column_name", "geometry"):
            # 检测几何类型
            try:
                geom_types = df[col].geom_type.unique()
                if len(geom_types) == 1:
                    geom_type = geom_types[0].upper()
                    if geom_type == "POINT":
                        type_mapping[col] = "POINT"
                    elif geom_type == "LINESTRING":
                        type_mapping[col] = "LINESTRING"
                    elif geom_type == "POLYGON":
                        type_mapping[col] = "POLYGON"
                    elif geom_type == "MULTIPOINT":
                        type_mapping[col] = "MULTIPOINT"
                    elif geom_type == "MULTILINESTRING":
                        type_mapping[col] = "MULTILINESTRING"
                    elif geom_type == "MULTIPOLYGON":
                        type_mapping[col] = "MULTIPOLYGON"
                    else:
                        type_mapping[col] = "GEOMETRY"
                else:
                    # 混合几何类型
                    type_mapping[col] = "GEOMETRY"
            except Exception:
                # 如果无法获取几何类型，默认为 GEOMETRY
                type_mapping[col] = "GEOMETRY"
            continue
        # ===== 以上为新增代码 =====

        if pd.api.types.is_integer_dtype(dtype):
            type_mapping[col] = "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            type_mapping[col] = "FLOAT"
        elif pd.api.types.is_bool_dtype(dtype):
            type_mapping[col] = "BOOLEAN"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            type_mapping[col] = "DATETIME"
        else:
            type_mapping[col] = "STRING"

    return type_mapping
