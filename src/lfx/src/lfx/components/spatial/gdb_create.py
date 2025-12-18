"""GDB建库组件 - Create GDB datasource in data-governance system."""

from __future__ import annotations

import i18n

from lfx.custom import Component
from lfx.io import FileInput, MessageTextInput, StrInput
from lfx.schema import Data
from lfx.services.deps import get_feign_service
from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
from lfx.services.feign.clients.data_governance import DataGovernanceFeignClient
from lfx.template.field.base import Output


class GDBCreateComponent(Component):
    """Component for creating GDB datasource and registering to data-governance."""

    display_name = i18n.t("components.spatial.gdb_create.display_name")
    description = i18n.t("components.spatial.gdb_create.description")
    icon = "database"
    name = "GDBCreate"

    inputs = [
        FileInput(
            name="gdb_file",
            display_name=i18n.t("components.spatial.gdb_create.gdb_file.display_name"),
            info=i18n.t("components.spatial.gdb_create.gdb_file.info"),
            file_types=["zip"],
            required=False,
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.gdb_create.file_id_variable.display_name"),
            info=i18n.t("components.spatial.gdb_create.file_id_variable.info"),
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="resource_name",
            display_name=i18n.t("components.spatial.gdb_create.resource_name.display_name"),
            info=i18n.t("components.spatial.gdb_create.resource_name.info"),
            required=True,
        ),
        MessageTextInput(
            name="resource_code",
            display_name=i18n.t("components.spatial.gdb_create.resource_code.display_name"),
            info=i18n.t("components.spatial.gdb_create.resource_code.info"),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.spatial.gdb_create.outputs.datasource_id.display_name"),
            name="datasource_id",
            method="create_gdb_datasource",
        ),
        Output(
            display_name=i18n.t("components.spatial.gdb_create.outputs.result_info.display_name"),
            name="result_info",
            method="create_gdb_datasource",
        ),
    ]

    async def _get_file_id(self) -> str:
        """Get file ID from either variable or file input.

        Priority:
            1. file_id_variable (higher)
            2. gdb_file (lower)

        Returns:
            File ID string

        Raises:
            ValueError: No file source provided
        """
        # Priority 1: file_id_variable
        if hasattr(self, "file_id_variable") and self.file_id_variable:
            variable_value = self.file_id_variable.strip()
            if variable_value:
                # If it's a variable reference like {gdbFileId}, resolve it
                if variable_value.startswith("{") and variable_value.endswith("}"):
                    # Extract variable name
                    var_name = variable_value[1:-1]
                    # Try to get from vertex outputs
                    if hasattr(self, "vertex") and self.vertex and hasattr(self.vertex, "outputs"):
                        if var_name in self.vertex.outputs:
                            resolved = self.vertex.outputs[var_name]
                            if resolved:
                                return str(resolved)
                    # If not found in outputs, return the original value without braces
                    return var_name
                # Direct file ID value
                return variable_value

        # Priority 2: gdb_file
        if hasattr(self, "gdb_file") and self.gdb_file:
            # FileInput can be either a path string or an object with path attribute
            if hasattr(self.gdb_file, "path"):
                file_path = str(self.gdb_file.path)
            else:
                file_path = str(self.gdb_file)

            # Extract file ID from path (assuming format like "file_123" or just "123")
            # If it's a full path, try to extract the file ID from the filename
            if "/" in file_path or "\\" in file_path:
                from pathlib import Path

                filename = Path(file_path).stem
                # Try to extract numeric ID from filename
                import re

                match = re.search(r"\d+", filename)
                if match:
                    return match.group(0)
                return filename
            return file_path

        # No file source provided
        msg = i18n.t("components.spatial.gdb_create.errors.no_file")
        raise ValueError(msg)

    async def create_gdb_datasource(self) -> Data:
        """Create GDB datasource in data-governance system.

        Returns:
            Data object containing datasource_id and other creation info

        Raises:
            ValueError: Missing required parameters or creation failed
        """
        try:
            # Step 1: Validate resource parameters
            if not all([self.resource_name, self.resource_code]):
                msg = i18n.t("components.spatial.gdb_create.errors.missing_params")
                raise ValueError(msg)

            # Update status
            self.status = i18n.t("components.spatial.gdb_create.status.creating")

            # Step 2: Get file ID
            file_id = await self._get_file_id()

            # Step 3: Call data-governance API
            feign_service = get_feign_service()
            governance_client = DataGovernanceFeignClient(feign_service)

            resource_params = {
                "name": self.resource_name,
                "code": self.resource_code,
            }

            result = await governance_client.create_gdb_datasource(
                file_id=file_id,
                resource_params=resource_params,
            )

            # Step 4: Update status and return result
            datasource_id = result.get("datasource_id") or result.get("id")
            self.status = i18n.t(
                "components.spatial.gdb_create.status.success",
                datasource_id=datasource_id,
                resource_name=self.resource_name,
            )

            return Data(
                data={
                    "datasource_id": datasource_id,
                    "resource_name": self.resource_name,
                    "resource_code": self.resource_code,
                    **result,
                }
            )

        except Exception as e:
            error_msg = i18n.t("components.spatial.gdb_create.errors.creation_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
