from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, FileInput, IntInput, Output, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.services.feign.clients.data_construction import cleanup_temp_file, download_file_by_id

# ★★★ MODULE LOADED: data-construction/excel_input.py UPDATED 2025-10-21 ★★★
print("★★★ [data-construction] EXCEL_INPUT MODULE LOADED - file_path EXTRACTION FIX ★★★")
logger.info("★★★ [data-construction] EXCEL_INPUT MODULE LOADED - file_path EXTRACTION FIX ★★★")


def _format_i18n(key: str, **kwargs) -> str:
    """Helper function to format i18n strings with parameters.

    The i18n library's parameter substitution doesn't work properly,
    so we manually replace {param} placeholders.
    """
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


# Header mode constants - use these internally instead of i18n values
HEADER_MODE_FIRST_ROW = "first_row"
HEADER_MODE_CUSTOM_ROW = "custom_row"
HEADER_MODE_NO_HEADER = "no_header"


class ETLExcelInputComponent(Component):
    """Excel file reader component for ETL operations."""

    display_name = i18n.t("components.input_output.excel_input.display_name")
    description = i18n.t("components.input_output.excel_input.description")
    icon = "FileSpreadsheet"
    name = "ETLExcelInput"
    include_universal_input = True  # Enable universal input for Excel Input

    inputs = [
        FileInput(
            name="file_path",
            display_name=i18n.t("components.input_output.excel_input.file_path.display_name"),
            info=i18n.t("components.input_output.excel_input.file_path.info"),
            file_types=["xlsx", "xls"],
            is_list=False,
            temp_file=False,  # Trigger FileTableInputComponent
            required=False,  # Optional since file_id_variable can replace it
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.input_output.excel_input.file_id_variable.display_name"),
            info=i18n.t("components.input_output.excel_input.file_id_variable.info"),
            placeholder="{excelFileId}",
            required=False,  # Optional since file_path can replace it
            resolve_variables=True,  # Enable automatic variable resolution
        ),
        IntInput(
            name="sheet_index",
            display_name=i18n.t("components.input_output.excel_input.sheet_index.display_name"),
            info=i18n.t("components.input_output.excel_input.sheet_index.info"),
            value=0,
            advanced=True,
        ),
        DropdownInput(
            name="header_mode",
            display_name=i18n.t("components.input_output.excel_input.header_mode.display_name"),
            info=i18n.t("components.input_output.excel_input.header_mode.info"),
            options=[HEADER_MODE_FIRST_ROW, HEADER_MODE_CUSTOM_ROW, HEADER_MODE_NO_HEADER],
            options_metadata=[
                {
                    "value": HEADER_MODE_FIRST_ROW,
                    "label": i18n.t("components.input_output.excel_input.header_mode.first_row"),
                },
                {
                    "value": HEADER_MODE_CUSTOM_ROW,
                    "label": i18n.t("components.input_output.excel_input.header_mode.custom_row"),
                },
                {
                    "value": HEADER_MODE_NO_HEADER,
                    "label": i18n.t("components.input_output.excel_input.header_mode.no_header"),
                },
            ],
            value=HEADER_MODE_FIRST_ROW,
            advanced=True,
        ),
        IntInput(
            name="header_row",
            display_name=i18n.t("components.input_output.excel_input.header_row.display_name"),
            info=i18n.t("components.input_output.excel_input.header_row.info"),
            value=1,
            advanced=True,
            # This field will be conditionally shown based on header_mode
        ),
        IntInput(
            name="data_start_row",
            display_name=i18n.t("components.input_output.excel_input.data_start_row.display_name"),
            info=i18n.t("components.input_output.excel_input.data_start_row.info"),
            value=2,
            advanced=True,
        ),
        IntInput(
            name="max_rows",
            display_name=i18n.t("components.input_output.excel_input.max_rows.display_name"),
            info=i18n.t("components.input_output.excel_input.max_rows.info"),
            value=0,
            advanced=True,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.excel_input.preview_table.display_name"),
            info=i18n.t("components.input_output.excel_input.preview_table.info"),
            table_schema=[],  # Will be dynamically generated
            value=[],  # Will be dynamically filled
            table_options={
                "block_add": True,  # Disable add
                "block_delete": True,  # Disable delete
                "block_edit": True,  # Read-only
                "pagination": True,  # Enable pagination
                "action_buttons": [
                    {
                        "name": "preview_excel",
                        "label": i18n.t("components.input_output.excel_input.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.excel_input.output_data.display_name"),
            method="load_data",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Handle dynamic configuration updates and preview button."""
        # Handle conditional field display
        if field_name == "header_mode":
            if field_value != HEADER_MODE_CUSTOM_ROW:
                # Hide header_row field
                if "header_row" in build_config:
                    build_config["header_row"]["show"] = False
            # Show header_row field
            elif "header_row" in build_config:
                build_config["header_row"]["show"] = True

        # Handle preview button click
        if field_name == "preview_table" and action == "preview_excel":
            temp_file_path = None
            try:
                # FileInput with temp_file=False sends:
                # - value: filename (e.g., "README.xlsx")
                # - file_path: file ID (e.g., "123")
                # We need to get file_path, not value
                file_path_field = build_config.get("file_path", {})
                file_id = file_path_field.get("file_path") or file_path_field.get("value")
                logger.info(f"[ExcelInput] Extracted file_id: {file_id} (type: {type(file_id)})")

                if not file_id:
                    self.status = i18n.t("components.input_output.excel_input.errors.no_file_selected")
                    return build_config

                # Check if file_id is a file ID (numeric) or actual path
                # If it's numeric, download from resource management system
                is_file_id = file_id.isdigit() if isinstance(file_id, str) else False

                if is_file_id:
                    # Download file by ID using Nacos Feign interface
                    temp_file_path = await download_file_by_id(file_id)
                    actual_file_path = temp_file_path
                    logger.info(f"[ExcelInput] Downloaded file ID {file_id} to {temp_file_path}")
                else:
                    # Use file path directly
                    actual_file_path = file_id

                # Get other configuration values
                sheet_index = build_config.get("sheet_index", {}).get("value", 0)
                header_mode = build_config.get("header_mode", {}).get("value")
                header_row = build_config.get("header_row", {}).get("value", 1)
                data_start_row = build_config.get("data_start_row", {}).get("value", 2)

                # Read Excel file for preview (max 100 rows)
                df = self._read_excel_file(
                    file_path=actual_file_path,
                    sheet_index=sheet_index,
                    header_mode=header_mode,
                    header_row=header_row,
                    data_start_row=data_start_row,
                    max_rows=100,
                )

                # Generate table schema dynamically
                table_schema = []
                for col in df.columns:
                    table_schema.append(
                        {
                            "name": str(col),
                            "display_name": str(col),
                            "type": "str",
                            "disable_edit": True,  # Read-only
                        }
                    )

                # Convert data to table format
                preview_data = df.fillna("").to_dict("records")

                # Update preview table
                build_config["preview_table"]["table_schema"] = table_schema
                build_config["preview_table"]["value"] = preview_data

                self.status = _format_i18n(
                    "components.input_output.excel_input.status.preview_success", count=len(preview_data)
                )
                logger.info(f"[ExcelInput] Preview successful: {len(preview_data)} rows")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                self.status = _format_i18n("components.input_output.excel_input.errors.preview_failed", error=error_msg)
                logger.exception(f"[ExcelInput] Failed to preview Excel file: {error_msg}")
            finally:
                # Cleanup temporary file if it was downloaded
                if temp_file_path:
                    cleanup_temp_file(temp_file_path)

        return build_config

    def _read_excel_file(
        self,
        file_path: str,
        sheet_index: int = 0,
        header_mode: str = None,
        header_row: int = 1,
        data_start_row: int = 2,
        max_rows: int = 0,
    ) -> pd.DataFrame:
        """Read Excel file with specified configuration.

        Note on row numbering:
        - header_row and data_start_row use 1-based indexing (as users see in Excel)
        - pandas uses 0-based indexing internally
        - header_row=1 means Excel row 1 (pandas index 0)
        - data_start_row=2 means Excel row 2 (pandas index 1)
        """
        try:
            # Use instance attributes if parameters not provided
            if header_mode is None:
                header_mode = getattr(self, "header_mode", HEADER_MODE_FIRST_ROW)

            # Determine header configuration
            if header_mode == HEADER_MODE_FIRST_ROW:
                header = 0
                skiprows = None
            elif header_mode == HEADER_MODE_CUSTOM_ROW:
                header = header_row - 1  # User input starts from 1
                skiprows = None
            else:  # HEADER_MODE_NO_HEADER
                header = None
                skiprows = None

            # Calculate skiprows based on data_start_row when we have a header
            # If header_row=1 and data_start_row=2, no rows to skip (data immediately after header)
            # If header_row=1 and data_start_row=3, skip 1 row after header (row 2)
            if header is not None and data_start_row > (header_row + 1):
                rows_to_skip_after_header = data_start_row - (header_row + 1)
                # skiprows must be a list of 0-based row indices
                # We need to skip rows between header and data_start
                skiprows = list(range(header + 1, header + 1 + rows_to_skip_after_header))

            # Read Excel file
            nrows = max_rows if max_rows > 0 else None
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_index,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                engine="openpyxl",
            )

            # If no header, use column identifiers
            if header is None:
                df.columns = [self._get_excel_column_name(i) for i in range(len(df.columns))]

            return df

        except Exception as e:
            raise ValueError(_format_i18n("components.input_output.excel_input.errors.read_excel_failed", error=str(e)))

    def _get_excel_column_name(self, col_index: int) -> str:
        """Convert column index to Excel column identifier (A, B, ..., AA, AB, ...)."""
        result = ""
        while col_index >= 0:
            result = chr((col_index % 26) + ord("A")) + result
            col_index = col_index // 26 - 1
        return result

    def _get_file_id(self) -> str:
        """Extract file_id from either file selection or external variable.

        Priority:
        1. file_id_variable (if provided and not empty)
        2. file_path (if provided)
        3. Raise error if neither provided

        Returns:
            str: File ID (resource ID from file browser or resolved variable)

        Raises:
            ValueError: If neither input is provided
        """
        # Priority 1: File Variable (with manual fallback if automatic resolution failed)
        if hasattr(self, "file_id_variable") and self.file_id_variable:
            variable_value = self.file_id_variable.strip()
            if variable_value:
                # Use base class helper method for variable resolution with fallback
                resolved_value = self._resolve_variable_with_fallback(
                    variable_value,
                    "components.input_output.excel_input.errors.variable_not_resolved"
                )
                logger.info(f"[ExcelInput] Using file_id from variable: {resolved_value}")
                return resolved_value

        # Priority 2: File selection from UI - use existing extraction logic
        file_id = None

        # Check if _parameters has the original file_path structure
        file_path_param = self._parameters.get("file_path")
        if isinstance(file_path_param, dict):
            file_id = file_path_param.get("file_path") or file_path_param.get("value")
            logger.info(f"[ExcelInput] Extracted file_id from dict _parameters: {file_id}")
        elif isinstance(file_path_param, str):
            if file_path_param.isdigit():
                file_id = file_path_param
                logger.info(f"[ExcelInput] Using numeric string from _parameters as file_id: {file_id}")
            else:
                import os

                basename = os.path.basename(file_path_param)
                if basename.isdigit():
                    file_id = basename
                    logger.info(f"[ExcelInput] Extracted file_id from cached path basename: {file_id}")
                else:
                    file_id = file_path_param
                    logger.info(f"[ExcelInput] Using path from _parameters: {file_id}")

        # Fallback to self.file_path
        if not file_id and hasattr(self, "file_path") and self.file_path:
            file_id = self.file_path
            logger.info(f"[ExcelInput] Fallback to self.file_path: {file_id}")

        if file_id:
            logger.info(f"[ExcelInput] Using file_id from file selection: {file_id}")
            return file_id

        # Neither provided - raise error
        error_msg = i18n.t("components.input_output.excel_input.errors.no_file_source")
        logger.error("[ExcelInput] No file source provided")
        raise ValueError(error_msg)

    def load_data(self) -> list[Data]:
        """Load Excel data and return as list of Data objects."""
        logger.info("[ExcelInput] load_data called")
        logger.info(f"[ExcelInput] _parameters keys: {list(self._parameters.keys())}")

        # Get file_id from either external variable or file selection
        file_id = self._get_file_id()

        temp_file_path = None
        try:
            # Check if file_id is a file ID (numeric) or actual path
            is_file_id = file_id.isdigit() if isinstance(file_id, str) else False
            logger.info(f"[ExcelInput] file_id={file_id}, is_file_id: {is_file_id}")

            if is_file_id:
                # Download file by ID using Nacos Feign interface
                import asyncio

                # Create async function to download
                async def _download():
                    return await download_file_by_id(file_id)

                # Always create a new event loop to avoid thread issues
                try:
                    # Try to get existing loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, we need a new loop
                        raise RuntimeError("Need new loop")
                except RuntimeError:
                    # No loop or loop is running, use asyncio.run (creates new loop)
                    temp_file_path = asyncio.run(_download())
                else:
                    # Loop exists and not running, use it
                    temp_file_path = loop.run_until_complete(_download())

                actual_file_path = temp_file_path
                logger.info(f"[ExcelInput] Downloaded file ID {file_id} to {temp_file_path} for loading")
            else:
                # Use file path directly
                actual_file_path = file_id

            # Read complete data
            max_rows = self.max_rows if hasattr(self, "max_rows") else 0
            df = self._read_excel_file(
                file_path=actual_file_path,
                sheet_index=getattr(self, "sheet_index", 0),
                header_mode=getattr(self, "header_mode", None),
                header_row=getattr(self, "header_row", 1),
                data_start_row=getattr(self, "data_start_row", 2),
                max_rows=max_rows,
            )

            # Convert to list of Data objects
            result = []
            for _, row in df.iterrows():
                # Convert NaN to None for cleaner data
                row_dict = row.where(pd.notnull(row), None).to_dict()
                result.append(Data(data=row_dict))

            self.status = _format_i18n("components.input_output.excel_input.status.loaded_rows", count=len(result))
            logger.info(f"[ExcelInput] Loaded {len(result)} rows from Excel file")

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[ExcelInput] Failed to load data: {error_msg}")
            logger.exception("[ExcelInput] Full exception traceback:")

            # Format error message with i18n
            translated_msg = _format_i18n(
                "components.input_output.excel_input.errors.load_data_failed", error=error_msg
            )
            logger.error(f"[ExcelInput] Translated error: {translated_msg}")

            raise ValueError(translated_msg)
        finally:
            # Cleanup temporary file if it was downloaded
            if temp_file_path:
                cleanup_temp_file(temp_file_path)
                logger.info(f"[ExcelInput] Cleaned up temporary file after loading: {temp_file_path}")
