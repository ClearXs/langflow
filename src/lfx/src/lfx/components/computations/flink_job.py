import asyncio
import datetime
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
            # Use 'value' (ID) as the option value, not display_name
            build_config["flink_datasource"]["options"] = [ds["value"] for ds in datasources]
            build_config["flink_datasource"]["options_metadata"] = datasources

        return build_config

    async def _load_flink_datasources_async(self) -> list[dict]:
        """Load unified Flink datasources (builtin + public) asynchronously."""
        try:
            builtin_datasources = await self._get_builtin_flink_datasources_async()
            public_datasources = await self._get_public_flink_clusters_async()

            # Combine both lists
            all_datasources = builtin_datasources + public_datasources

            logger.info(
                f"Loaded {len(builtin_datasources)} builtin and {len(public_datasources)} public Flink datasources"
            )

            return all_datasources

        except Exception as e:
            logger.error(f"Failed to load Flink datasources: {e}")
            return []

    def _load_flink_datasources(self) -> list[dict]:
        """Load unified Flink datasources (builtin + public) - sync wrapper."""
        try:
            return asyncio.run(self._load_flink_datasources_async())
        except RuntimeError:
            # If we're already in an event loop, we can't use asyncio.run
            logger.warning("[FlinkJob] Cannot use asyncio.run in active event loop, returning empty list")
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

    async def _get_builtin_flink_datasources_async(self) -> list[dict]:
        """Get builtin (custom) Flink datasources asynchronously."""
        try:
            from lfx.base.datasource.manager import DataSourceManager

            # Initialize datasource manager
            if not hasattr(self, "datasource_manager"):
                self.datasource_manager = DataSourceManager()

            # Get datasources using correct API
            datasources = await self.datasource_manager.get_datasources()
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

    def _get_builtin_flink_datasources(self) -> list[dict]:
        """Get builtin (custom) Flink datasources - sync wrapper."""
        try:
            return asyncio.run(self._get_builtin_flink_datasources_async())
        except RuntimeError:
            logger.warning("[FlinkJob] Cannot load builtin datasources in active event loop")
            return []

    async def _get_public_flink_clusters_async(self) -> list[dict]:
        """Get public Flink clusters from data-stream service asynchronously."""
        try:
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.data_stream import DataStreamFeignClient

            feign_service = get_feign_service()
            client = DataStreamFeignClient(feign_service)

            # Async call to get cluster list
            cluster_list = await client.get_flink_cluster_list()

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

    def _get_public_flink_clusters(self) -> list[dict]:
        """Get public Flink clusters from data-stream service - sync wrapper."""
        try:
            return asyncio.run(self._get_public_flink_clusters_async())
        except RuntimeError:
            logger.warning("[FlinkJob] Cannot load public clusters in active event loop")
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

    async def _find_datasource_by_display_name_async(self, display_name: str) -> dict | None:
        """Find datasource in cached options_metadata by display name (async version)."""
        try:
            logger.debug(f"[FlinkJob] Searching for datasource by display_name: {display_name}")
            logger.debug(f"[FlinkJob] Has _input_dict: {hasattr(self, '_input_dict')}")

            # Access cached metadata from update_build_config
            if hasattr(self, "_input_dict") and self._input_dict:
                flink_datasource_input = self._input_dict.get("flink_datasource")
                logger.debug(f"[FlinkJob] flink_datasource_input found: {flink_datasource_input is not None}")

                if flink_datasource_input and hasattr(flink_datasource_input, "options_metadata"):
                    options_metadata = flink_datasource_input.options_metadata
                    logger.debug(
                        f"[FlinkJob] options_metadata length: {len(options_metadata) if options_metadata else 0}"
                    )

                    if options_metadata:
                        for ds in options_metadata:
                            ds_display = ds.get("display_name")
                            ds_label = ds.get("label")
                            logger.debug(
                                f"[FlinkJob] Checking datasource: display_name={ds_display}, label={ds_label}, id={ds.get('id')}"
                            )

                            if ds_display == display_name or ds_label == display_name:
                                logger.info(
                                    f"[FlinkJob] Found datasource by display_name: {display_name} -> {ds.get('id')}"
                                )
                                return ds
                else:
                    logger.warning(f"[FlinkJob] flink_datasource_input has no options_metadata attribute")
            else:
                logger.warning(f"[FlinkJob] _input_dict not available or empty")

            # Fallback: Try to load datasources directly using async version
            logger.info(f"[FlinkJob] Falling back to direct datasource loading (async)")
            datasources = await self._load_flink_datasources_async()
            logger.debug(f"[FlinkJob] Loaded {len(datasources)} datasources for lookup")

            for ds in datasources:
                ds_display = ds.get("display_name")
                ds_label = ds.get("label")

                if ds_display == display_name or ds_label == display_name:
                    logger.info(f"[FlinkJob] Found datasource via fallback: {display_name} -> {ds.get('id')}")
                    return ds

        except Exception as e:
            logger.error(f"[FlinkJob] Failed to find datasource by display_name: {e}", exc_info=True)

        return None

    async def _get_flink_connection_info(self, datasource_id: str) -> dict:
        """Get Flink connection information from datasource.

        Args:
            datasource_id: Datasource ID (UUID)
        """
        try:
            logger.info(f"[FlinkJob] Getting connection info for datasource ID: {datasource_id}")

            # Find datasource in cached metadata by ID
            datasource = self._find_datasource_by_id(datasource_id)
            logger.debug(f"[FlinkJob] Find by ID result: {datasource is not None}")

            if not datasource:
                logger.warning(f"[FlinkJob] Datasource not found in metadata cache, querying DataSourceManager")
                # Fallback to DataSourceManager
                from lfx.base.datasource.manager import DataSourceManager

                manager = DataSourceManager()
                datasource_dict = await manager._get_datasource_by_id(datasource_id)

                if not datasource_dict:
                    raise ValueError(f"Datasource not found: {datasource_id}")

                # Extract connection info from datasource
                return self._extract_connection_info_from_datasource(datasource_dict)

            # Found datasource in metadata
            logger.info(
                f"[FlinkJob] Found datasource in metadata: {datasource.get('name')} (source={datasource.get('source')})"
            )

            # Check source to determine how to extract connection info
            source = datasource.get("source", "builtin")

            if source == "public":
                # Extract from public datasource (raw_data)
                return self._build_public_flink_connection_info(datasource)

            # Extract from builtin datasource using DataSourceManager
            from lfx.base.datasource.manager import DataSourceManager

            manager = DataSourceManager()

            # Use the ID from cached datasource (already has correct prefix: custom_ or enterprise_)
            actual_id = datasource.get("id")
            logger.info(f"[FlinkJob] Looking up builtin datasource with ID: {actual_id}")

            # Use await instead of asyncio.run()
            builtin_ds = await manager._get_datasource_by_id(actual_id)

            if not builtin_ds:
                raise ValueError(f"Builtin datasource not found: {actual_id}")

            # Extract connection info from datasource
            return self._extract_connection_info_from_datasource(builtin_ds)

        except Exception as e:
            logger.error(f"[FlinkJob] Failed to get Flink connection info: {e}", exc_info=True)
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
        logger.info(f"[FlinkJob] Extracting connection info from datasource: {datasource.get('name', 'Unknown')}")
        logger.debug(f"[FlinkJob] Datasource keys: {list(datasource.keys())}")

        # Try to get from advanced_config first (for Flink datasources)
        advanced_config = datasource.get("advanced_config", {})
        logger.debug(f"[FlinkJob] advanced_config type: {type(advanced_config)}, value: {advanced_config}")

        if isinstance(advanced_config, str):
            try:
                import json

                advanced_config = json.loads(advanced_config)
                logger.debug(f"[FlinkJob] Parsed advanced_config: {advanced_config}")
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"[FlinkJob] Failed to parse advanced_config as JSON")
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
            return url, 8081

        # Try to extract Flink-specific config
        jobmanager_host = None
        rest_port = None

        # First try advanced_config
        if advanced_config.get("jobmanager_host"):
            jobmanager_host = advanced_config.get("jobmanager_host")
            rest_port = advanced_config.get("rest_port") or 8081
            logger.info(f"[FlinkJob] Found jobmanager_host in advanced_config: {jobmanager_host}:{rest_port}")
        elif advanced_config.get("host"):
            # Parse host which might contain URL with port
            jobmanager_host, rest_port = parse_url(advanced_config.get("host"))
            logger.info(f"[FlinkJob] Parsed host from advanced_config: {jobmanager_host}:{rest_port}")
        elif datasource.get("host"):
            # Parse datasource host which might contain URL with port
            jobmanager_host, rest_port = parse_url(datasource.get("host"))
            logger.info(f"[FlinkJob] Parsed host from datasource: {jobmanager_host}:{rest_port}")
        else:
            jobmanager_host = "localhost"
            rest_port = 8081
            logger.warning(f"[FlinkJob] No host configuration found, using default: {jobmanager_host}:{rest_port}")

        jobmanager_port = advanced_config.get("jobmanager_port") or 6123

        logger.info(
            f"[FlinkJob] Extracted connection info: host={jobmanager_host}, "
            f"rest_port={rest_port}, jobmanager_port={jobmanager_port}"
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
        self, datasource_id: str, file_id: str, entry_class: str, program_args: str, parallelism: int
    ) -> dict:
        """Submit JAR job to Flink cluster with datasource file download.

        Args:
            datasource_id: Flink datasource ID
            file_id: File ID (numeric) or file path
            entry_class: Main class entry point
            program_args: Program arguments
            parallelism: Job parallelism

        Returns:
            Job information dictionary
        """
        # Get Flink connection info
        conn_info = await self._get_flink_connection_info(datasource_id)
        rest_url = f"http://{conn_info['jobmanager_host']}:{conn_info['rest_port']}"

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

            # Extract file ID from _parameters (same pattern as CSV Input)
            logger.info(
                f"[FlinkJob] submit_flink_job called with jar_file: {self.jar_file} (type: {type(self.jar_file)})"
            )
            logger.info(f"[FlinkJob] _parameters keys: {list(self._parameters.keys())}")

            # Try to get file_id from multiple sources
            file_id = None

            # 1. Check if _parameters has the original jar_file structure
            jar_file_param = self._parameters.get("jar_file")
            if isinstance(jar_file_param, dict):
                file_id = jar_file_param.get("file_path") or jar_file_param.get("value")
                logger.info(f"[FlinkJob] Extracted file_id from dict _parameters: {file_id}")

            # 2. If _parameters has a string path, check if it looks like a file ID
            elif isinstance(jar_file_param, str):
                # Check if it's a numeric file ID
                if jar_file_param.isdigit():
                    file_id = jar_file_param
                    logger.info(f"[FlinkJob] Using numeric string from _parameters as file_id: {file_id}")
                else:
                    # It's a path (could be cached path or real path)
                    # Try to extract file ID from the path if it looks like /path/to/cache/123456
                    basename = os.path.basename(jar_file_param)
                    if basename.isdigit():
                        file_id = basename
                        logger.info(f"[FlinkJob] Extracted file_id from cached path basename: {file_id}")
                    else:
                        # It's a real file path, use it directly
                        file_id = jar_file_param
                        logger.info(f"[FlinkJob] Using path from _parameters: {file_id}")

            # 3. Fallback to self.jar_file
            if not file_id and self.jar_file:
                file_id = self.jar_file
                logger.info(f"[FlinkJob] Fallback to self.jar_file: {file_id}")

            if not file_id:
                raise ValueError(i18n.t("components.computations.flink_job.errors.no_jar_file"))

            # Submit JAR job with extracted file_id
            result = asyncio.run(
                self._submit_jar_job(
                    datasource_id,
                    file_id,
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
