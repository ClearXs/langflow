import asyncio
import datetime
from typing import Any

import i18n
import sqlparse
from lfx.custom.custom_component.component import Component
from lfx.io import CodeInput, DropdownInput, IntInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFlinkSQLComponent(Component):
    """Flink SQL component for executing Flink SQL statements."""

    display_name = i18n.t("components.computations.flink_sql.display_name")
    description = i18n.t("components.computations.flink_sql.description")
    icon = "Database"
    name = "FlinkSQL"

    # Enable universal input
    include_universal_input = True

    inputs = [
        DropdownInput(
            name="flink_datasource",
            display_name=i18n.t("components.computations.flink_sql.flink_datasource.display_name"),
            info=i18n.t("components.computations.flink_sql.flink_datasource.info"),
            required=True,
            refresh_button=True,
            real_time_refresh=True,
            options=[],
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        DropdownInput(
            name="execution_mode",
            display_name=i18n.t("components.computations.flink_sql.execution_mode.display_name"),
            info=i18n.t("components.computations.flink_sql.execution_mode.info"),
            options=["streaming", "batch"],
            value="streaming",
            required=True,
        ),
        CodeInput(
            name="sql_script",
            display_name=i18n.t("components.computations.flink_sql.sql_script.display_name"),
            info=i18n.t("components.computations.flink_sql.sql_script.info"),
            required=True,
            language="sql",
            value="""-- Word Count Example - Flink SQL (Batch Mode)
-- 注意：需要预先创建 /tmp/input.csv 文件，每行一个单词

-- 创建源表（从 CSV 文件读取单词）
CREATE TABLE word_source (
    word STRING
) WITH (
    'connector.type' = 'filesystem',
    'format.type' = 'csv',
    'connector.path' = '/tmp/input.csv'
);

-- 创建目标表（将统计结果写入 CSV）
CREATE TABLE word_count_sink (
    word STRING,
    count_value BIGINT
) WITH (
    'connector.type' = 'filesystem',
    'format.type' = 'csv',
    'connector.path' = '/tmp/wordcount_output.csv'
);

-- Word Count 查询（注意：Flink 1.9 中此语句只会被注册，不会立即执行）
INSERT INTO word_count_sink
SELECT word, COUNT(*) as count_value
FROM word_source
GROUP BY word;""",
        ),
        IntInput(
            name="parallelism",
            display_name=i18n.t("components.computations.flink_sql.parallelism.display_name"),
            info=i18n.t("components.computations.flink_sql.parallelism.info"),
            value=1,
            advanced=True,
        ),
        IntInput(
            name="checkpoint_interval",
            display_name=i18n.t("components.computations.flink_sql.checkpoint_interval.display_name"),
            info=i18n.t("components.computations.flink_sql.checkpoint_interval.info"),
            value=10000,
            advanced=True,
        ),
        TableInput(
            name="execution_results",
            display_name=i18n.t("components.computations.flink_sql.execution_results.display_name"),
            table_schema=[
                {"name": "statement_index", "display_name": "序号", "type": "int", "disable_edit": True},
                {"name": "statement_type", "display_name": "语句类型", "type": "str", "disable_edit": True},
                {"name": "sql_statement", "display_name": "SQL 语句", "type": "str", "disable_edit": True},
                {"name": "execution_status", "display_name": "执行状态", "type": "str", "disable_edit": True},
                {"name": "rows_affected", "display_name": "影响行数", "type": "str", "disable_edit": True},
                {"name": "error_message", "display_name": "错误信息", "type": "str", "disable_edit": True},
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "execute_sql",
                        "label": i18n.t("components.computations.flink_sql.execute_button"),
                        "icon": "Play",
                        "position": "top",
                    }
                ],
            },
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.computations.flink_sql.output.display_name"),
            method="execute_flink_sql",
        ),
    ]

    def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Handle field changes and action button clicks."""

        # Load Flink datasources
        if field_name is None or (field_name == "flink_datasource" and not field_value):
            datasources = self._load_flink_datasources()
            build_config["flink_datasource"]["options"] = [ds["display_name"] for ds in datasources]
            build_config["flink_datasource"]["options_metadata"] = datasources

        # Handle "Execute SQL" button click
        if field_name == "execution_results" and action == "execute_sql":
            try:
                datasource_id = self.flink_datasource
                sql_script = self.sql_script
                execution_mode = self.execution_mode
                parallelism = self.parallelism
                checkpoint_interval = self.checkpoint_interval

                if not datasource_id:
                    raise ValueError(i18n.t("components.computations.flink_sql.error.no_datasource"))

                if not sql_script or not sql_script.strip():
                    raise ValueError(i18n.t("components.computations.flink_sql.error.no_sql"))

                # Execute SQL statements
                results = self._execute_sql_statements(
                    datasource_id, sql_script, execution_mode, parallelism, checkpoint_interval
                )

                # Update results table
                build_config["execution_results"]["value"] = results
                success_count = sum(1 for r in results if r["execution_status"] == "成功")
                total_count = len(results)
                self.status = self._format_i18n(
                    "components.computations.flink_sql.status.success", success=success_count, total=total_count
                )

            except Exception as e:
                error_msg = str(e)
                self.status = f"{i18n.t('components.computations.flink_sql.status.error')}: {error_msg}"
                build_config["execution_results"]["value"] = [
                    {
                        "statement_index": 1,
                        "statement_type": "ERROR",
                        "sql_statement": "N/A",
                        "execution_status": "失败",
                        "rows_affected": "",
                        "error_message": error_msg,
                    }
                ]

        return build_config

    def _load_flink_datasources(self) -> list[dict]:
        """Load unified Flink datasources (builtin + public)."""
        try:
            builtin_datasources = self._get_builtin_flink_datasources()
            public_datasources = self._get_public_flink_clusters()

            # Combine both lists
            all_datasources = builtin_datasources + public_datasources

            logger.info(
                f"Loaded {len(builtin_datasources)} builtin and {len(public_datasources)} public Flink datasources"
            )

            return all_datasources

        except Exception as e:
            logger.error(f"Failed to load Flink datasources: {e}")
            return []

    def _extract_uuid_from_id(self, datasource_id: str) -> str:
        """Extract UUID from datasource ID if it has a prefix."""
        if "_" in datasource_id:
            parts = datasource_id.split("_", 1)
            if len(parts) == 2:
                prefix, uuid_part = parts
                # Verify uuid_part is valid UUID format
                if "-" in uuid_part and len(uuid_part) == 36:
                    logger.debug(f"[FlinkSQL] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                    return uuid_part

        # If no prefix or not valid UUID format, return as-is
        return datasource_id

    def _get_builtin_flink_datasources(self) -> list[dict]:
        """Get builtin (custom) Flink datasources."""
        try:
            from lfx.base.datasource.manager import DataSourceManager

            # Initialize datasource manager
            if not hasattr(self, "datasource_manager"):
                self.datasource_manager = DataSourceManager()

            # Get datasources using correct API
            datasources = asyncio.run(self.datasource_manager.get_datasources())
            flink_datasources = []

            logger.debug(f"[FlinkSQL] Got enterprise datasources: {len(datasources.get('enterprise', []))}")
            logger.debug(f"[FlinkSQL] Got custom datasources: {len(datasources.get('custom', []))}")

            # Merge enterprise and custom datasources
            for ds in datasources.get("enterprise", []) + datasources.get("custom", []):
                datasource_id = self._extract_uuid_from_id(ds["id"])
                ds_name = ds.get("name", "Unknown")
                ds_type = ds.get("type", "")

                logger.debug(f"[FlinkSQL] Datasource: id={datasource_id}, name={ds_name}, type={ds_type}")

                # Filter by Flink type (case-insensitive)
                ds_type_lower = ds_type.lower() if ds_type else ""
                if "flink" in ds_type_lower:
                    logger.info(f"[FlinkSQL] ✓ Including Flink datasource: {ds_name} (type={ds_type})")
                    flink_datasources.append(
                        {
                            "value": str(datasource_id),
                            "label": f"{ds_name} ({ds_type}) [自定义]",
                            "display_name": f"{ds_name} ({ds_type}) [自定义]",
                            "id": str(datasource_id),
                            "name": ds_name,
                            "type": ds_type,
                            "source": "builtin",
                            # No raw_data for builtin datasources
                        }
                    )
                else:
                    logger.debug(f"[FlinkSQL] ✗ Skipping non-Flink datasource: {ds_name} (type={ds_type})")

            logger.info(f"[FlinkSQL] Filtered Flink datasources count: {len(flink_datasources)}")
            return flink_datasources

        except Exception as e:
            logger.exception(f"[FlinkSQL] Failed to load builtin Flink datasources: {e}")
            return []

    def _get_public_flink_clusters(self) -> list[dict]:
        """Get public Flink clusters from data-stream service."""
        try:
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.data_stream import DataStreamFeignClient

            feign_service = get_feign_service()
            client = DataStreamFeignClient(feign_service)

            # Async call to get cluster list
            cluster_list = asyncio.run(client.get_flink_cluster_list())

            public_datasources = []
            for cluster in cluster_list:
                cluster_id = cluster.get("id")
                cluster_name = cluster.get("name", "Unknown")
                version = cluster.get("version", "")
                execution_mode = cluster.get("executionMode", "")
                status = "Active" if cluster.get("status") == 1 else "Inactive"

                # Build display name with version, mode, and status
                display_name = self._build_flink_cluster_display_name(
                    cluster_name, version, execution_mode, status
                )

                public_datasources.append(
                    {
                        "value": str(cluster_id),
                        "label": display_name,
                        "display_name": display_name,
                        "id": str(cluster_id),
                        "name": cluster_name,
                        "type": "Flink",
                        "source": "public",
                        "raw_data": cluster,  # Store full cluster data for connection info
                    }
                )

            logger.info(f"[FlinkSQL] Loaded {len(public_datasources)} public Flink clusters")
            return public_datasources

        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to load public Flink clusters: {e}")
            return []

    def _build_flink_cluster_display_name(
        self, name: str, version: str, execution_mode: str, status: str
    ) -> str:
        """Build display name for public Flink cluster."""
        parts = [f"{name} (Flink"]

        if version:
            parts.append(f" {version}")

        parts.append(") [公共]")

        if execution_mode:
            parts.append(f" [{execution_mode}]")

        if status:
            parts.append(f" [{status}]")

        return "".join(parts)

    def _find_datasource_by_id(self, datasource_id: str) -> dict | None:
        """Find datasource in cached options_metadata."""
        try:
            # Access cached metadata from update_build_config
            if hasattr(self, "_input_dict") and self._input_dict:
                flink_datasource_input = self._input_dict.get("flink_datasource")
                if flink_datasource_input and hasattr(flink_datasource_input, "options_metadata"):
                    options_metadata = flink_datasource_input.options_metadata
                    if options_metadata:
                        for ds in options_metadata:
                            if str(ds.get("id")) == str(datasource_id):
                                return ds
        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to find datasource in metadata: {e}")

        return None

    def _get_flink_connection_info(self, datasource_id: str) -> dict:
        """Get Flink connection information from datasource."""
        try:
            # Find datasource in metadata
            datasource = self._find_datasource_by_id(datasource_id)

            if not datasource:
                logger.warning(f"[FlinkSQL] Datasource not found in metadata: {datasource_id}, using DataSourceManager")
                # Fallback to DataSourceManager
                from lfx.base.datasource.manager import DataSourceManager

                manager = DataSourceManager()
                # Use async method correctly
                datasource = asyncio.run(manager._get_datasource_by_id(datasource_id))

                if not datasource:
                    raise ValueError(f"Datasource not found: {datasource_id}")

                # Extract connection info from datasource
                return self._extract_connection_info_from_datasource(datasource)

            # Check source to determine how to extract connection info
            source = datasource.get("source", "builtin")

            if source == "public":
                # Extract from public datasource (raw_data)
                return self._build_public_flink_connection_info(datasource)
            else:
                # Extract from builtin datasource using DataSourceManager
                from lfx.base.datasource.manager import DataSourceManager

                manager = DataSourceManager()
                # Use async method correctly
                builtin_ds = asyncio.run(manager._get_datasource_by_id(datasource_id))

                if not builtin_ds:
                    raise ValueError(f"Builtin datasource not found: {datasource_id}")

                # Extract connection info from datasource
                return self._extract_connection_info_from_datasource(builtin_ds)

        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to get Flink connection info: {e}")
            # Return default values
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
                "connection_string": "",
            }

    def _extract_connection_info_from_datasource(self, datasource: dict) -> dict:
        """Extract connection info from datasource dictionary.

        Args:
            datasource: Datasource dictionary from DataSourceManager

        Returns:
            Connection info dictionary
        """
        # Try to get from advanced_config first (for Flink datasources)
        advanced_config = datasource.get("advanced_config", {})
        if isinstance(advanced_config, str):
            try:
                import json
                advanced_config = json.loads(advanced_config)
            except (json.JSONDecodeError, ValueError):
                advanced_config = {}

        # Try to extract Flink-specific config
        jobmanager_host = advanced_config.get("jobmanager_host") or advanced_config.get("host") or datasource.get("host", "localhost")
        jobmanager_port = advanced_config.get("jobmanager_port") or 6123
        rest_port = advanced_config.get("rest_port") or 8081

        return {
            "jobmanager_host": jobmanager_host,
            "jobmanager_port": jobmanager_port,
            "rest_port": rest_port,
            "connection_string": advanced_config.get("connection_string", ""),
        }

    def _build_public_flink_connection_info(self, datasource: dict) -> dict:
        """Build connection info from public Flink cluster data."""
        try:
            raw_data = datasource.get("raw_data", {})

            # Extract connection information from RegistryClusterVO
            # RegistryCluster has: address, jobManagerAddress
            address = raw_data.get("address", "")
            job_manager_address = raw_data.get("jobManagerAddress", "")

            # Parse address (format might be "host:port")
            jobmanager_host = "localhost"
            rest_port = 8081

            # Try to parse from address first
            if address:
                if ":" in address:
                    parts = address.split(":")
                    jobmanager_host = parts[0]
                    try:
                        rest_port = int(parts[1])
                    except (ValueError, IndexError):
                        rest_port = 8081
                else:
                    jobmanager_host = address

            # Override with jobManagerAddress if available
            if job_manager_address:
                if ":" in job_manager_address:
                    parts = job_manager_address.split(":")
                    jobmanager_host = parts[0]
                    try:
                        rest_port = int(parts[1])
                    except (ValueError, IndexError):
                        rest_port = 8081
                else:
                    jobmanager_host = job_manager_address

            return {
                "jobmanager_host": jobmanager_host,
                "jobmanager_port": 6123,  # Default RPC port
                "rest_port": rest_port,
                "connection_string": address or job_manager_address,
            }

        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to build public Flink connection info: {e}")
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
                "connection_string": "",
            }

    def _execute_sql_statements(
        self,
        datasource_id: str,
        sql_script: str,
        execution_mode: str,
        parallelism: int,
        checkpoint_interval: int,
    ) -> list[dict]:
        """Execute SQL statements on remote Flink cluster using PyFlink."""

        # Parse SQL statements
        statements = self._parse_sql_statements(sql_script)

        if not statements:
            raise ValueError(i18n.t("components.computations.flink_sql.error.no_valid_sql"))

        # Get connection information
        conn_info = self._get_flink_connection_info(datasource_id)

        # Execute SQL using PyFlink with remote cluster configuration
        try:
            # Monkey patch for py4j 0.10.8.1 compatibility with Python 3.10+
            # py4j 0.10.8.1 tries to import MutableMapping from collections, but it's moved to collections.abc
            import collections
            import collections.abc
            for name in ['MutableMapping', 'MutableSequence', 'MutableSet', 'Sequence', 'Set']:
                if not hasattr(collections, name):
                    setattr(collections, name, getattr(collections.abc, name))

            import os
            import tempfile
            from pyflink.datastream import StreamExecutionEnvironment
            from pyflink.table import EnvironmentSettings, StreamTableEnvironment

            # ===== 配置远程集群（创建临时配置文件）=====
            has_remote_config = conn_info.get("jobmanager_host") and (
                conn_info.get("jobmanager_port") or conn_info.get("rest_port")
            )

            if has_remote_config:
                jobmanager_host = conn_info["jobmanager_host"]
                jobmanager_port = conn_info.get("jobmanager_port", 6123)
                rest_port = conn_info.get("rest_port", 8081)

                # 创建临时配置目录
                flink_conf_dir = tempfile.mkdtemp(prefix="flink_conf_")

                # 创建 flink-conf.yaml
                flink_conf_content = f"""jobmanager.rpc.address: {jobmanager_host}
jobmanager.rpc.port: {jobmanager_port}
rest.address: {jobmanager_host}
rest.port: {rest_port}
"""
                flink_conf_path = os.path.join(flink_conf_dir, "flink-conf.yaml")
                with open(flink_conf_path, 'w') as f:
                    f.write(flink_conf_content)

                # 创建简单的 log4j.properties 以避免警告
                log4j_content = """log4j.rootLogger=WARN, console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
"""
                log4j_path = os.path.join(flink_conf_dir, "log4j-cli.properties")
                with open(log4j_path, 'w') as f:
                    f.write(log4j_content)

                # 设置环境变量
                os.environ["FLINK_CONF_DIR"] = flink_conf_dir

                logger.info(
                    f"[FlinkSQL] Configured remote Flink cluster: "
                    f"rpc={jobmanager_host}:{jobmanager_port}, rest={jobmanager_host}:{rest_port}, conf_dir={flink_conf_dir}"
                )
            else:
                logger.info("[FlinkSQL] No remote cluster configuration, using local execution mode")

            # 创建 StreamExecutionEnvironment
            env = StreamExecutionEnvironment.get_execution_environment()
            env.set_parallelism(parallelism)

            # 创建 TableEnvironment
            if execution_mode == "streaming":
                env_settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
            else:
                env_settings = EnvironmentSettings.new_instance().in_batch_mode().build()

            table_env = StreamTableEnvironment.create(
                stream_execution_environment=env, environment_settings=env_settings
            )

            # 配置 checkpoint (仅 streaming 模式)
            if execution_mode == "streaming":
                env.get_checkpoint_config().set_checkpoint_interval(checkpoint_interval)

            # Execute statements using Flink 1.9.3 API
            # Note: In Flink 1.9, sql_update() only registers DDL/DML, doesn't execute immediately
            results = []
            for idx, stmt in enumerate(statements):
                try:
                    stmt_type = self._get_statement_type(stmt)
                    start_time = datetime.datetime.now()

                    # Flink 1.9 API: sql_update() for DDL and DML
                    if stmt_type in ["SELECT"]:
                        # SELECT queries not supported in Flink 1.9 PyFlink
                        rows_affected = "不支持"
                        results.append({
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "跳过",
                            "rows_affected": rows_affected,
                            "error_message": "Flink 1.9 不支持直接执行 SELECT 查询，请使用 INSERT INTO 将结果写入 sink 表",
                        })
                        continue
                    elif stmt_type in ["CREATE", "DROP", "ALTER"]:
                        # DDL statements: register table definitions
                        table_env.sql_update(stmt)
                        rows_affected = "已注册"
                        logger.debug(f"[FlinkSQL] Registered {stmt_type} statement")
                    elif stmt_type in ["INSERT"]:
                        # DML statements: register data transformations
                        table_env.sql_update(stmt)
                        rows_affected = "已注册 (需调用 execute 执行)"
                        logger.debug(f"[FlinkSQL] Registered INSERT statement")
                    else:
                        # Unknown statement type
                        table_env.sql_update(stmt)
                        rows_affected = "已注册"

                    duration = (datetime.datetime.now() - start_time).total_seconds()

                    results.append(
                        {
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "成功",
                            "rows_affected": rows_affected,
                            "error_message": "",
                        }
                    )

                except Exception as e:
                    logger.error(f"[FlinkSQL] Failed to process statement {idx + 1}: {e}")
                    results.append(
                        {
                            "statement_index": idx + 1,
                            "statement_type": self._get_statement_type(stmt),
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "失败",
                            "rows_affected": "",
                            "error_message": str(e),
                        }
                    )

            logger.info(f"[FlinkSQL] Processed {len(results)} SQL statements (注意: Flink 1.9 中 sql_update 只注册语句，不会立即执行)")
            return results

        except ImportError as e:
            # If PyFlink is not available, return mock results
            logger.warning(f"[FlinkSQL] PyFlink import failed: {e}. Returning mock results.")
            logger.exception("[FlinkSQL] Import error details:")
            return self._create_mock_results(statements)

        except Exception as e:
            logger.exception(f"[FlinkSQL] Unexpected error during SQL execution: {e}")
            raise Exception(f"Failed to execute SQL: {str(e)}")

    def _create_mock_results(self, statements: list[str]) -> list[dict]:
        """Create mock results when PyFlink is not available."""
        results = []
        for idx, stmt in enumerate(statements):
            results.append(
                {
                    "statement_index": idx + 1,
                    "statement_type": self._get_statement_type(stmt),
                    "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                    "execution_status": "模拟",
                    "rows_affected": "N/A (PyFlink not installed)",
                    "error_message": "",
                }
            )
        return results

    def _parse_sql_statements(self, sql_script: str) -> list[str]:
        """Parse SQL script into multiple statements."""
        try:
            parsed = sqlparse.parse(sql_script)
            statements = []
            for statement in parsed:
                sql = statement.value.strip()
                # Remove trailing semicolon (Flink sql_update doesn't support it)
                if sql.endswith(";"):
                    sql = sql[:-1].strip()
                # Skip empty statements and comments
                if sql and not sql.startswith("--"):
                    statements.append(sql)
            return statements
        except Exception as e:
            logger.warning(f"[FlinkSQL] Failed to parse SQL: {e}")
            # Fallback: split by semicolon and remove trailing semicolons
            statements = []
            for s in sql_script.split(";"):
                s = s.strip()
                if s:
                    statements.append(s)
            return statements

    def _get_statement_type(self, sql: str) -> str:
        """Get SQL statement type."""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            return "SELECT"
        elif sql_upper.startswith("CREATE"):
            return "CREATE"
        elif sql_upper.startswith("INSERT"):
            return "INSERT"
        elif sql_upper.startswith("DROP"):
            return "DROP"
        elif sql_upper.startswith("ALTER"):
            return "ALTER"
        elif sql_upper.startswith("UPDATE"):
            return "UPDATE"
        elif sql_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"

    def _format_i18n(self, key: str, **kwargs) -> str:
        """Format i18n text with parameters."""
        text = i18n.t(key)
        for param_key, param_value in kwargs.items():
            text = text.replace(f"{{{param_key}}}", str(param_value))
        return text

    def execute_flink_sql(self) -> list[Data]:
        """Main execution method - return execution results."""
        results = []

        # If execution_results is empty, auto-execute SQL
        if not (hasattr(self, "execution_results") and self.execution_results):
            logger.info("[FlinkSQL] execution_results is empty, auto-executing SQL")
            try:
                datasource_id = self.flink_datasource
                sql_script = self.sql_script
                execution_mode = self.execution_mode
                parallelism = self.parallelism
                checkpoint_interval = self.checkpoint_interval

                if not datasource_id:
                    raise ValueError(i18n.t("components.computations.flink_sql.error.no_datasource"))

                if not sql_script or not sql_script.strip():
                    raise ValueError(i18n.t("components.computations.flink_sql.error.no_sql"))

                # Execute SQL statements
                execution_results = self._execute_sql_statements(
                    datasource_id, sql_script, execution_mode, parallelism, checkpoint_interval
                )

                # Convert to Data objects
                for result in execution_results:
                    results.append(Data(data=result))

                logger.info(f"[FlinkSQL] Auto-executed SQL, got {len(results)} results")

            except Exception as e:
                error_msg = str(e)
                logger.exception(f"[FlinkSQL] Auto-execution failed: {error_msg}")
                self.status = f"{i18n.t('components.computations.flink_sql.status.error')}: {error_msg}"
                # Return error result
                results.append(
                    Data(
                        data={
                            "statement_index": 1,
                            "statement_type": "ERROR",
                            "sql_statement": "N/A",
                            "execution_status": "失败",
                            "rows_affected": "",
                            "error_message": error_msg,
                        }
                    )
                )
        else:
            # Use existing execution_results
            logger.info("[FlinkSQL] Using existing execution_results")
            for result in self.execution_results:
                results.append(Data(data=result))

        return results
