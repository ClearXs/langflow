"""GDB入库组件 - Import GDB layer data to PostgreSQL database."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

import httpx
import i18n

from lfx.custom import Component
from lfx.io import BoolInput, DropdownInput, FileInput, IntInput, MessageTextInput, StrInput, TableInput
from lfx.schema import Data
from lfx.services.deps import get_feign_service
from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
from lfx.template.field.base import Output


class GDBImportComponent(Component):
    """Component for importing GDB layer data to PostgreSQL database."""

    display_name = i18n.t("components.spatial.gdb_import.display_name")
    description = i18n.t("components.spatial.gdb_import.description")
    icon = "download"
    name = "GDBImport"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.spatial.gdb_import.datasource_selector.display_name"),
            info=i18n.t("components.spatial.gdb_import.datasource_selector.info"),
            options=[],
            required=True,
            refresh_button=True,
        ),
        FileInput(
            name="gdb_file",
            display_name=i18n.t("components.spatial.gdb_import.gdb_file.display_name"),
            info=i18n.t("components.spatial.gdb_import.gdb_file.info"),
            file_types=["zip"],
            required=False,
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.gdb_import.file_id_variable.display_name"),
            info=i18n.t("components.spatial.gdb_import.file_id_variable.info"),
            required=False,
            advanced=True,
        ),
        TableInput(
            name="layer_selector",
            display_name=i18n.t("components.spatial.gdb_import.layer_selector.display_name"),
            info=i18n.t("components.spatial.gdb_import.layer_selector.info"),
            table_schema=[
                {
                    "name": "layer_name",
                    "display_name": i18n.t("components.spatial.gdb_import.layer_selector.layer_name"),
                    "type": "str",
                },
                {
                    "name": "feature_count",
                    "display_name": i18n.t("components.spatial.gdb_import.layer_selector.feature_count"),
                    "type": "int",
                },
                {
                    "name": "geometry_type",
                    "display_name": i18n.t("components.spatial.gdb_import.layer_selector.geometry_type"),
                    "type": "str",
                },
            ],
            value=[],
            table_options={
                "action_buttons": [
                    {
                        "name": "load_layers",
                        "label": i18n.t("components.spatial.gdb_import.layer_selector.load_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        MessageTextInput(
            name="target_table",
            display_name=i18n.t("components.spatial.gdb_import.target_table.display_name"),
            info=i18n.t("components.spatial.gdb_import.target_table.info"),
            required=True,
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
        # Load PostgreSQL datasources
        if field_name is None or field_name == "datasource_selector":
            await self._load_datasources(build_config)

        # Load GDB layers when button clicked
        if field_name == "layer_selector" and action == "load_layers":
            await self._load_gdb_layers(build_config)

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

    async def _load_gdb_layers(self, build_config: dict) -> None:
        """Load GDB layers from file."""
        try:
            self.status = i18n.t("components.spatial.gdb_import.status.loading_layers")

            # Get file ID and MinIO URL
            file_id = await self._get_file_id()
            minio_url = await self._get_minio_url(file_id)

            # Parse GDB structure
            api_url = self._get_api_url()
            async with httpx.AsyncClient(timeout=180.0) as http_client:
                response = await http_client.post(
                    f"{api_url}/api/v1/gdb/parse-from-url",
                    json={"minio_url": minio_url},
                )
                response.raise_for_status()
                gdb_structure = response.json()

            # Extract Table type layers
            table_layers = []
            self._extract_table_layers(gdb_structure.get("root", {}), table_layers)

            if table_layers:
                # Populate TableInput
                build_config["layer_selector"]["value"] = [
                    {
                        "layer_name": layer["name"],
                        "feature_count": layer.get("feature_count", 0),
                        "geometry_type": layer.get("geometry_type", "Table"),
                    }
                    for layer in table_layers
                ]

                self.status = i18n.t(
                    "components.spatial.gdb_import.status.layers_loaded",
                    count=len(table_layers),
                )
            else:
                self.status = i18n.t("components.spatial.gdb_import.warnings.no_table_layers")

        except Exception as e:
            self.status = i18n.t("components.spatial.gdb_import.errors.load_layers_failed", error=str(e))

    def _extract_table_layers(self, node: dict, result: list[dict]) -> None:
        """Recursively extract Table type layer nodes.

        Args:
            node: Current tree node
            result: List to accumulate table layers
        """
        if node.get("node_type") == "table":
            result.append(node)

        for child in node.get("children", []):
            self._extract_table_layers(child, result)

    async def _get_file_id(self) -> str:
        """Get file ID from either variable or file input.

        Returns:
            File ID string

        Raises:
            ValueError: No file source provided
        """
        # Priority 1: file_id_variable
        if hasattr(self, "file_id_variable") and self.file_id_variable:
            variable_value = self.file_id_variable.strip()
            if variable_value:
                # Variable reference like {gdbFileId}
                if variable_value.startswith("{") and variable_value.endswith("}"):
                    var_name = variable_value[1:-1]
                    if hasattr(self, "vertex") and self.vertex and hasattr(self.vertex, "outputs"):
                        if var_name in self.vertex.outputs:
                            resolved = self.vertex.outputs[var_name]
                            if resolved:
                                return str(resolved)
                    return var_name
                return variable_value

        # Priority 2: gdb_file
        if hasattr(self, "gdb_file") and self.gdb_file:
            if hasattr(self.gdb_file, "path"):
                file_path = str(self.gdb_file.path)
            else:
                file_path = str(self.gdb_file)

            # Extract file ID from path
            if "/" in file_path or "\\" in file_path:
                from pathlib import Path

                filename = Path(file_path).stem
                match = re.search(r"\d+", filename)
                if match:
                    return match.group(0)
                return filename
            return file_path

        msg = i18n.t("components.spatial.gdb_import.errors.no_file")
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
        try:
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            file_detail = await client.get_file_detail(int(file_id))

            # Extract MinIO URL from file detail
            minio_url = file_detail.get("data", {}).get("url") or file_detail.get("url")

            if not minio_url:
                msg = i18n.t("components.spatial.gdb_import.errors.no_minio_url", file_id=file_id)
                raise ValueError(msg)

            return minio_url

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_import.errors.get_url_failed", file_id=file_id, error=str(e))
            raise ValueError(error_msg) from e

    def _get_api_url(self) -> str:
        """Get Langflow API URL.

        Returns:
            API base URL
        """
        import os

        # Get from environment or use default
        return os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

    async def _get_connection_string(self, datasource_id: int) -> str:
        """Get PostgreSQL connection string.

        Args:
            datasource_id: Datasource ID

        Returns:
            SQLAlchemy connection string

        Raises:
            ValueError: Datasource not found
        """
        try:
            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)

            datasource_list = await client.get_datasource_list()
            datasource = next((ds for ds in datasource_list if ds["id"] == datasource_id), None)

            if not datasource:
                msg = i18n.t("components.spatial.gdb_import.errors.datasource_not_found", id=datasource_id)
                raise ValueError(msg)

            # Extract connection parameters
            params = datasource.get("dataSourceParam", {})
            host = params.get("host", "localhost")
            port = params.get("port", 5432)
            database = params.get("database", "postgres")
            username = params.get("username", "postgres")
            password = params.get("password", "")

            # URL encode credentials
            username_encoded = quote_plus(username)
            password_encoded = quote_plus(password)

            return f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"

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
        """Import GDB layer data to PostgreSQL.

        Returns:
            Data object with import results

        Raises:
            ValueError: Import failed
        """
        try:
            # Validate inputs
            if not self.layer_selector:
                msg = i18n.t("components.spatial.gdb_import.errors.no_layers_selected")
                raise ValueError(msg)

            if not self.target_table:
                msg = i18n.t("components.spatial.gdb_import.errors.no_target_table")
                raise ValueError(msg)

            self.status = i18n.t("components.spatial.gdb_import.status.importing")

            # Get file and datasource info
            file_id = await self._get_file_id()
            minio_url = await self._get_minio_url(file_id)
            connection_string = await self._get_connection_string(int(self.datasource_selector))

            # Get selected layer (first one from table)
            selected_layer = self.layer_selector[0]["layer_name"]

            # Read layer data from GDB
            api_url = self._get_api_url()
            async with httpx.AsyncClient(timeout=300.0) as http_client:
                response = await http_client.post(
                    f"{api_url}/api/v1/gdb/layer-data-from-url",
                    json={
                        "minio_url": minio_url,
                        "layer_name": selected_layer,
                        "limit": 100000,  # Large limit for full data
                        "offset": 0,
                    },
                )
                response.raise_for_status()
                layer_data = response.json()

            # Convert to DataFrame
            df = self._convert_gdb_to_dataframe(layer_data)

            if df.empty:
                msg = i18n.t("components.spatial.gdb_import.warnings.no_data")
                self.status = msg
                return Data(data={"success": False, "message": msg, "rows_written": 0})

            # Write to PostgreSQL
            from sqlalchemy import create_engine
            from sqlalchemy.pool import NullPool

            engine = create_engine(connection_string, poolclass=NullPool)

            if_exists = "replace" if self.create_table else "append"
            if self.truncate_first and not self.create_table:
                # Truncate table first
                with engine.connect() as conn:
                    conn.execute(f"TRUNCATE TABLE {self.target_table}")

            df.to_sql(
                self.target_table,
                engine,
                if_exists=if_exists,
                index=False,
                chunksize=self.batch_size,
                method="multi",
            )

            # Success
            rows_written = len(df)
            self.status = i18n.t(
                "components.spatial.gdb_import.status.success",
                rows=rows_written,
                table=self.target_table,
            )

            return Data(
                data={
                    "success": True,
                    "rows_written": rows_written,
                    "table": self.target_table,
                    "layer_name": selected_layer,
                }
            )

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_import.errors.import_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
