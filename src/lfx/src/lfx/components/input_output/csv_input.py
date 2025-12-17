from typing import Any

import chardet
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, FileInput, IntInput, Output, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.services.feign.clients.data_construction import cleanup_temp_file, download_file_by_id

# ★★★ MODULE LOADED: data-construction/csv_input.py UPDATED 2025-10-21 ★★★
print("★★★ [data-construction] CSV_INPUT MODULE LOADED - file_path EXTRACTION FIX ★★★")
logger.info("★★★ [data-construction] CSV_INPUT MODULE LOADED - file_path EXTRACTION FIX ★★★")


def _format_i18n(key: str, **kwargs) -> str:
    """Helper function to format i18n strings with parameters.

    The i18n library's parameter substitution doesn't work properly,
    so we manually replace {param} placeholders.
    """
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


# Header mode constants
HEADER_MODE_FIRST_ROW = "first_row"
HEADER_MODE_CUSTOM_ROW = "custom_row"
HEADER_MODE_NO_HEADER = "no_header"

# Delimiter constants
DELIMITER_COMMA = ","
DELIMITER_SEMICOLON = ";"
DELIMITER_TAB = "\\t"
DELIMITER_PIPE = "|"
DELIMITER_CUSTOM = "custom"

# Encoding constants
ENCODING_AUTO = "auto"


class ETLCSVInputComponent(Component):
    """CSV file reader component for ETL operations."""

    display_name = i18n.t("components.input_output.csv_input.display_name")
    description = i18n.t("components.input_output.csv_input.description")
    include_universal_input = True  # Enable universal input for CSV Input
    icon = "FileText"
    name = "ETLCSVInput"

    inputs = [
        FileInput(
            name="file_path",
            display_name=i18n.t("components.input_output.csv_input.file_path.display_name"),
            info=i18n.t("components.input_output.csv_input.file_path.info"),
            file_types=["csv", "txt", "tsv"],
            is_list=False,
            temp_file=False,  # Trigger FileTableInputComponent
            required=False,  # Optional since file_id_variable can replace it
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.input_output.csv_input.file_id_variable.display_name"),
            info=i18n.t("components.input_output.csv_input.file_id_variable.info"),
            placeholder="{csvFileId}",
            required=False,  # Optional since file_path can replace it
            resolve_variables=True,  # Enable automatic variable resolution
        ),
        DropdownInput(
            name="delimiter",
            display_name=i18n.t("components.input_output.csv_input.delimiter.display_name"),
            info=i18n.t("components.input_output.csv_input.delimiter.info"),
            options=[DELIMITER_COMMA, DELIMITER_SEMICOLON, DELIMITER_TAB, DELIMITER_PIPE, DELIMITER_CUSTOM],
            options_metadata=[
                {"value": DELIMITER_COMMA, "label": ","},
                {"value": DELIMITER_SEMICOLON, "label": ";"},
                {"value": DELIMITER_TAB, "label": "\\t (Tab)"},
                {"value": DELIMITER_PIPE, "label": "|"},
                {"value": DELIMITER_CUSTOM, "label": i18n.t("components.input_output.csv_input.delimiter.custom")},
            ],
            value=DELIMITER_COMMA,
            advanced=True,
        ),
        StrInput(
            name="custom_delimiter",
            display_name=i18n.t("components.input_output.csv_input.custom_delimiter.display_name"),
            info=i18n.t("components.input_output.csv_input.custom_delimiter.info"),
            value="",
            advanced=True,
            # This field will be conditionally shown based on delimiter
        ),
        DropdownInput(
            name="encoding",
            display_name=i18n.t("components.input_output.csv_input.encoding.display_name"),
            info=i18n.t("components.input_output.csv_input.encoding.info"),
            options=["utf-8", "gbk", "gb2312", "big5", ENCODING_AUTO],
            options_metadata=[
                {"value": "utf-8", "label": "UTF-8"},
                {"value": "gbk", "label": "GBK"},
                {"value": "gb2312", "label": "GB2312"},
                {"value": "big5", "label": "Big5"},
                {"value": ENCODING_AUTO, "label": i18n.t("components.input_output.csv_input.encoding.auto")},
            ],
            value="utf-8",
            advanced=True,
        ),
        DropdownInput(
            name="header_mode",
            display_name=i18n.t("components.input_output.csv_input.header_mode.display_name"),
            info=i18n.t("components.input_output.csv_input.header_mode.info"),
            options=[HEADER_MODE_FIRST_ROW, HEADER_MODE_CUSTOM_ROW, HEADER_MODE_NO_HEADER],
            options_metadata=[
                {
                    "value": HEADER_MODE_FIRST_ROW,
                    "label": i18n.t("components.input_output.csv_input.header_mode.first_row"),
                },
                {
                    "value": HEADER_MODE_CUSTOM_ROW,
                    "label": i18n.t("components.input_output.csv_input.header_mode.custom_row"),
                },
                {
                    "value": HEADER_MODE_NO_HEADER,
                    "label": i18n.t("components.input_output.csv_input.header_mode.no_header"),
                },
            ],
            value=HEADER_MODE_FIRST_ROW,
            advanced=True,
        ),
        IntInput(
            name="header_row",
            display_name=i18n.t("components.input_output.csv_input.header_row.display_name"),
            info=i18n.t("components.input_output.csv_input.header_row.info"),
            value=1,
            advanced=True,
            # This field will be conditionally shown based on header_mode
        ),
        IntInput(
            name="data_start_row",
            display_name=i18n.t("components.input_output.csv_input.data_start_row.display_name"),
            info=i18n.t("components.input_output.csv_input.data_start_row.info"),
            value=2,
            advanced=True,
        ),
        IntInput(
            name="max_rows",
            display_name=i18n.t("components.input_output.csv_input.max_rows.display_name"),
            info=i18n.t("components.input_output.csv_input.max_rows.info"),
            value=0,
            advanced=True,
        ),
        BoolInput(
            name="skip_blank_lines",
            display_name=i18n.t("components.input_output.csv_input.skip_blank_lines.display_name"),
            info=i18n.t("components.input_output.csv_input.skip_blank_lines.info"),
            value=True,
            advanced=True,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.csv_input.preview_table.display_name"),
            info=i18n.t("components.input_output.csv_input.preview_table.info"),
            table_schema=[],  # Will be dynamically generated
            value=[],  # Will be dynamically filled
            table_options={
                "block_add": True,  # Disable add
                "block_delete": True,  # Disable delete
                "block_edit": True,  # Read-only
                "pagination": True,  # Enable pagination
                "action_buttons": [
                    {
                        "name": "preview_csv",
                        "label": i18n.t("components.input_output.csv_input.preview_table.preview_button"),
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
            display_name=i18n.t("components.input_output.csv_input.output_data.display_name"),
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
        # Handle conditional field display for delimiter
        if field_name == "delimiter":
            if field_value != DELIMITER_CUSTOM:
                # Hide custom_delimiter field
                if "custom_delimiter" in build_config:
                    build_config["custom_delimiter"]["show"] = False
            # Show custom_delimiter field
            elif "custom_delimiter" in build_config:
                build_config["custom_delimiter"]["show"] = True

        # Handle conditional field display for header mode
        if field_name == "header_mode":
            if field_value != HEADER_MODE_CUSTOM_ROW:
                # Hide header_row field
                if "header_row" in build_config:
                    build_config["header_row"]["show"] = False
            # Show header_row field
            elif "header_row" in build_config:
                build_config["header_row"]["show"] = True

        # Handle preview button click
        if field_name == "preview_table" and action == "preview_csv":
            logger.info(f"[CSVInput] Preview button clicked, field_name={field_name}, action={action}")
            logger.info(f"[CSVInput] Full build_config keys: {list(build_config.keys())}")
            logger.info(f"[CSVInput] file_path field: {build_config.get('file_path')}")

            temp_file_path = None
            try:
                # FileInput with temp_file=False sends:
                # - value: filename (e.g., "README.txt")
                # - file_path: file ID (e.g., "123")
                # We need to get file_path, not value
                file_path_field = build_config.get("file_path", {})
                file_id = file_path_field.get("file_path") or file_path_field.get("value")
                logger.info(f"[CSVInput] file_path_field: {file_path_field}")
                logger.info(f"[CSVInput] Extracted file_id: {file_id} (type: {type(file_id)})")

                if not file_id:
                    self.status = i18n.t("components.input_output.csv_input.errors.no_file_selected")
                    logger.warning("[CSVInput] No file selected")
                    return build_config

                # Check if file_id is a file ID (numeric) or actual path
                # If it's numeric, download from resource management system
                is_file_id = file_id.isdigit() if isinstance(file_id, str) else False

                if is_file_id:
                    # Download file by ID using Nacos Feign interface
                    temp_file_path = await download_file_by_id(file_id)
                    actual_file_path = temp_file_path
                    logger.info(f"[CSVInput] Downloaded file ID {file_id} to {temp_file_path}")
                else:
                    # Use file path directly
                    actual_file_path = file_id

                # Get other configuration values
                delimiter = build_config.get("delimiter", {}).get("value", ",")
                custom_delimiter = build_config.get("custom_delimiter", {}).get("value", "")
                encoding = build_config.get("encoding", {}).get("value", "utf-8")
                header_mode = build_config.get("header_mode", {}).get("value")
                header_row = build_config.get("header_row", {}).get("value", 1)
                data_start_row = build_config.get("data_start_row", {}).get("value", 2)
                skip_blank_lines = build_config.get("skip_blank_lines", {}).get("value", True)

                # Read CSV file for preview (max 100 rows)
                df = self._read_csv_file(
                    file_path=actual_file_path,
                    delimiter=delimiter,
                    custom_delimiter=custom_delimiter,
                    encoding=encoding,
                    header_mode=header_mode,
                    header_row=header_row,
                    data_start_row=data_start_row,
                    skip_blank_lines=skip_blank_lines,
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
                    "components.input_output.csv_input.status.preview_success", count=len(preview_data)
                )
                logger.info(f"[CSVInput] Preview successful: {len(preview_data)} rows")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                self.status = _format_i18n("components.input_output.csv_input.errors.preview_failed", error=error_msg)
                logger.exception(f"[CSVInput] Failed to preview CSV file: {error_msg}")
                # Re-raise to see full traceback
                import traceback

                logger.error(f"[CSVInput] Full traceback:\n{traceback.format_exc()}")
            finally:
                # Cleanup temporary file if it was downloaded
                if temp_file_path:
                    cleanup_temp_file(temp_file_path)

        return build_config

    def _detect_encoding(self, file_path: str, encoding: str = None) -> str:
        """Auto-detect file encoding if needed."""
        if encoding and encoding != ENCODING_AUTO:
            return encoding

        try:
            with open(file_path, "rb") as f:
                # Read first 10KB for detection
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                detected_encoding = result["encoding"]

                if detected_encoding:
                    logger.info(
                        f"[CSVInput] Detected encoding: {detected_encoding} (confidence: {result['confidence']})"
                    )
                    return detected_encoding
                logger.warning("[CSVInput] Could not detect encoding, using utf-8")
                return "utf-8"
        except Exception as e:
            logger.warning(f"[CSVInput] Error detecting encoding: {e}, using utf-8")
            return "utf-8"

    def _read_csv_file(
        self,
        file_path: str,
        delimiter: str = ",",
        custom_delimiter: str = "",
        encoding: str = "utf-8",
        header_mode: str = None,
        header_row: int = 1,
        data_start_row: int = 2,
        skip_blank_lines: bool = True,
        max_rows: int = 0,
    ) -> pd.DataFrame:
        """Read CSV file with specified configuration."""
        try:
            # Determine the actual delimiter
            if delimiter == DELIMITER_CUSTOM:
                sep = custom_delimiter if custom_delimiter else ","
            elif delimiter == DELIMITER_TAB:
                sep = "\t"
            else:
                sep = delimiter

            # Detect encoding if needed
            actual_encoding = self._detect_encoding(file_path, encoding)

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

            # Read CSV file
            nrows = max_rows if max_rows > 0 else None
            df = pd.read_csv(
                file_path,
                sep=sep,
                encoding=actual_encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                skip_blank_lines=skip_blank_lines,
                on_bad_lines="warn",
            )

            # If no header, use column identifiers
            if header is None:
                df.columns = [f"Column_{i + 1}" for i in range(len(df.columns))]

            # Handle data start row
            if data_start_row > 1:
                if header is not None:
                    # If we have headers, skip rows after header
                    skip_rows = data_start_row - 2
                else:
                    # If no headers, skip from beginning
                    skip_rows = data_start_row - 1

                if skip_rows > 0 and skip_rows < len(df):
                    df = df.iloc[skip_rows:]
                elif skip_rows >= len(df):
                    # Return empty dataframe with columns
                    df = pd.DataFrame(columns=df.columns)

            return df

        except UnicodeDecodeError as e:
            raise ValueError(
                _format_i18n(
                    "components.input_output.csv_input.errors.encoding_error", encoding=actual_encoding, error=str(e)
                )
            )
        except Exception as e:
            raise ValueError(_format_i18n("components.input_output.csv_input.errors.read_csv_failed", error=str(e)))

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
                    "components.input_output.csv_input.errors.variable_not_resolved"
                )
                logger.info(f"[CSVInput] Using file_id from variable: {resolved_value}")
                return resolved_value

        # Priority 2: File selection from UI - use existing extraction logic
        # Try to get file_id from multiple sources
        file_id = None

        # Check if _parameters has the original file_path structure
        file_path_param = self._parameters.get("file_path")
        if isinstance(file_path_param, dict):
            file_id = file_path_param.get("file_path") or file_path_param.get("value")
            logger.info(f"[CSVInput] Extracted file_id from dict _parameters: {file_id}")
        elif isinstance(file_path_param, str):
            # Check if it's a numeric file ID
            if file_path_param.isdigit():
                file_id = file_path_param
                logger.info(f"[CSVInput] Using numeric string from _parameters as file_id: {file_id}")
            else:
                # It's a path (could be cached path or real path)
                import os

                basename = os.path.basename(file_path_param)
                if basename.isdigit():
                    file_id = basename
                    logger.info(f"[CSVInput] Extracted file_id from cached path basename: {file_id}")
                else:
                    # It's a real file path, use it directly
                    file_id = file_path_param
                    logger.info(f"[CSVInput] Using path from _parameters: {file_id}")

        # Fallback to self.file_path
        if not file_id and hasattr(self, "file_path") and self.file_path:
            file_id = self.file_path
            logger.info(f"[CSVInput] Fallback to self.file_path: {file_id}")

        if file_id:
            logger.info(f"[CSVInput] Using file_id from file selection: {file_id}")
            return file_id

        # Neither provided - raise error
        error_msg = i18n.t("components.input_output.csv_input.errors.no_file_source")
        logger.error("[CSVInput] No file source provided")
        raise ValueError(error_msg)

    def load_data(self) -> list[Data]:
        """Load CSV data and return as list of Data objects."""
        logger.info("[CSVInput] load_data called")
        logger.info(f"[CSVInput] _parameters keys: {list(self._parameters.keys())}")

        # Get file_id from either external variable or file selection
        file_id = self._get_file_id()

        temp_file_path = None
        try:
            # Check if file_id is a file ID (numeric) or actual path
            is_file_id = file_id.isdigit() if isinstance(file_id, str) else False
            logger.info(f"[CSVInput] file_id={file_id}, is_file_id: {is_file_id}")

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
                        # If loop is running, we need to run in a new thread with new loop
                        # But since you said we don't need thread pool, just use asyncio.run
                        # which creates a new loop
                        raise RuntimeError("Need new loop")
                except RuntimeError:
                    # No loop or loop is running, use asyncio.run (creates new loop)
                    temp_file_path = asyncio.run(_download())
                else:
                    # Loop exists and not running, use it
                    temp_file_path = loop.run_until_complete(_download())

                actual_file_path = temp_file_path
                logger.info(f"[CSVInput] Downloaded file ID {file_id} to {temp_file_path} for loading")
            else:
                # Use file path directly
                actual_file_path = file_id

            # Get delimiter configuration
            delimiter = getattr(self, "delimiter", ",")
            custom_delimiter = getattr(self, "custom_delimiter", "")

            # Read complete data
            max_rows = getattr(self, "max_rows", 0)
            df = self._read_csv_file(
                file_path=actual_file_path,
                delimiter=delimiter,
                custom_delimiter=custom_delimiter,
                encoding=getattr(self, "encoding", "utf-8"),
                header_mode=getattr(self, "header_mode", None),
                header_row=getattr(self, "header_row", 1),
                data_start_row=getattr(self, "data_start_row", 2),
                skip_blank_lines=getattr(self, "skip_blank_lines", True),
                max_rows=max_rows,
            )

            # Convert to list of Data objects
            result = []
            for _, row in df.iterrows():
                # Convert NaN to None for cleaner data
                row_dict = row.where(pd.notnull(row), None).to_dict()
                result.append(Data(data=row_dict))

            self.status = _format_i18n("components.input_output.csv_input.status.loaded_rows", count=len(result))
            logger.info(f"[CSVInput] Loaded {len(result)} rows from CSV file")

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[CSVInput] Failed to load data: {error_msg}")
            logger.exception("[CSVInput] Full exception traceback:")

            # Format error message with i18n
            translated_msg = _format_i18n("components.input_output.csv_input.errors.load_data_failed", error=error_msg)
            logger.error(f"[CSVInput] Translated error: {translated_msg}")

            raise ValueError(translated_msg)
        finally:
            # Cleanup temporary file if it was downloaded
            if temp_file_path:
                cleanup_temp_file(temp_file_path)
                logger.info(f"[CSVInput] Cleaned up temporary file after loading: {temp_file_path}")
