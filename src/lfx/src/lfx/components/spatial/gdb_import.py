"""GDB入库组件 - Import GDB layer data to PostgreSQL database."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

import i18n

from lfx.custom import Component
from lfx.io import BoolInput, DropdownInput, FileInput, IntInput, StrInput
from lfx.schema import Data
from lfx.services.deps import get_feign_service
from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
from lfx.services.gdb import GDBService
from lfx.template.field.base import Output


class GDBImportComponent(Component):
    """Component for importing GDB layer data to PostgreSQL database."""

    display_name = i18n.t("components.spatial.gdb_import.display_name")
    description = i18n.t("components.spatial.gdb_import.description")
    icon = "download"
    name = "GDBImport"
    include_universal_input = True  # Enable upstream data connection

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.spatial.gdb_import.datasource_selector.display_name"),
            info=i18n.t("components.spatial.gdb_import.datasource_selector.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        DropdownInput(
            name="database_selector",
            display_name=i18n.t("components.spatial.gdb_import.database_selector.display_name"),
            info=i18n.t("components.spatial.gdb_import.database_selector.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        FileInput(
            name="file_path",
            display_name=i18n.t("components.spatial.gdb_import.file_path.display_name"),
            info=i18n.t("components.spatial.gdb_import.file_path.info"),
            file_types=["zip"],
            temp_file=False,  # Enable file browser UI
            required=False,
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.gdb_import.file_id_variable.display_name"),
            info=i18n.t("components.spatial.gdb_import.file_id_variable.info"),
            placeholder="{gdbFileId}",
            required=False,
            resolve_variables=True,  # Enable automatic variable resolution
        ),
        BoolInput(
            name="create_table",
            display_name=i18n.t("components.spatial.gdb_import.create_table.display_name"),
            info=i18n.t("components.spatial.gdb_import.create_table.info"),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="truncate_first",
            display_name=i18n.t("components.spatial.gdb_import.truncate_first.display_name"),
            info=i18n.t("components.spatial.gdb_import.truncate_first.info"),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.spatial.gdb_import.batch_size.display_name"),
            info=i18n.t("components.spatial.gdb_import.batch_size.info"),
            value=1000,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.spatial.gdb_import.outputs.result.display_name"),
            name="result",
            method="import_gdb_data",
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
            f"[GDBImport] update_build_config called - field_name: {field_name}, "
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
                logger.info(f"[GDBImport] Component init - current datasource: {current_datasource}")
                if current_datasource:
                    await self._load_databases(build_config, int(current_datasource))

        # Load databases when datasource is selected
        if field_name == "datasource_selector" and field_value:
            logger.info(f"[GDBImport] Datasource changed to: {field_value}")
            await self._load_databases(build_config, int(field_value))

        # Load databases when database selector refresh button is clicked
        if field_name == "database_selector":
            logger.info("[GDBImport] Database selector refresh triggered")
            # Try to get datasource from component instance first
            if hasattr(self, "datasource_selector") and self.datasource_selector:
                logger.info(f"[GDBImport] Loading databases for datasource (from self): {self.datasource_selector}")
                await self._load_databases(build_config, int(self.datasource_selector))
            # Fallback to build_config
            elif build_config.get("datasource_selector", {}).get("value"):
                current_datasource = build_config.get("datasource_selector", {}).get("value")
                logger.info(f"[GDBImport] Loading databases for datasource (from build_config): {current_datasource}")
                await self._load_databases(build_config, int(current_datasource))
            else:
                logger.warning("[GDBImport] No datasource selected yet")

        return build_config

    async def _load_datasources(self, build_config: dict) -> None:
        """Load PostgreSQL datasources from data-construction service."""
        try:
            feign_service = get_feign_service()
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
                    "components.spatial.gdb_import.status.datasources_loaded",
                    count=len(pg_datasources),
                )
            else:
                self.status = i18n.t("components.spatial.gdb_import.warnings.no_datasources")

        except Exception as e:
            self.status = i18n.t("components.spatial.gdb_import.errors.load_datasources_failed", error=str(e))

    async def _load_databases(self, build_config: dict, datasource_id: int) -> None:
        """Load available databases from selected PostgreSQL datasource.

        Args:
            build_config: Current build configuration
            datasource_id: Selected datasource ID
        """
        from lfx.log.logger import logger

        logger.info(
            f"[GDBImport] _load_databases called with datasource_id: {datasource_id} "
            f"(type: {type(datasource_id)})"
        )

        try:
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            # Get datasource connection info
            datasource_list = await client.get_datasource_list()

            # Filter PostgreSQL datasources for logging
            pg_datasources = [
                ds for ds in datasource_list
                if ds.get("dataSourceParam", {}).get("type", "").lower() == "postgresql"
            ]
            pg_ids = [ds["id"] for ds in pg_datasources]
            logger.info(f"[GDBImport] Available PostgreSQL datasource IDs: {pg_ids}")
            logger.info(f"[GDBImport] Looking for datasource_id: {datasource_id}, type: {type(datasource_id)}")

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
                    f"[GDBImport] Datasource with id {datasource_id} not found "
                    f"in {len(datasource_list)} datasources"
                )
                logger.warning(msg)
                logger.warning(
                    f"[GDBImport] Available PostgreSQL datasources: "
                    f"{[(ds['id'], ds['name']) for ds in pg_datasources]}"
                )
                self.status = i18n.t("components.spatial.gdb_import.warnings.datasource_not_found")
                return

            logger.info(
                f"[GDBImport] Found datasource: {datasource.get('name')} "
                f"(ID: {datasource['id']}, type: {type(datasource['id'])})"
            )

            # Extract connection parameters
            params = datasource.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 5432)
            database = params.get("database", "postgres")
            username = params.get("username", "postgres")
            password = params.get("password", "")

            logger.info(f"[GDBImport] Connecting to {username}@{host}:{port}/{database}")

            # URL encode credentials
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

            logger.info("[GDBImport] Creating database engine...")
            engine = create_engine(connection_string, poolclass=NullPool)

            with engine.connect() as conn:
                logger.info("[GDBImport] Executing query to get database list...")
                # Query non-template databases
                result = conn.execute(
                    text("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
                )
                databases = [row[0] for row in result]

            engine.dispose()

            logger.info(f"[GDBImport] Found {len(databases)} databases: {databases}")

            if databases:
                build_config["database_selector"]["options"] = databases
                build_config["database_selector"]["options_metadata"] = [
                    {"value": db, "label": db} for db in databases
                ]

                self.status = i18n.t(
                    "components.spatial.gdb_import.status.databases_loaded",
                    count=len(databases),
                )
                logger.info("[GDBImport] Database selector options updated successfully")
            else:
                self.status = i18n.t("components.spatial.gdb_import.warnings.no_databases")
                logger.warning("[GDBImport] No databases found")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[GDBImport] Failed to load databases: {error_msg}")
            self.status = i18n.t("components.spatial.gdb_import.errors.load_databases_failed", error=error_msg)

    def _extract_all_tables(self, node, result: list) -> None:
        """Recursively extract all Table and FeatureClass type layer nodes.

        Args:
            node: Current tree node (GDBTreeNode)
            result: List to accumulate table/featureclass layers (GDBTreeNode objects)
        """
        from lfx.services.gdb.models import GDBNodeType

        # Check if this node is a table or feature class (both can be imported)
        if node.node_type in (GDBNodeType.TABLE, GDBNodeType.FEATURE_CLASS):
            result.append(node)

        # Recursively process children
        for child in node.children:
            self._extract_all_tables(child, result)

    async def _get_file_id(self) -> str:
        """Get file ID from either variable, upstream data, or file input.

        Priority:
            1. file_id_variable (variable resolution with fallback)
            2. upstream_data (from connected component, e.g., GDB Create)
            3. file_path (from _parameters or self.file_path)

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
                    "components.spatial.gdb_import.errors.variable_not_resolved",
                )
                logger.info(f"[GDBImport] Using file_id from variable: {resolved_value}")
                return resolved_value

        # Priority 2: upstream_data from connected component (e.g., GDB建库)
        if hasattr(self, "upstream_data") and self.upstream_data:
            # upstream_data can be Data object or dict
            upstream_dict = self.upstream_data.data if hasattr(self.upstream_data, "data") else self.upstream_data

            if isinstance(upstream_dict, dict) and "file_id" in upstream_dict:
                file_id = upstream_dict.get("file_id")
                if file_id:
                    logger.info(f"[GDBImport] Got file_id from upstream_data: {file_id}")
                    return str(file_id)

        # Priority 3: file_path (from _parameters or self)
        file_id = None

        if hasattr(self, "_parameters"):
            file_path_param = self._parameters.get("file_path")
            if isinstance(file_path_param, dict):
                file_id = file_path_param.get("file_path") or file_path_param.get("value")
                logger.info(f"[GDBImport] Extracted file_id from dict _parameters: {file_id}")
            elif isinstance(file_path_param, str):
                if file_path_param.isdigit():
                    file_id = file_path_param
                    logger.info(f"[GDBImport] Using numeric string from _parameters as file_id: {file_id}")
                else:
                    from pathlib import Path

                    basename = Path(file_path_param).name
                    if basename.isdigit():
                        file_id = basename
                        logger.info(f"[GDBImport] Extracted file_id from cached path basename: {file_id}")
                    else:
                        file_id = file_path_param
                        logger.info(f"[GDBImport] Using path from _parameters: {file_id}")

        if not file_id and hasattr(self, "file_path") and self.file_path:
            file_id = self.file_path
            logger.info(f"[GDBImport] Fallback to self.file_path: {file_id}")

        if file_id:
            logger.info(f"[GDBImport] Using file_id from file selection: {file_id}")
            return file_id

        # No file source provided
        msg = i18n.t("components.spatial.gdb_import.errors.no_file")
        logger.error("[GDBImport] No file source provided")
        raise ValueError(msg)

    async def _get_minio_url(self, file_id: str) -> str:
        """Get MinIO URL for file.

        Args:
            file_id: File ID

        Returns:
            MinIO pre-signed URL

        Raises:
            ValueError: Failed to get file URL
        """
        from lfx.log.logger import logger

        try:
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            file_detail = await client.get_file_detail(int(file_id))

            # Check if file_detail is valid
            if not file_detail:
                msg = i18n.t("components.spatial.gdb_import.errors.no_minio_url", file_id=file_id)
                raise ValueError(msg)

            # Extract MinIO URL from file detail
            # The API returns: {code, success, data: {file: {link, domain, name}}}
            minio_url = None
            if isinstance(file_detail, dict):
                data = file_detail.get("data", {})
                if isinstance(data, dict):
                    # Priority 1: data.file.link (main location)
                    file_obj = data.get("file", {})
                    if isinstance(file_obj, dict):
                        minio_url = file_obj.get("link")
                        logger.info(f"[GDBImport] URL from data.file.link: {minio_url}")

                    # Priority 2: data.url (fallback)
                    if not minio_url:
                        minio_url = data.get("url")
                        logger.info(f"[GDBImport] URL from data.url: {minio_url}")

                # Priority 3: root.url (fallback)
                if not minio_url:
                    minio_url = file_detail.get("url")
                    logger.info(f"[GDBImport] URL from root.url: {minio_url}")

            if not minio_url:
                logger.error(
                    f"[GDBImport] No URL found in file_detail. "
                    f"Available keys: {list(file_detail.keys()) if isinstance(file_detail, dict) else 'N/A'}"
                )
                msg = i18n.t("components.spatial.gdb_import.errors.no_minio_url", file_id=file_id)
                raise ValueError(msg)

            logger.info(f"[GDBImport] Final MinIO URL: {minio_url}")
            return minio_url

        except ValueError:
            # Re-raise ValueError with translated message
            raise
        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_import.errors.get_url_failed", file_id=file_id, error=str(e))
            raise ValueError(error_msg) from e

    async def _get_connection_string(self, datasource_id: int, database: str | None = None) -> str:
        """Get PostgreSQL connection string.

        Args:
            datasource_id: Datasource ID
            database: Target database name (overrides datasource default if provided)

        Returns:
            SQLAlchemy connection string

        Raises:
            ValueError: Datasource not found
        """
        try:
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            datasource_list = await client.get_datasource_list()
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
                msg = i18n.t("components.spatial.gdb_import.errors.datasource_not_found", id=datasource_id)
                raise ValueError(msg)

            # Extract connection parameters
            params = datasource.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 5432)
            default_database = params.get("database", "postgres")
            username = params.get("username", "postgres")
            password = params.get("password", "")

            # Use selected database or fall back to default
            target_database = database if database else default_database

            # URL encode credentials
            username_encoded = quote_plus(username)
            password_encoded = quote_plus(password)

            # Use psycopg (v3) driver instead of psycopg2
            return f"postgresql+psycopg://{username_encoded}:{password_encoded}@{host}:{port}/{target_database}"

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_import.errors.get_connection_failed", error=str(e))
            raise ValueError(error_msg) from e

    def _convert_gdb_to_dataframe(self, layer_data: dict):
        """Convert GDB layer data to DataFrame.

        Args:
            layer_data: Layer data from GDB API

        Returns:
            Pandas DataFrame
        """
        import pandas as pd

        features = layer_data.get("features", [])

        if not features:
            return pd.DataFrame()

        records = []
        for feature in features:
            record = {
                "feature_id": feature.get("id"),
                **feature.get("properties", {}),
            }

            # Store geometry as WKT if present
            if feature.get("geometry"):
                import json

                record["geometry_wkt"] = json.dumps(feature["geometry"])

            records.append(record)

        return pd.DataFrame(records)

    async def import_gdb_data(self) -> Data:
        """Import all GDB table layers to PostgreSQL automatically.

        Returns:
            Data object with import results

        Raises:
            ValueError: Import failed
        """
        from lfx.log.logger import logger

        temp_zip_path = None
        gdb_id = None

        try:
            logger.info("[GDBImport] Starting import_gdb_data execution")
            self.status = i18n.t("components.spatial.gdb_import.status.importing")

            # Get datasource ID - check upstream_data first
            datasource_id = None

            # Priority 1: upstream_data from connected component (e.g., GDB建库)
            if hasattr(self, "upstream_data") and self.upstream_data:
                upstream_dict = self.upstream_data.data if hasattr(self.upstream_data, "data") else self.upstream_data

                if isinstance(upstream_dict, dict) and "pg_datasource_id" in upstream_dict:
                    pg_ds_id = upstream_dict.get("pg_datasource_id")
                    if pg_ds_id:
                        datasource_id = int(pg_ds_id)
                        logger.info(f"[GDBImport] Got datasource_id from upstream_data: {datasource_id}")

            # Priority 2: datasource_selector dropdown
            if datasource_id is None and hasattr(self, "datasource_selector") and self.datasource_selector:
                datasource_id = int(self.datasource_selector)
                logger.info(f"[GDBImport] Got datasource_id from datasource_selector: {datasource_id}")

            if datasource_id is None:
                msg = i18n.t("components.spatial.gdb_import.errors.no_datasource")
                self.status = msg
                logger.error("[GDBImport] No datasource selected")
                raise ValueError(msg)

            # Get selected database
            database = None
            if hasattr(self, "database_selector") and self.database_selector:
                database = self.database_selector
                logger.info(f"[GDBImport] Selected database: {database}")

            # Get file ID and MinIO URL
            logger.info("[GDBImport] Getting file ID...")
            file_id = await self._get_file_id()
            logger.info(f"[GDBImport] File ID: {file_id}")

            logger.info("[GDBImport] Getting MinIO URL...")
            minio_url = await self._get_minio_url(file_id)
            logger.info(f"[GDBImport] MinIO URL: {minio_url}")

            logger.info("[GDBImport] Getting database connection string...")
            connection_string = await self._get_connection_string(datasource_id, database)
            logger.info(f"[GDBImport] Connection string obtained (length: {len(connection_string)})")

            # Create GDBService instance
            gdb_service = GDBService()
            gdb_id = str(uuid4())

            # 1. Download GDB file from MinIO
            logger.info("[GDBImport] Downloading GDB file from MinIO...")
            temp_zip_path = await gdb_service.download_from_url(minio_url)
            logger.info(f"[GDBImport] Downloaded to: {temp_zip_path}")

            # 2. Extract GDB file
            logger.info("[GDBImport] Extracting GDB file...")
            extract_result = gdb_service.extract_gdb_from_zip(temp_zip_path, gdb_id)
            gdb_path = extract_result.gdb_path
            logger.info(f"[GDBImport] Extracted to: {gdb_path}")
            logger.info(f"[GDBImport] GDB name: {extract_result.gdb_name}, layers: {extract_result.layer_count}")

            # 3. Parse GDB structure to get all table layers
            logger.info("[GDBImport] Parsing GDB structure...")
            gdb_structure = gdb_service.read_gdb_tree_structure(
                gdb_path,
                include_data=True,
                limit_per_layer=100,
            )
            logger.info("[GDBImport] GDB structure parsed successfully")

            # Extract all Table and FeatureClass type layers
            table_layers = []
            self._extract_all_tables(gdb_structure.root, table_layers)
            logger.info(f"[GDBImport] Found {len(table_layers)} table/featureclass layers")

            if not table_layers:
                msg = i18n.t("components.spatial.gdb_import.warnings.no_table_layers")
                self.status = msg
                return Data(data={"success": False, "message": msg, "tables_imported": 0})

            # Import each table layer - track success, skip, and failure
            imported_tables = []
            skipped_layers = []
            failed_layers = []
            total_rows = 0

            from sqlalchemy import create_engine
            from sqlalchemy.pool import NullPool

            for layer in table_layers:
                layer_name = layer.name  # GDBTreeNode has .name attribute
                logger.info(f"[GDBImport] Processing layer: {layer_name}")

                try:
                    # Read layer data from GDB using GDBService
                    layer_data = gdb_service.read_layer_data(
                        gdb_path,
                        layer_name,
                        limit=100000,  # Large limit for full data
                        offset=0,
                    )
                    logger.info(f"[GDBImport] Layer {layer_name}: {layer_data.total_count} features")

                    # Convert to DataFrame
                    df = self._convert_gdb_to_dataframe(layer_data.model_dump())

                    if df.empty:
                        skip_reason = i18n.t("components.spatial.gdb_import.status.layer_empty")
                        logger.warning(f"[GDBImport] Layer {layer_name} has no data, skipping")
                        skipped_layers.append({
                            "layer": layer_name,
                            "reason": skip_reason,
                            "feature_count": layer_data.total_count,
                        })
                        continue

                    # Write to PostgreSQL (use layer name as table name)
                    logger.info(f"[GDBImport] Writing {len(df)} rows to PostgreSQL table: {layer_name}")
                    engine = create_engine(connection_string, poolclass=NullPool)

                    try:
                        # Auto create/replace table
                        if_exists = "replace" if self.create_table else "append"
                        if self.truncate_first and not self.create_table:
                            # Truncate table first
                            with engine.connect() as conn:
                                from sqlalchemy import text

                                conn.execute(text(f"TRUNCATE TABLE {layer_name}"))
                                conn.commit()

                        df.to_sql(
                            layer_name,  # Use layer name as table name
                            engine,
                            if_exists=if_exists,
                            index=False,
                            chunksize=self.batch_size,
                            method="multi",
                        )

                        rows_written = len(df)
                        total_rows += rows_written
                        imported_tables.append({
                            "table": layer_name,
                            "rows": rows_written,
                            "type": layer.node_type.value,
                        })
                        logger.info(f"[GDBImport] Successfully imported {rows_written} rows to table: {layer_name}")

                    finally:
                        engine.dispose()

                except Exception as layer_error:
                    error_msg = str(layer_error)
                    logger.error(f"[GDBImport] Failed to import layer {layer_name}: {error_msg}")
                    failed_layers.append({
                        "layer": layer_name,
                        "error": error_msg,
                        "type": layer.node_type.value,
                    })
                    # Continue processing other layers instead of failing completely

            # Build result with complete information
            logger.info(
                f"[GDBImport] Import completed - "
                f"Success: {len(imported_tables)}, Skipped: {len(skipped_layers)}, Failed: {len(failed_layers)}"
            )

            self.status = i18n.t(
                "components.spatial.gdb_import.status.success_with_details",
                imported=len(imported_tables),
                skipped=len(skipped_layers),
                failed=len(failed_layers),
                rows=total_rows,
            )

            return Data(
                data={
                    "success": True,
                    "tables_imported": len(imported_tables),
                    "total_rows": total_rows,
                    "imported": imported_tables,
                    "skipped": skipped_layers,
                    "failed": failed_layers,
                    "summary": {
                        "total_layers": len(table_layers),
                        "imported_count": len(imported_tables),
                        "skipped_count": len(skipped_layers),
                        "failed_count": len(failed_layers),
                    },
                }
            )

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_import.errors.import_failed", error=str(e))
            logger.exception(f"[GDBImport] Import failed: {e!s}")
            self.status = error_msg
            raise ValueError(error_msg) from e

        finally:
            # Clean up temporary files
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    logger.info(f"[GDBImport] Cleaning up temp ZIP: {temp_zip_path}")
                    os.unlink(temp_zip_path)
                except Exception as cleanup_error:
                    logger.warning(f"[GDBImport] Failed to cleanup temp ZIP: {cleanup_error}")

            if gdb_id:
                try:
                    logger.info(f"[GDBImport] Cleaning up GDB storage: {gdb_id}")
                    gdb_service = GDBService()
                    gdb_service.delete_gdb_storage(gdb_id)
                except Exception as cleanup_error:
                    logger.warning(f"[GDBImport] Failed to cleanup GDB storage: {cleanup_error}")
