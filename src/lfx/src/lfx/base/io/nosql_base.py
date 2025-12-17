"""NoSQL 数据库输入/输出组件的中间基类

为 NoSQL 数据库（MongoDB、Neo4j、ClickHouse 等）提供基础框架。

与 SQL 数据库不同，NoSQL 数据库的实现差异较大：
- MongoDB: 使用 pymongo 驱动，集合概念
- Neo4j: 使用 neo4j 驱动，图数据库，节点/关系概念
- ClickHouse: 使用 clickhouse-connect，列式存储

因此这个基类主要提供接口定义，具体实现由子类完成。
"""

import logging
from abc import ABC

from lfx.base.io.table_base import BaseTableInputComponent, BaseTableOutputComponent

logger = logging.getLogger(__name__)


class BaseNoSQLInputComponent(BaseTableInputComponent, ABC):
    """NoSQL 数据库输入的中间基类

    NoSQL 数据库的差异较大，这个基类主要提供：
    1. 统一的接口定义
    2. 通用的错误处理框架
    3. 日志记录

    子类需要实现：
    - _build_connection_string(): 构建连接字符串
    - _load_tables(): 加载集合/标签列表（具体名称取决于数据库类型）
    - _read_data(): 读取数据

    示例子类：
    - MongoDBInput: 使用 pymongo，加载集合列表
    - Neo4jInput: 使用 neo4j驱动，加载标签列表
    - ClickHouseInput: 使用 clickhouse-connect，加载表列表
    """

    def _log_operation_start(self, operation: str, **kwargs):
        """记录操作开始

        Args:
            operation: 操作名称（如 "read", "query", "fetch"）
            **kwargs: 额外的日志参数
        """
        params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"{self.__class__.__name__} starting {operation} operation ({params_str})")

    def _log_operation_end(self, operation: str, result_count: int = 0):
        """记录操作结束

        Args:
            operation: 操作名称
            result_count: 结果数量
        """
        logger.info(f"{self.__class__.__name__} completed {operation} operation (result_count={result_count})")


class BaseNoSQLOutputComponent(BaseTableOutputComponent, ABC):
    """NoSQL 数据库输出的中间基类

    NoSQL 数据库的写入模式差异较大，这个基类主要提供：
    1. 统一的接口定义
    2. 通用的错误处理框架
    3. 日志记录

    子类需要实现：
    - _build_connection_string(): 构建连接字符串
    - _load_tables(): 加载集合/标签列表
    - _write_data(): 写入数据（根据数据库特性实现不同的写入模式）

    示例子类：
    - MongoDBOutput: 使用 pymongo，支持 insert/update/upsert
    - Neo4jOutput: 使用 neo4j 驱动，支持 batch_insert/append/upsert/replace
    - ClickHouseOutput: 使用 clickhouse-connect，批量写入
    """

    def _log_operation_start(self, operation: str, **kwargs):
        """记录操作开始

        Args:
            operation: 操作名称（如 "write", "insert", "update"）
            **kwargs: 额外的日志参数
        """
        params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"{self.__class__.__name__} starting {operation} operation ({params_str})")

    def _log_operation_end(self, operation: str, affected_count: int = 0):
        """记录操作结束

        Args:
            operation: 操作名称
            affected_count: 受影响的记录数
        """
        logger.info(f"{self.__class__.__name__} completed {operation} operation (affected_count={affected_count})")

    def _validate_nosql_write_mode(self, allowed_modes: list[str]):
        """验证 NoSQL 数据库的写入模式

        NoSQL 数据库的写入模式可能与 SQL 不同：
        - MongoDB: insert, update, upsert, replace
        - Neo4j: batch_insert, append, upsert, replace
        - ClickHouse: append, replace

        Args:
            allowed_modes: 当前数据库允许的写入模式列表

        Raises:
            ValueError: 如果写入模式不在允许列表中
        """
        write_mode = getattr(self, "write_mode", None)
        if write_mode not in allowed_modes:
            raise ValueError(
                f"Invalid write_mode '{write_mode}' for {self.__class__.__name__}. "
                f"Allowed modes: {', '.join(allowed_modes)}"
            )
