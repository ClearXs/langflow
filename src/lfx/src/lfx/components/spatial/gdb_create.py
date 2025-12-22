"""GDB建库组件 - Create GDB datasource in data-governance system."""

from __future__ import annotations

from typing import Any

import i18n

from lfx.custom import Component
from lfx.io import DropdownInput, FileInput, StrInput
from lfx.schema import Data
from lfx.services.deps import get_feign_service
from lfx.services.feign.clients.data_governance import DataGovernanceFeignClient
from lfx.template.field.base import Output


class GDBCreateComponent(Component):
    """Component for creating GDB datasource and registering to data-governance."""

    display_name = i18n.t("components.spatial.gdb_create.display_name")
    description = i18n.t("components.spatial.gdb_create.description")
    icon = "database"
    name = "GDBCreate"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.spatial.gdb_create.datasource_selector.display_name"),
            info=i18n.t("components.spatial.gdb_create.datasource_selector.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        DropdownInput(
            name="database_selector",
            display_name=i18n.t("components.spatial.gdb_create.database_selector.display_name"),
            info=i18n.t("components.spatial.gdb_create.database_selector.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        FileInput(
            name="file_path",
            display_name=i18n.t("components.spatial.gdb_create.file_path.display_name"),
            info=i18n.t("components.spatial.gdb_create.file_path.info"),
            file_types=["zip"],
            temp_file=False,  # Enable file browser UI
            required=False,
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.gdb_create.file_id_variable.display_name"),
            info=i18n.t("components.spatial.gdb_create.file_id_variable.info"),
            placeholder="{gdbFileId}",
            required=False,
            resolve_variables=True,  # Enable automatic variable resolution
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.spatial.gdb_create.outputs.result_info.display_name"),
            name="result_info",
            method="create_gdb_datasource",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ) -> dict:
        """Dynamic configuration updates.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button clicked (if any)
        """
        from lfx.log.logger import logger

        logger.info(
            f"[GDBCreate] update_build_config called - field_name: {field_name}, "
            f"field_value: {field_value}, action: {action}"
        )

        # Load PostgreSQL datasources when component initializes or datasource selector is refreshed
        if field_name is None or field_name == "datasource_selector":
            await self._load_datasources(build_config)

            # After loading datasources, check if we need to load databases
            # This handles the case when datasource is already selected (e.g., from saved state)
            if field_name is None:
                # Component initialization - check if datasource_selector has a value
                current_datasource = build_config.get("datasource_selector", {}).get("value")
                logger.info(f"[GDBCreate] Component init - current datasource: {current_datasource}")
                if current_datasource:
                    await self._load_databases(build_config, int(current_datasource))

        # Load databases when datasource is selected
        if field_name == "datasource_selector" and field_value:
            logger.info(f"[GDBCreate] Datasource changed to: {field_value}")
            await self._load_databases(build_config, int(field_value))

        # Load databases when database selector refresh button is clicked
        if field_name == "database_selector":
            logger.info("[GDBCreate] Database selector refresh triggered")
            # Try to get datasource from component instance first
            if hasattr(self, "datasource_selector") and self.datasource_selector:
                logger.info(f"[GDBCreate] Loading databases for datasource (from self): {self.datasource_selector}")
                await self._load_databases(build_config, int(self.datasource_selector))
            # Fallback to build_config
            elif build_config.get("datasource_selector", {}).get("value"):
                current_datasource = build_config.get("datasource_selector", {}).get("value")
                logger.info(f"[GDBCreate] Loading databases for datasource (from build_config): {current_datasource}")
                await self._load_databases(build_config, int(current_datasource))
            else:
                logger.warning("[GDBCreate] No datasource selected yet")

        return build_config

    async def _load_datasources(self, build_config: dict) -> None:
        """Load PostgreSQL datasources from data-construction service."""
        try:
            feign_service = get_feign_service()
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
            client = DataConstructionFeignClient(feign_service)
            datasource_list = await client.get_datasource_list()

            # Filter PostgreSQL datasources
            pg_datasources = [
                ds
                for ds in datasource_list
                if ds.get("dataSourceParam", {}).get("type", "").lower() == "postgresql"
            ]

            # Update dropdown options
            if pg_datasources:
                options = [ds["id"] for ds in pg_datasources]
                options_metadata = [
                    {
                        "value": ds["id"],
                        "label": f"{ds['name']} ({ds.get('dataSourceParam', {}).get('host', 'N/A')})",
                        "raw_data": ds,
                    }
                    for ds in pg_datasources
                ]

                build_config["datasource_selector"]["options"] = options
                build_config["datasource_selector"]["options_metadata"] = options_metadata

                self.status = i18n.t(
                    "components.spatial.gdb_create.status.datasources_loaded",
                    count=len(pg_datasources),
                )
            else:
                self.status = i18n.t("components.spatial.gdb_create.warnings.no_datasources")

        except Exception as e:
            self.status = i18n.t("components.spatial.gdb_create.errors.load_datasources_failed", error=str(e))

    async def _load_databases(self, build_config: dict, datasource_id: int) -> None:
        """Load available databases from selected PostgreSQL datasource.

        Args:
            build_config: Current build configuration
            datasource_id: Selected datasource ID
        """
        from lfx.log.logger import logger

        logger.info(
            f"[GDBCreate] _load_databases called with datasource_id: {datasource_id} "
            f"(type: {type(datasource_id)})"
        )

        try:
            feign_service = get_feign_service()
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
            client = DataConstructionFeignClient(feign_service)

            # Get datasource connection info
            datasource_list = await client.get_datasource_list()

            # Filter PostgreSQL datasources for logging
            pg_datasources = [
                ds for ds in datasource_list
                if ds.get("dataSourceParam", {}).get("type", "").lower() == "postgresql"
            ]
            pg_ids = [ds["id"] for ds in pg_datasources]
            logger.info(f"[GDBCreate] Available PostgreSQL datasource IDs: {pg_ids}")
            logger.info(f"[GDBCreate] Looking for datasource_id: {datasource_id}, type: {type(datasource_id)}")

            # IMPORTANT: Compare both as integers and as strings to handle type mismatches
            datasource = next(
                (
                    ds
                    for ds in datasource_list
                    if ds["id"] == datasource_id or str(ds["id"]) == str(datasource_id)
                ),
                None,
            )

            if not datasource:
                msg = (
                    f"[GDBCreate] Datasource with id {datasource_id} not found "
                    f"in {len(datasource_list)} datasources"
                )
                logger.warning(msg)
                logger.warning(
                    f"[GDBCreate] Available PostgreSQL datasources: "
                    f"{[(ds['id'], ds['name']) for ds in pg_datasources]}"
                )
                self.status = i18n.t("components.spatial.gdb_create.warnings.datasource_not_found")
                return

            logger.info(
                f"[GDBCreate] Found datasource: {datasource.get('name')} "
                f"(ID: {datasource['id']}, type: {type(datasource['id'])})"
            )

            # Extract connection parameters
            params = datasource.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 5432)
            database = params.get("database", "postgres")
            username = params.get("username", "postgres")
            password = params.get("password", "")

            logger.info(f"[GDBCreate] Connecting to {username}@{host}:{port}/{database}")

            # URL encode credentials
            from urllib.parse import quote_plus
            username_encoded = quote_plus(username)
            password_encoded = quote_plus(password)

            # Connect to default database to query available databases
            # Use psycopg (v3) driver instead of psycopg2
            connection_string = (
                f"postgresql+psycopg://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
            )

            # Query available databases
            from sqlalchemy import create_engine, text
            from sqlalchemy.pool import NullPool

            logger.info("[GDBCreate] Creating database engine...")
            engine = create_engine(connection_string, poolclass=NullPool)

            with engine.connect() as conn:
                logger.info("[GDBCreate] Executing query to get database list...")
                # Query non-template databases
                result = conn.execute(
                    text("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
                )
                databases = [row[0] for row in result]

            engine.dispose()

            logger.info(f"[GDBCreate] Found {len(databases)} databases: {databases}")

            if databases:
                build_config["database_selector"]["options"] = databases
                build_config["database_selector"]["options_metadata"] = [
                    {"value": db, "label": db} for db in databases
                ]

                self.status = i18n.t(
                    "components.spatial.gdb_create.status.databases_loaded",
                    count=len(databases),
                )
                logger.info("[GDBCreate] Database selector options updated successfully")
            else:
                self.status = i18n.t("components.spatial.gdb_create.warnings.no_databases")
                logger.warning("[GDBCreate] No databases found")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[GDBCreate] Failed to load databases: {error_msg}")
            self.status = i18n.t("components.spatial.gdb_create.errors.load_databases_failed", error=error_msg)

    async def _get_file_id(self) -> str:
        """Get file ID from either variable or file input.

        Priority:
            1. file_id_variable (variable resolution with fallback)
            2. file_path (from _parameters or self.file_path)

        Returns:
            File ID string

        Raises:
            ValueError: No file source provided
        """
        from lfx.log.logger import logger

        # Priority 1: file_id_variable (with automatic + manual fallback resolution)
        if hasattr(self, "file_id_variable") and self.file_id_variable:
            variable_value = self.file_id_variable.strip()
            if variable_value:
                # Use base class helper for variable resolution with fallback
                resolved_value = self._resolve_variable_with_fallback(
                    variable_value,
                    "components.spatial.gdb_create.errors.variable_not_resolved",
                )
                logger.info(f"[GDBCreate] Using file_id from variable: {resolved_value}")
                return resolved_value

        # Priority 2: file_path (from _parameters or self)
        file_id = None

        if hasattr(self, "_parameters"):
            file_path_param = self._parameters.get("file_path")
            if isinstance(file_path_param, dict):
                file_id = file_path_param.get("file_path") or file_path_param.get("value")
                logger.info(f"[GDBCreate] Extracted file_id from dict _parameters: {file_id}")
            elif isinstance(file_path_param, str):
                if file_path_param.isdigit():
                    file_id = file_path_param
                    logger.info(f"[GDBCreate] Using numeric string from _parameters as file_id: {file_id}")
                else:
                    from pathlib import Path

                    basename = Path(file_path_param).name
                    if basename.isdigit():
                        file_id = basename
                        logger.info(f"[GDBCreate] Extracted file_id from cached path basename: {file_id}")
                    else:
                        file_id = file_path_param
                        logger.info(f"[GDBCreate] Using path from _parameters: {file_id}")

        if not file_id and hasattr(self, "file_path") and self.file_path:
            file_id = self.file_path
            logger.info(f"[GDBCreate] Fallback to self.file_path: {file_id}")

        if file_id:
            logger.info(f"[GDBCreate] Using file_id from file selection: {file_id}")
            return file_id

        # No file source provided
        msg = i18n.t("components.spatial.gdb_create.errors.no_file")
        logger.error("[GDBCreate] No file source provided")
        raise ValueError(msg)

    async def create_gdb_datasource(self) -> Data:
        """Create GDB datasource and register to data-governance system.

        Collects and passes to API:
        1. GDB file ID
        2. PostgreSQL datasource ID and complete connection information
        3. Target database name

        Returns:
            Data object - API result information

        Raises:
            ValueError: Missing required parameters or creation failed
        """
        from lfx.log.logger import logger

        try:
            # Step 1: Validate required parameters
            if not hasattr(self, "datasource_selector") or not self.datasource_selector:
                msg = i18n.t("components.spatial.gdb_create.errors.no_datasource")
                logger.error("[GDBCreate] No PostgreSQL datasource selected")
                raise ValueError(msg)

            if not hasattr(self, "database_selector") or not self.database_selector:
                msg = i18n.t("components.spatial.gdb_create.errors.no_database")
                logger.error("[GDBCreate] No target database selected")
                raise ValueError(msg)

            self.status = i18n.t("components.spatial.gdb_create.status.creating")
            logger.info("[GDBCreate] Starting GDB datasource creation...")

            # Step 2: Get GDB file ID
            file_id = await self._get_file_id()
            logger.info(f"[GDBCreate] GDB file ID: {file_id}")

            # Step 3: Get PostgreSQL datasource ID
            datasource_id = int(self.datasource_selector)
            logger.info(f"[GDBCreate] PostgreSQL datasource ID: {datasource_id}")
            logger.info(f"[GDBCreate] Target database: {self.database_selector}")

            # Step 4: Call data-governance API
            feign_service = get_feign_service()
            governance_client = DataGovernanceFeignClient(feign_service)

            logger.info("[GDBCreate] Calling data-governance API...")
            result = await governance_client.create_gdb_datasource(
                datasource_id=datasource_id,
                database_name=self.database_selector,
                resource_id=file_id,
            )

            # Step 5: Update status and return result
            datasource_id_result = result.get("datasource_id") or result.get("id")
            self.status = i18n.t(
                "components.spatial.gdb_create.status.success",
                datasource_id=datasource_id_result,
            )
            logger.info(f"[GDBCreate] Successfully created GDB datasource: {datasource_id_result}")

            return Data(data=result)

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_create.errors.creation_failed", error=str(e))
            logger.exception(f"[GDBCreate] Failed to create GDB datasource: {e}")
            self.status = error_msg
            raise ValueError(error_msg) from e
