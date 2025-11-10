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
            options=["batch", "streaming"],
            value="batch",
            required=True,
        ),
        CodeInput(
            name="sql_script",
            display_name=i18n.t("components.computations.flink_sql.sql_script.display_name"),
            info=i18n.t("components.computations.flink_sql.sql_script.info"),
            required=True,
            language="sql",
            value="""-- Flink SQL Example - Generate and Print Data
-- 使用 datagen 连接器生成测试数据，使用 print 连接器输出到日志

-- 创建源表（使用 datagen 连接器自动生成数据）
CREATE TABLE user_behavior (
    user_id BIGINT,
    item_id BIGINT,
    category_id BIGINT,
    behavior STRING,
    ts TIMESTAMP(3)
) WITH (
    'connector' = 'datagen',
    'rows-per-second' = '10',
    'fields.user_id.min' = '1',
    'fields.user_id.max' = '1000',
    'fields.item_id.min' = '1',
    'fields.item_id.max' = '10000',
    'fields.category_id.min' = '1',
    'fields.category_id.max' = '100',
    'fields.behavior.length' = '10'
);

-- 创建目标表（使用 print 连接器输出到 TaskManager 日志）
CREATE TABLE user_behavior_print (
    user_id BIGINT,
    item_id BIGINT,
    category_id BIGINT,
    behavior STRING,
    ts TIMESTAMP(3)
) WITH (
    'connector' = 'print'
);

-- 简单的数据复制查询
INSERT INTO user_behavior_print
SELECT user_id, item_id, category_id, behavior, ts
FROM user_behavior;""",
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
        """Find datasource by reloading datasource list.

        Supports matching by:
        - id (numeric or string)
        - value (cluster_id)
        - display_name (full display name)
        - label (display name)
        """
        try:
            logger.debug(f"[FlinkSQL] Searching for datasource: {datasource_id}")

            # Try cached metadata first
            if hasattr(self, "_input_dict") and self._input_dict:
                logger.debug(f"[FlinkSQL] Has _input_dict with keys: {self._input_dict.keys()}")
                flink_datasource_input = self._input_dict.get("flink_datasource")

                if flink_datasource_input and hasattr(flink_datasource_input, "options_metadata"):
                    options_metadata = flink_datasource_input.options_metadata
                    logger.debug(f"[FlinkSQL] options_metadata count: {len(options_metadata) if options_metadata else 0}")

                    if options_metadata:
                        for idx, ds in enumerate(options_metadata):
                            logger.debug(f"[FlinkSQL] Checking datasource {idx}: id={ds.get('id')}, display_name={ds.get('display_name')}")

                            if (
                                str(ds.get("id")) == str(datasource_id)
                                or str(ds.get("value")) == str(datasource_id)
                                or ds.get("display_name") == datasource_id
                                or ds.get("label") == datasource_id
                            ):
                                logger.info(f"[FlinkSQL] Found datasource in cache: id={ds.get('id')}, display_name={ds.get('display_name')}")
                                return ds

            # If not found in cache, reload datasources
            logger.info("[FlinkSQL] Datasource not in cache, reloading all datasources")
            all_datasources = self._load_flink_datasources()
            logger.debug(f"[FlinkSQL] Reloaded {len(all_datasources)} datasources")

            for idx, ds in enumerate(all_datasources):
                logger.debug(f"[FlinkSQL] Checking reloaded datasource {idx}: id={ds.get('id')}, display_name={ds.get('display_name')}")

                if (
                    str(ds.get("id")) == str(datasource_id)
                    or str(ds.get("value")) == str(datasource_id)
                    or ds.get("display_name") == datasource_id
                    or ds.get("label") == datasource_id
                ):
                    logger.info(f"[FlinkSQL] Found datasource after reload: id={ds.get('id')}, display_name={ds.get('display_name')}")
                    return ds

        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to find datasource: {e}", exc_info=True)

        logger.warning(f"[FlinkSQL] Datasource not found after search: {datasource_id}")
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
        sql_gateway_port = advanced_config.get("sql_gateway_port") or 8083

        return {
            "jobmanager_host": jobmanager_host,
            "jobmanager_port": jobmanager_port,
            "rest_port": rest_port,
            "sql_gateway_port": sql_gateway_port,
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

            logger.debug(f"[FlinkSQL] Parsing address: {address}, jobManagerAddress: {job_manager_address}")

            # Parse address (format might be "http://host:port" or "host:port")
            jobmanager_host = "localhost"
            rest_port = 8081

            # Helper function to parse URL
            def parse_url(url: str) -> tuple[str, int]:
                """Parse URL and extract host and port."""
                # Remove protocol if present
                if "://" in url:
                    url = url.split("://", 1)[1]

                # Split by colon to get host and port
                if ":" in url:
                    parts = url.split(":")
                    host = parts[0]
                    try:
                        port = int(parts[1].split("/")[0])  # Remove trailing path if any
                    except (ValueError, IndexError):
                        port = 8081
                    return host, port
                return url, 8081

            # Try to parse from address first
            if address:
                jobmanager_host, rest_port = parse_url(address)
                logger.debug(f"[FlinkSQL] Parsed from address: host={jobmanager_host}, port={rest_port}")

            # Override with jobManagerAddress if available
            if job_manager_address:
                jobmanager_host, rest_port = parse_url(job_manager_address)
                logger.debug(f"[FlinkSQL] Parsed from jobManagerAddress: host={jobmanager_host}, port={rest_port}")

            # SQL Gateway port is typically 8083 (same host as JobManager)
            sql_gateway_port = 8083

            logger.debug(f"[FlinkSQL] Connection info: host={jobmanager_host}, rest={rest_port}, sql_gateway={sql_gateway_port}")

            return {
                "jobmanager_host": jobmanager_host,
                "jobmanager_port": 6123,  # Default RPC port
                "rest_port": rest_port,
                "sql_gateway_port": sql_gateway_port,
                "connection_string": address or job_manager_address,
            }

        except Exception as e:
            logger.error(f"[FlinkSQL] Failed to build public Flink connection info: {e}", exc_info=True)
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
                "sql_gateway_port": 8083,
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
        """Execute SQL statements on remote Flink cluster using SQL Gateway REST API."""
        # Log the received SQL script
        logger.debug(f"[FlinkSQL] Received SQL script length: {len(sql_script) if sql_script else 0}")
        logger.debug(f"[FlinkSQL] SQL script preview: {sql_script[:200] if sql_script else 'EMPTY'}")

        # Log full SQL for debugging
        if sql_script and len(sql_script) > 200:
            logger.info(f"[FlinkSQL] Full SQL script:\n{sql_script}")

        # Parse SQL statements
        statements = self._parse_sql_statements(sql_script)

        logger.debug(f"[FlinkSQL] Parsed {len(statements)} SQL statements")

        # Log each parsed statement for debugging
        for idx, stmt in enumerate(statements, 1):
            logger.info(f"[FlinkSQL] Statement {idx}:\n{stmt[:500]}")  # First 500 chars

        if not statements:
            logger.error(f"[FlinkSQL] No statements parsed from SQL script: {sql_script}")
            raise ValueError(i18n.t("components.computations.flink_sql.error.no_valid_sql"))

        # Get connection information
        conn_info = self._get_flink_connection_info(datasource_id)

        # Execute SQL using Flink SQL Gateway REST API
        return self._execute_via_sql_gateway(conn_info, statements, execution_mode, parallelism, checkpoint_interval)

    def _execute_via_sql_gateway(
        self,
        conn_info: dict,
        statements: list[str],
        execution_mode: str,
        parallelism: int,
        checkpoint_interval: int,
    ) -> list[dict]:
        """Execute SQL statements using Flink SQL Gateway REST API.

        SQL Gateway API workflow:
        1. Create a session
        2. Submit SQL statements
        3. Check operation status
        4. Fetch results (if needed)
        5. Close session
        """
        import time

        import requests

        jobmanager_host = conn_info.get("jobmanager_host", "localhost")
        # SQL Gateway default port is 8083, not 8081
        sql_gateway_port = conn_info.get("sql_gateway_port", 8083)
        sql_gateway_url = f"http://{jobmanager_host}:{sql_gateway_port}"

        logger.info(f"[FlinkSQL] Using SQL Gateway at {sql_gateway_url}")

        session_handle = None
        results = []

        try:
            # Step 1: Create a session
            session_properties = {
                "execution.runtime-mode": "streaming" if execution_mode == "streaming" else "batch",
                "parallelism.default": str(parallelism),
            }

            if execution_mode == "streaming":
                session_properties["execution.checkpointing.interval"] = str(checkpoint_interval)

            logger.info(f"[FlinkSQL] Creating session with properties: {session_properties}")

            create_session_response = requests.post(
                f"{sql_gateway_url}/v1/sessions",
                json={"properties": session_properties},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            create_session_response.raise_for_status()
            session_data = create_session_response.json()
            session_handle = session_data.get("sessionHandle")

            if not session_handle:
                raise ValueError(f"Failed to create session: {session_data}")

            logger.info(f"[FlinkSQL] Created session: {session_handle}")

            # Step 2 & 3: Submit each SQL statement and wait for completion
            for idx, stmt in enumerate(statements):
                try:
                    stmt_type = self._get_statement_type(stmt)
                    start_time = datetime.datetime.now()

                    logger.info(f"[FlinkSQL] Submitting statement {idx + 1}/{len(statements)}: {stmt_type}")

                    # Submit statement
                    submit_response = requests.post(
                        f"{sql_gateway_url}/v1/sessions/{session_handle}/statements",
                        json={"statement": stmt},
                        headers={"Content-Type": "application/json"},
                        timeout=30,
                    )
                    submit_response.raise_for_status()
                    submit_data = submit_response.json()
                    operation_handle = submit_data.get("operationHandle")

                    if not operation_handle:
                        raise ValueError(f"Failed to submit statement: {submit_data}")

                    logger.debug(f"[FlinkSQL] Statement submitted, operation handle: {operation_handle}")

                    # Poll operation status
                    # For INSERT statements, check if job is RUNNING (which means success for streaming jobs)
                    max_retries = 30  # 30 seconds should be enough to check if job started
                    retry_count = 0
                    operation_status = None

                    while retry_count < max_retries:
                        status_response = requests.get(
                            f"{sql_gateway_url}/v1/sessions/{session_handle}/operations/{operation_handle}/status",
                            timeout=10,
                        )
                        status_response.raise_for_status()
                        status_data = status_response.json()
                        operation_status = status_data.get("status")

                        logger.debug(f"[FlinkSQL] Operation status: {operation_status}")

                        # For DDL statements (CREATE/DROP), wait for FINISHED
                        # For DML statements (INSERT), RUNNING means job started successfully
                        if operation_status in ["FINISHED", "ERROR", "CANCELED"]:
                            break
                        if operation_status == "RUNNING" and stmt_type == "INSERT":
                            # INSERT job started successfully in streaming mode
                            logger.info("[FlinkSQL] INSERT job started and running")
                            break

                        time.sleep(1)
                        retry_count += 1

                    duration = (datetime.datetime.now() - start_time).total_seconds()

                    if operation_status == "FINISHED":
                        results.append({
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "成功",
                            "rows_affected": f"完成 ({duration:.2f}s)",
                            "error_message": "",
                        })
                        logger.info(f"[FlinkSQL] Statement {idx + 1} completed successfully in {duration:.2f}s")
                    elif operation_status == "RUNNING" and stmt_type == "INSERT":
                        # INSERT job is running - this is success for streaming jobs
                        results.append({
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "运行中",
                            "rows_affected": f"作业已启动 ({duration:.2f}s)",
                            "error_message": "",
                        })
                        logger.info(f"[FlinkSQL] Statement {idx + 1} job started and running in {duration:.2f}s")
                    elif operation_status == "ERROR":
                        # Try to get error message from different possible locations
                        logger.debug(f"[FlinkSQL] Error status_data: {status_data}")

                        # Try multiple ways to extract error message
                        error_msg = None
                        if "error" in status_data:
                            if isinstance(status_data["error"], dict):
                                error_msg = status_data["error"].get("message") or status_data["error"].get("errorMessage")
                            elif isinstance(status_data["error"], str):
                                error_msg = status_data["error"]

                        # Fallback to checking other fields
                        if not error_msg:
                            error_msg = status_data.get("errorMessage") or status_data.get("message") or "Unknown error"

                        results.append({
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "失败",
                            "rows_affected": "",
                            "error_message": error_msg,
                        })
                        logger.error(f"[FlinkSQL] Statement {idx + 1} failed: {error_msg}")
                    else:
                        # Timeout or other status
                        results.append({
                            "statement_index": idx + 1,
                            "statement_type": stmt_type,
                            "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "execution_status": "超时",
                            "rows_affected": "",
                            "error_message": f"Operation status: {operation_status}",
                        })
                        logger.warning(f"[FlinkSQL] Statement {idx + 1} timed out or unexpected status: {operation_status}")

                except Exception as e:
                    logger.error(f"[FlinkSQL] Failed to process statement {idx + 1}: {e}")
                    results.append({
                        "statement_index": idx + 1,
                        "statement_type": self._get_statement_type(stmt),
                        "sql_statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                        "execution_status": "失败",
                        "rows_affected": "",
                        "error_message": str(e),
                    })

            logger.info(f"[FlinkSQL] Processed {len(results)} SQL statements via SQL Gateway")
            return results

        except requests.exceptions.ConnectionError as e:
            logger.error(f"[FlinkSQL] Failed to connect to SQL Gateway at {sql_gateway_url}: {e}")
            raise ValueError(
                f"无法连接到 Flink SQL Gateway ({sql_gateway_url})。"
                f"请确认: 1) SQL Gateway 已启动 2) 端口号正确（默认 8083）3) 网络可达"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"[FlinkSQL] Request to SQL Gateway timed out: {e}")
            raise ValueError(f"SQL Gateway 请求超时: {e}")
        except Exception as e:
            logger.exception(f"[FlinkSQL] Unexpected error during SQL Gateway execution: {e}")
            raise Exception(f"SQL Gateway 执行失败: {e!s}")
        finally:
            # Step 5: Close session
            if session_handle:
                try:
                    logger.info(f"[FlinkSQL] Closing session: {session_handle}")
                    requests.delete(
                        f"{sql_gateway_url}/v1/sessions/{session_handle}",
                        timeout=10,
                    )
                    logger.info("[FlinkSQL] Session closed successfully")
                except Exception as e:
                    logger.warning(f"[FlinkSQL] Failed to close session: {e}")

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
            # First, remove comment lines (-- ...) to avoid parsing issues
            lines = []
            for line in sql_script.split("\n"):
                stripped_line = line.strip()
                # Skip empty lines and comment-only lines
                if stripped_line and not stripped_line.startswith("--"):
                    lines.append(line)

            # Reconstruct SQL without comments
            cleaned_sql = "\n".join(lines)

            if not cleaned_sql.strip():
                logger.warning("[FlinkSQL] SQL script contains only comments or is empty")
                return []

            # Parse SQL statements
            parsed = sqlparse.parse(cleaned_sql)
            statements = []
            for statement in parsed:
                sql = statement.value.strip()

                # Remove leading digits and whitespace (sometimes appears in parsed SQL)
                while sql and (sql[0].isdigit() or sql[0].isspace()):
                    sql = sql[1:].lstrip()

                # Remove trailing semicolon (Flink sql_update doesn't support it)
                if sql.endswith(";"):
                    sql = sql[:-1].strip()

                # Add non-empty statements
                if sql:
                    statements.append(sql)

            logger.debug(f"[FlinkSQL] Successfully parsed {len(statements)} statements")
            return statements

        except Exception as e:
            logger.warning(f"[FlinkSQL] Failed to parse SQL with sqlparse: {e}")
            # Fallback: split by semicolon and remove comments manually
            statements = []
            for s in sql_script.split(";"):
                # Remove inline comments and trim
                s = s.split("--")[0].strip()
                if s:
                    statements.append(s)
            logger.debug(f"[FlinkSQL] Fallback parsing got {len(statements)} statements")
            return statements

    def _get_statement_type(self, sql: str) -> str:
        """Get SQL statement type."""
        # Remove leading whitespace and numbers (sometimes sqlparse adds line numbers)
        sql_cleaned = sql.strip()

        # Remove leading digits and whitespace
        while sql_cleaned and (sql_cleaned[0].isdigit() or sql_cleaned[0].isspace()):
            sql_cleaned = sql_cleaned[1:].lstrip()

        sql_upper = sql_cleaned.upper()

        if sql_upper.startswith("SELECT"):
            return "SELECT"
        if sql_upper.startswith("CREATE"):
            return "CREATE"
        if sql_upper.startswith("INSERT"):
            return "INSERT"
        if sql_upper.startswith("DROP"):
            return "DROP"
        if sql_upper.startswith("ALTER"):
            return "ALTER"
        if sql_upper.startswith("UPDATE"):
            return "UPDATE"
        if sql_upper.startswith("DELETE"):
            return "DELETE"
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
