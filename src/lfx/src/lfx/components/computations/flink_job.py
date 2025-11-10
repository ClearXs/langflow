import asyncio
import datetime
import json
from typing import Any

import i18n
import requests

from lfx.custom.custom_component.component import Component
from lfx.io import CodeInput, DropdownInput, FileInput, IntInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.services.feign.clients.data_construction import cleanup_temp_file, download_file_by_id


class ETLFlinkJobComponent(Component):
    """Flink Job component for submitting JAR or Python jobs."""

    display_name = i18n.t("components.computations.flink_job.display_name")
    description = i18n.t("components.computations.flink_job.description")
    icon = "Zap"
    name = "FlinkJob"

    # Enable universal input
    include_universal_input = True

    inputs = [
        DropdownInput(
            name="flink_datasource",
            display_name=i18n.t("components.computations.flink_job.flink_datasource.display_name"),
            info=i18n.t("components.computations.flink_job.flink_datasource.info"),
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
            name="job_mode",
            display_name=i18n.t("components.computations.flink_job.job_mode.display_name"),
            info=i18n.t("components.computations.flink_job.job_mode.info"),
            options=["jar", "python"],
            value="python",
            required=True,
            real_time_refresh=True,
        ),
        # JAR mode inputs (hidden by default since default mode is python)
        FileInput(
            name="jar_file",
            display_name=i18n.t("components.computations.flink_job.jar_file.display_name"),
            info=i18n.t("components.computations.flink_job.jar_file.info"),
            file_types=["jar"],
            is_list=False,
            temp_file=False,
            required=False,
            advanced=False,
        ),
        StrInput(
            name="entry_class",
            display_name=i18n.t("components.computations.flink_job.entry_class.display_name"),
            info=i18n.t("components.computations.flink_job.entry_class.info"),
            required=False,
            advanced=False,
        ),
        StrInput(
            name="program_args",
            display_name=i18n.t("components.computations.flink_job.program_args.display_name"),
            info=i18n.t("components.computations.flink_job.program_args.info"),
            required=False,
            advanced=True,
        ),
        # Python mode input (shown by default)
        CodeInput(
            name="python_script",
            display_name=i18n.t("components.computations.flink_job.python_script.display_name"),
            info=i18n.t("components.computations.flink_job.python_script.info"),
            required=True,
            advanced=False,
            language="python",
            value="""# Word Count Example - PyFlink 1.9.3 (Batch Processing)
from pyflink.dataset import ExecutionEnvironment
from pyflink.table import TableConfig, BatchTableEnvironment

# 创建批处理环境
exec_env = ExecutionEnvironment.get_execution_environment()
exec_env.set_parallelism(1)
t_config = TableConfig()
t_env = BatchTableEnvironment.create(exec_env, t_config)

# 创建源表（文件系统 CSV）- 需要预先创建 /tmp/input.csv 文件
# 文件内容示例（每行一个单词）：
# hello
# world
# hello
# flink
# world
my_source_ddl = \"\"\"
    create table mySource (
        word VARCHAR
    ) with (
        'connector.type' = 'filesystem',
        'format.type' = 'csv',
        'connector.path' = '/tmp/input.csv'
    )
\"\"\"

# 创建目标表（文件系统 CSV）
my_sink_ddl = \"\"\"
    create table mySink (
        word VARCHAR,
        `count` BIGINT
    ) with (
        'connector.type' = 'filesystem',
        'format.type' = 'csv',
        'connector.path' = '/tmp/output.csv'
    )
\"\"\"

# 注册表
t_env.sql_update(my_source_ddl)
t_env.sql_update(my_sink_ddl)

# 执行 word count：扫描源表，按单词分组，统计数量
t_env.scan('mySource') \\
    .group_by('word') \\
    .select('word, count(1) as count') \\
    .insert_into('mySink')

# 执行作业
t_env.execute("word_count_job")

print("Word count job completed! Check /tmp/output.csv for results.")
""",
        ),
        IntInput(
            name="parallelism",
            display_name=i18n.t("components.computations.flink_job.parallelism.display_name"),
            info=i18n.t("components.computations.flink_job.parallelism.info"),
            value=1,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="job_info",
            display_name=i18n.t("components.computations.flink_job.output.display_name"),
            method="submit_flink_job",
        ),
    ]

    def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Handle field changes and dynamic field visibility."""
        # Load Flink datasources
        if field_name is None or (field_name == "flink_datasource" and not field_value):
            datasources = self._load_flink_datasources()
            build_config["flink_datasource"]["options"] = [ds["display_name"] for ds in datasources]
            build_config["flink_datasource"]["options_metadata"] = datasources

        # Adjust field visibility based on job_mode
        if field_name == "job_mode" or field_name is None:
            # Get current mode from field_value, build_config, or default to python
            if field_name == "job_mode":
                current_mode = field_value
            elif hasattr(self, "job_mode"):
                current_mode = self.job_mode
            else:
                # First render: get from build_config
                current_mode = build_config.get("job_mode", {}).get("value", "python")

            if current_mode == "jar":
                # Show JAR-related fields, hide Python fields
                build_config["jar_file"]["show"] = True
                build_config["jar_file"]["required"] = True
                build_config["jar_file"]["advanced"] = False
                build_config["entry_class"]["show"] = True
                build_config["entry_class"]["required"] = True
                build_config["entry_class"]["advanced"] = False
                build_config["program_args"]["show"] = True
                build_config["program_args"]["advanced"] = True
                build_config["python_script"]["show"] = False
                build_config["python_script"]["required"] = False
                build_config["python_script"]["advanced"] = True
            else:
                # Show Python fields, hide JAR-related fields
                build_config["jar_file"]["show"] = False
                build_config["jar_file"]["required"] = False
                build_config["jar_file"]["advanced"] = True
                build_config["entry_class"]["show"] = False
                build_config["entry_class"]["required"] = False
                build_config["entry_class"]["advanced"] = True
                build_config["program_args"]["show"] = False
                build_config["program_args"]["advanced"] = True
                build_config["python_script"]["show"] = True
                build_config["python_script"]["required"] = True
                build_config["python_script"]["advanced"] = False

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
                    logger.debug(f"[FlinkJob] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
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

            logger.debug(f"[FlinkJob] Got enterprise datasources: {len(datasources.get('enterprise', []))}")
            logger.debug(f"[FlinkJob] Got custom datasources: {len(datasources.get('custom', []))}")

            # Merge enterprise and custom datasources
            for ds in datasources.get("enterprise", []) + datasources.get("custom", []):
                datasource_id = self._extract_uuid_from_id(ds["id"])
                ds_name = ds.get("name", "Unknown")
                ds_type = ds.get("type", "")

                logger.debug(f"[FlinkJob] Datasource: id={datasource_id}, name={ds_name}, type={ds_type}")

                # Filter by Flink type (case-insensitive)
                ds_type_lower = ds_type.lower() if ds_type else ""
                if "flink" in ds_type_lower:
                    logger.info(f"[FlinkJob] ✓ Including Flink datasource: {ds_name} (type={ds_type})")
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
                    logger.debug(f"[FlinkJob] ✗ Skipping non-Flink datasource: {ds_name} (type={ds_type})")

            logger.info(f"[FlinkJob] Filtered Flink datasources count: {len(flink_datasources)}")
            return flink_datasources

        except Exception as e:
            logger.exception(f"[FlinkJob] Failed to load builtin Flink datasources: {e}")
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

            logger.info(f"[FlinkJob] Loaded {len(public_datasources)} public Flink clusters")
            return public_datasources

        except Exception as e:
            logger.error(f"[FlinkJob] Failed to load public Flink clusters: {e}")
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
            logger.error(f"[FlinkJob] Failed to find datasource in metadata: {e}")

        return None

    def _get_flink_connection_info(self, datasource_id: str) -> dict:
        """Get Flink connection information from datasource."""
        try:
            # Find datasource in metadata
            datasource = self._find_datasource_by_id(datasource_id)

            if not datasource:
                logger.warning(f"[FlinkJob] Datasource not found in metadata: {datasource_id}, using DataSourceManager")
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
            logger.error(f"[FlinkJob] Failed to get Flink connection info: {e}")
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
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
            }

        except Exception as e:
            logger.error(f"[FlinkJob] Failed to build public Flink connection info: {e}")
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
            }

    async def _submit_jar_job(
        self, datasource_id: str, jar_file: str, entry_class: str, program_args: str, parallelism: int
    ) -> dict:
        """Submit JAR job to Flink cluster."""
        # Get connection information
        conn_info = self._get_flink_connection_info(datasource_id)
        rest_url = f"http://{conn_info['jobmanager_host']}:{conn_info['rest_port']}"

        # Parse jar_file (format: {"value": "filename", "file_path": "file_id"})
        try:
            jar_data = json.loads(jar_file) if isinstance(jar_file, str) else jar_file
        except json.JSONDecodeError:
            jar_data = {"file_path": jar_file}

        file_id = jar_data.get("file_path")
        if not file_id:
            raise ValueError("Invalid JAR file data")

        # Download JAR file
        temp_jar_path = await download_file_by_id(file_id)

        try:
            start_time = datetime.datetime.now()

            # Upload JAR to Flink
            with open(temp_jar_path, "rb") as f:
                files = {"jarfile": (jar_data.get("value", "job.jar"), f, "application/x-java-archive")}
                upload_resp = requests.post(f"{rest_url}/jars/upload", files=files, timeout=60)

            upload_resp.raise_for_status()
            jar_id = upload_resp.json().get("filename", "").split("/")[-1]

            if not jar_id:
                raise ValueError("Failed to get JAR ID from upload response")

            # Submit job
            submit_data = {
                "entryClass": entry_class,
                "parallelism": parallelism,
            }

            if program_args:
                submit_data["programArgs"] = program_args

            submit_resp = requests.post(f"{rest_url}/jars/{jar_id}/run", json=submit_data, timeout=30)
            submit_resp.raise_for_status()
            job_id = submit_resp.json().get("jobid", "unknown")

            # Query job status
            try:
                status_resp = requests.get(f"{rest_url}/jobs/{job_id}", timeout=10)
                status_resp.raise_for_status()
                job_info = status_resp.json()

                job_name = job_info.get("name", "Unknown")
                job_state = job_info.get("state", "UNKNOWN")
                job_start_time = job_info.get("start-time", 0)
                job_duration = job_info.get("duration", 0)

                duration = (datetime.datetime.now() - start_time).total_seconds()

                return {
                    "job_id": job_id,
                    "job_name": job_name,
                    "status": job_state,
                    "start_time": (
                        datetime.datetime.fromtimestamp(job_start_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
                        if job_start_time
                        else start_time.strftime("%Y-%m-%d %H:%M:%S")
                    ),
                    "duration": f"{duration:.2f}s",
                    "message": "作业已提交到 Flink 集群",
                }

            except Exception as e:
                # If status query fails, still return success with job_id
                duration = (datetime.datetime.now() - start_time).total_seconds()
                return {
                    "job_id": job_id,
                    "job_name": entry_class.split(".")[-1],
                    "status": "SUBMITTED",
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": f"{duration:.2f}s",
                    "message": f"作业已提交 (无法获取详细状态: {e!s})",
                }

        finally:
            # Cleanup temporary file
            cleanup_temp_file(temp_jar_path)

    def _submit_python_job(self, datasource_id: str, python_script: str, parallelism: int) -> dict:
        """Submit Python script job to remote Flink cluster."""
        # Get connection information
        conn_info = self._get_flink_connection_info(datasource_id)

        start_time = datetime.datetime.now()

        try:
            # Monkey patch for py4j 0.10.8.1 compatibility with Python 3.10+
            # py4j 0.10.8.1 tries to import MutableMapping from collections, but it's moved to collections.abc
            import collections
            import collections.abc
            for name in ["MutableMapping", "MutableSequence", "MutableSet", "Sequence", "Set"]:
                if not hasattr(collections, name):
                    setattr(collections, name, getattr(collections.abc, name))

            # Try to use PyFlink with remote cluster configuration
            import os
            import tempfile

            from pyflink.datastream import StreamExecutionEnvironment
            from pyflink.table import EnvironmentSettings, StreamTableEnvironment

            # 配置远程集群（创建临时配置文件）
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
                with open(flink_conf_path, "w") as f:
                    f.write(flink_conf_content)

                # 创建简单的 log4j.properties 以避免警告
                log4j_content = """log4j.rootLogger=WARN, console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
"""
                log4j_path = os.path.join(flink_conf_dir, "log4j-cli.properties")
                with open(log4j_path, "w") as f:
                    f.write(log4j_content)

                # 设置环境变量
                os.environ["FLINK_CONF_DIR"] = flink_conf_dir

                logger.info(
                    f"[FlinkJob] Configured remote Flink cluster: "
                    f"rpc={jobmanager_host}:{jobmanager_port}, rest={jobmanager_host}:{rest_port}, conf_dir={flink_conf_dir}"
                )
            else:
                logger.info("[FlinkJob] No remote cluster configuration, using local execution mode")

            # 不预先创建环境，让用户脚本完全控制
            # 只提供必要的导入和类，让用户脚本自己决定使用 Batch 还是 Streaming

            # Import all necessary PyFlink modules for user script
            from pyflink.dataset import ExecutionEnvironment
            from pyflink.table import BatchTableEnvironment, TableConfig

            # 6. Execute Python script in a controlled environment
            # Provide all PyFlink classes and modules to user script
            exec_globals = {
                # DataStream API
                "StreamExecutionEnvironment": StreamExecutionEnvironment,
                "StreamTableEnvironment": StreamTableEnvironment,
                "EnvironmentSettings": EnvironmentSettings,
                # Batch API
                "ExecutionEnvironment": ExecutionEnvironment,
                "BatchTableEnvironment": BatchTableEnvironment,
                "TableConfig": TableConfig,
            }

            # Capture output
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()

            try:
                exec(python_script, exec_globals)
                output = captured_output.getvalue()
            finally:
                sys.stdout = old_stdout

            duration = (datetime.datetime.now() - start_time).total_seconds()

            # Extract job info if available
            job_id = "local-python-job"
            message = "Python 脚本执行成功"
            if output:
                message += f"\n输出: {output[:200]}"

            return {
                "job_id": job_id,
                "job_name": "PyFlink Script",
                "status": "完成",
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": f"{duration:.2f}s",
                "message": message,
            }

        except ImportError:
            # PyFlink not installed
            duration = (datetime.datetime.now() - start_time).total_seconds()
            return {
                "job_id": "N/A",
                "job_name": "PyFlink Script",
                "status": "失败",
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": f"{duration:.2f}s",
                "message": "PyFlink 未安装，无法执行 Python 脚本",
            }

        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            return {
                "job_id": "N/A",
                "job_name": "PyFlink Script",
                "status": "失败",
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": f"{duration:.2f}s",
                "message": f"执行失败: {e!s}",
            }

    def submit_flink_job(self) -> Data:
        """Main execution method - submit Flink job and return result."""
        try:
            datasource_id = self.flink_datasource
            job_mode = self.job_mode

            if not datasource_id:
                raise ValueError(i18n.t("components.computations.flink_job.error.no_datasource"))

            if job_mode == "jar":
                # JAR mode submission
                if not self.jar_file:
                    raise ValueError(i18n.t("components.computations.flink_job.error.no_jar"))
                if not self.entry_class:
                    raise ValueError(i18n.t("components.computations.flink_job.error.no_entry_class"))

                result = asyncio.run(
                    self._submit_jar_job(
                        datasource_id, self.jar_file, self.entry_class, self.program_args or "", self.parallelism
                    )
                )
            else:
                # Python mode submission
                if not self.python_script or not self.python_script.strip():
                    raise ValueError(i18n.t("components.computations.flink_job.error.no_python_script"))

                result = self._submit_python_job(datasource_id, self.python_script, self.parallelism)

            # Set status and return result
            self.status = f"Job {result['job_id']}: {result['status']}"
            return Data(data=result)

        except Exception as e:
            error_msg = str(e)
            self.status = f"{i18n.t('components.computations.flink_job.status.error')}: {error_msg}"
            return Data(
                data={
                    "job_id": "N/A",
                    "job_name": "N/A",
                    "status": "失败",
                    "start_time": "",
                    "duration": "",
                    "message": error_msg,
                }
            )
