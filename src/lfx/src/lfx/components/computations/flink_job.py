import asyncio
import datetime
import json
import os
from typing import Any

import i18n
import requests

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, FileInput, IntInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.services.feign.clients.data_construction import cleanup_temp_file, download_file_by_id


class ETLFlinkJobComponent(Component):
    """Flink Job component for submitting JAR jobs to Flink cluster."""

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
        FileInput(
            name="jar_file",
            display_name=i18n.t("components.computations.flink_job.jar_file.display_name"),
            info=i18n.t("components.computations.flink_job.jar_file.info"),
            file_types=["jar"],
            is_list=False,
            temp_file=False,
            required=True,
        ),
        StrInput(
            name="entry_class",
            display_name=i18n.t("components.computations.flink_job.entry_class.display_name"),
            info=i18n.t("components.computations.flink_job.entry_class.info"),
            required=True,
        ),
        StrInput(
            name="program_args",
            display_name=i18n.t("components.computations.flink_job.program_args.display_name"),
            info=i18n.t("components.computations.flink_job.program_args.info"),
            required=False,
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
        """Handle field changes - load Flink datasources."""
        # Load Flink datasources for initial load or when flink_datasource is accessed
        if field_name is None or field_name == "flink_datasource":
            datasources = self._load_flink_datasources()
            build_config["flink_datasource"]["options"] = [ds["display_name"] for ds in datasources]
            build_config["flink_datasource"]["options_metadata"] = datasources

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
                # Keep the full ID with prefix (custom_ or enterprise_) for DataSourceManager
                datasource_id = ds["id"]  # Don't strip prefix
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
                display_name = self._build_flink_cluster_display_name(cluster_name, version, execution_mode, status)

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

    def _build_flink_cluster_display_name(self, name: str, version: str, execution_mode: str, status: str) -> str:
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

            # Use the ID from cached datasource (already has correct prefix: custom_ or enterprise_)
            actual_id = datasource.get("id", datasource_id)
            logger.debug(f"[FlinkJob] Looking up builtin datasource with ID: {actual_id}")

            # Use async method correctly
            builtin_ds = asyncio.run(manager._get_datasource_by_id(actual_id))

            if not builtin_ds:
                raise ValueError(f"Builtin datasource not found: {actual_id} (original input: {datasource_id})")

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
            else:
                return url, 8081

        # Try to extract Flink-specific config
        jobmanager_host = None
        rest_port = None

        # First try advanced_config
        if advanced_config.get("jobmanager_host"):
            jobmanager_host = advanced_config.get("jobmanager_host")
            rest_port = advanced_config.get("rest_port") or 8081
        elif advanced_config.get("host"):
            # Parse host which might contain URL with port
            jobmanager_host, rest_port = parse_url(advanced_config.get("host"))
        elif datasource.get("host"):
            # Parse datasource host which might contain URL with port
            jobmanager_host, rest_port = parse_url(datasource.get("host"))
        else:
            jobmanager_host = "localhost"
            rest_port = 8081

        jobmanager_port = advanced_config.get("jobmanager_port") or 6123

        logger.debug(
            f"[FlinkJob] Extracted connection info: host={jobmanager_host}, "
            f"rest_port={rest_port}"
        )

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
            address = raw_data.get("address", "")
            job_manager_address = raw_data.get("jobManagerAddress", "")

            logger.debug(f"[FlinkJob] Parsing address: {address}, jobManagerAddress: {job_manager_address}")

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
                logger.debug(f"[FlinkJob] Parsed from address: host={jobmanager_host}, port={rest_port}")

            # Override with jobManagerAddress if available
            if job_manager_address:
                jobmanager_host, rest_port = parse_url(job_manager_address)
                logger.debug(f"[FlinkJob] Parsed from jobManagerAddress: host={jobmanager_host}, port={rest_port}")

            logger.debug(f"[FlinkJob] Connection info: host={jobmanager_host}, rest={rest_port}")

            return {
                "jobmanager_host": jobmanager_host,
                "jobmanager_port": 6123,  # Default RPC port
                "rest_port": rest_port,
                "connection_string": address or job_manager_address,
            }

        except Exception as e:
            logger.error(f"[FlinkJob] Failed to build public Flink connection info: {e}", exc_info=True)
            return {
                "jobmanager_host": "localhost",
                "jobmanager_port": 6123,
                "rest_port": 8081,
                "connection_string": "",
            }

    async def _submit_jar_job(
        self, datasource_id: str, jar_file_input: str, entry_class: str, program_args: str, parallelism: int
    ) -> dict:
        """Submit JAR job to Flink cluster with datasource file download."""
        # Get Flink connection info
        conn_info = self._get_flink_connection_info(datasource_id)
        rest_url = f"http://{conn_info['jobmanager_host']}:{conn_info['rest_port']}"

        # Extract file ID using CSV/Excel pattern
        file_id = self._extract_jar_file_id(jar_file_input)
        if not file_id:
            raise ValueError(i18n.t("components.computations.flink_job.errors.invalid_jar_file"))

        # Check if it's a file ID (numeric) or actual path
        is_file_id = file_id.isdigit() if isinstance(file_id, str) else False

        temp_jar_path = None
        try:
            start_time = datetime.datetime.now()

            # Download from datasource if it's a file ID
            if is_file_id:
                logger.info(f"[FlinkJob] Downloading JAR file ID: {file_id}")
                temp_jar_path = await download_file_by_id(file_id)
                actual_jar_path = temp_jar_path
                logger.info(f"[FlinkJob] Downloaded to: {temp_jar_path}")
            else:
                # Use file path directly (for local files)
                actual_jar_path = file_id
                logger.info(f"[FlinkJob] Using local JAR: {actual_jar_path}")

            # Upload JAR to Flink cluster
            logger.info(f"[FlinkJob] Uploading JAR to Flink: {rest_url}")
            with open(actual_jar_path, "rb") as f:
                filename = os.path.basename(actual_jar_path)
                files = {"jarfile": (filename, f, "application/x-java-archive")}
                upload_resp = requests.post(f"{rest_url}/jars/upload", files=files, timeout=60)

            upload_resp.raise_for_status()
            jar_id = upload_resp.json().get("filename", "").split("/")[-1]

            if not jar_id:
                raise ValueError("Failed to get JAR ID from Flink upload response")

            logger.info(f"[FlinkJob] JAR uploaded, ID: {jar_id}")

            # Submit job
            submit_data = {
                "entryClass": entry_class,
                "parallelism": parallelism,
            }
            if program_args:
                submit_data["programArgs"] = program_args

            logger.info(f"[FlinkJob] Submitting job with entry class: {entry_class}")
            submit_resp = requests.post(f"{rest_url}/jars/{jar_id}/run", json=submit_data, timeout=30)
            submit_resp.raise_for_status()
            job_id = submit_resp.json().get("jobid", "unknown")

            logger.info(f"[FlinkJob] Job submitted: {job_id}")

            # Query job status
            try:
                status_resp = requests.get(f"{rest_url}/jobs/{job_id}", timeout=10)
                status_resp.raise_for_status()
                job_info = status_resp.json()

                job_name = job_info.get("name", "Unknown")
                job_state = job_info.get("state", "UNKNOWN")
                job_start_time = job_info.get("start-time", 0)

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
                    "message": i18n.t("components.computations.flink_job.success.job_submitted"),
                }

            except Exception as e:
                # Status query failed, but job was submitted
                duration = (datetime.datetime.now() - start_time).total_seconds()
                logger.warning(f"[FlinkJob] Job status unavailable: {e}")
                return {
                    "job_id": job_id,
                    "job_name": entry_class.split(".")[-1],
                    "status": "SUBMITTED",
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": f"{duration:.2f}s",
                    "message": i18n.t("components.computations.flink_job.success.job_submitted"),
                }

        finally:
            # Always cleanup temporary file
            if temp_jar_path:
                cleanup_temp_file(temp_jar_path)
                logger.info(f"[FlinkJob] Cleaned up temp file: {temp_jar_path}")

    def _extract_jar_file_id(self, jar_file_input: Any) -> str | None:
        """Extract file ID from JAR file input (same pattern as CSV/Excel components).

        Args:
            jar_file_input: JAR file input from component

        Returns:
            File ID (numeric string) or file path
        """
        # Parse JSON string if needed
        if isinstance(jar_file_input, str):
            try:
                jar_data = json.loads(jar_file_input)
                file_id = jar_data.get("file_path") or jar_data.get("value")
                logger.debug(f"[FlinkJob] Extracted from JSON: {file_id}")
                return file_id
            except json.JSONDecodeError:
                # Not JSON, might be direct file ID or path
                logger.debug(f"[FlinkJob] Using string directly: {jar_file_input}")
                return jar_file_input

        # Already a dict
        elif isinstance(jar_file_input, dict):
            file_id = jar_file_input.get("file_path") or jar_file_input.get("value")
            logger.debug(f"[FlinkJob] Extracted from dict: {file_id}")
            return file_id

        logger.warning(f"[FlinkJob] Unexpected input type: {type(jar_file_input)}")
        return None

    def submit_flink_job(self) -> Data:
        """Submit JAR job to Flink cluster."""
        try:
            datasource_id = self.flink_datasource
            if not datasource_id:
                raise ValueError(i18n.t("components.computations.flink_job.errors.no_datasource"))

            # Validate inputs
            if not self.jar_file:
                raise ValueError(i18n.t("components.computations.flink_job.errors.no_jar_file"))
            if not self.entry_class:
                raise ValueError(i18n.t("components.computations.flink_job.errors.no_entry_class"))

            # Submit JAR job
            result = asyncio.run(
                self._submit_jar_job(
                    datasource_id,
                    self.jar_file,
                    self.entry_class,
                    self.program_args or "",
                    self.parallelism,
                )
            )

            # Update status
            self.status = f"Job {result['job_id']}: {result['status']}"
            return Data(data=result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[FlinkJob] Job submission failed: {error_msg}", exc_info=True)
            self.status = f"{i18n.t('components.computations.flink_job.status.error')}: {error_msg}"

            return Data(
                data={
                    "job_id": "N/A",
                    "job_name": "N/A",
                    "status": i18n.t("components.computations.flink_job.status.failed"),
                    "start_time": "",
                    "duration": "",
                    "message": error_msg,
                }
            )
