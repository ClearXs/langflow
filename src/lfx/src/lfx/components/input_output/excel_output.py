import tempfile

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, FileInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.services.feign.clients.data_construction import cleanup_temp_file, upload_file_to_folder


def _format_i18n(key: str, **kwargs) -> str:
    """Helper function to format i18n strings with parameters."""
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


class ETLExcelOutputComponent(Component):
    display_name = i18n.t("components.input_output.excel_output.display_name")
    description = i18n.t("components.input_output.excel_output.description")
    icon = "FileSpreadsheet"
    name = "ETLExcelOutput"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.excel_output.data_input.display_name"),
            info=i18n.t("components.input_output.excel_output.data_input.info"),
            is_list=True,
            required=True,
        ),
        FileInput(
            name="output_folder",
            display_name=i18n.t("components.input_output.excel_output.output_folder.display_name"),
            info=i18n.t("components.input_output.excel_output.output_folder.info"),
            file_types=["folder"],  # Special marker for folder-only selection
            temp_file=False,  # Use FileTableInputComponent
            required=True,
        ),
        MessageTextInput(
            name="filename",
            display_name=i18n.t("components.input_output.excel_output.filename.display_name"),
            info=i18n.t("components.input_output.excel_output.filename.info"),
            value="output.xlsx",
            required=True,
        ),
        MessageTextInput(
            name="sheet_name",
            display_name=i18n.t("components.input_output.excel_output.sheet_name.display_name"),
            info=i18n.t("components.input_output.excel_output.sheet_name.info"),
            value="Sheet1",
            advanced=True,
        ),
        BoolInput(
            name="include_index",
            display_name=i18n.t("components.input_output.excel_output.include_index.display_name"),
            info=i18n.t("components.input_output.excel_output.include_index.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.input_output.excel_output.outputs.result.display_name"),
            method="export_to_excel",
        )
    ]

    async def export_to_excel(self) -> Data:
        temp_file_path = None
        try:
            # 1. Validate data
            self.status = _format_i18n("components.input_output.excel_output.status.validating")

            if not self.data_input:
                error_msg = i18n.t("components.input_output.excel_output.errors.no_data")
                self.status = error_msg
                raise ValueError(error_msg)

            # 2. Get folder ID from FileInput
            # FileInput with temp_file=False stores folder_id in multiple possible locations
            folder_id = None

            # Try to get from _parameters (priority 1)
            if hasattr(self, "_parameters") and "output_folder" in self._parameters:
                param_value = self._parameters["output_folder"]
                if isinstance(param_value, dict):
                    # If it's a dict, try to get file_path key
                    folder_id = param_value.get("file_path")
                elif isinstance(param_value, str):
                    # If it's already a string, use it directly
                    folder_id = param_value

            # Fallback to direct attribute (priority 2)
            if not folder_id and hasattr(self, "output_folder"):
                folder_id = self.output_folder

            if not folder_id:
                error_msg = i18n.t("components.input_output.excel_output.errors.no_folder_selected")
                self.status = error_msg
                raise ValueError(error_msg)

            # Validate folder_id is numeric (not a file path)
            # Extract numeric ID from path if necessary (e.g., "/path/to/123" -> "123")
            folder_id_str = str(folder_id)
            if "/" in folder_id_str or "\\" in folder_id_str:
                # This looks like a file path, try to extract the last part as ID
                path_parts = folder_id_str.replace("\\", "/").split("/")
                potential_id = path_parts[-1]
                if potential_id.isdigit():
                    folder_id = potential_id
                    logger.warning(f"[ExcelOutput] Extracted folder ID {folder_id} from path {folder_id_str}")
                else:
                    error_msg = i18n.t(
                        "components.input_output.excel_output.errors.invalid_folder_id",
                        folder_id=folder_id_str,
                    )
                    self.status = error_msg
                    raise ValueError(error_msg)

            # Validate folder_id can be converted to int
            try:
                folder_id_int = int(folder_id)
            except (ValueError, TypeError) as e:
                error_msg = i18n.t(
                    "components.input_output.excel_output.errors.invalid_folder_id",
                    folder_id=folder_id,
                )
                self.status = error_msg
                raise ValueError(error_msg) from e

            logger.info(f"[ExcelOutput] Exporting to folder_id={folder_id}, filename={self.filename}")

            # 3. Convert data to DataFrame
            self.status = _format_i18n("components.input_output.excel_output.status.converting")
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            if df.empty:
                error_msg = i18n.t("components.input_output.excel_output.errors.empty_dataframe")
                self.status = error_msg
                raise ValueError(error_msg)

            # 4. Save to temporary file
            self.status = _format_i18n("components.input_output.excel_output.status.saving_temp")
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False, prefix="lfx_excel_output_") as temp_file:
                temp_file_path = temp_file.name

            # Write Excel file (openpyxl doesn't support writing to file object directly)
            df.to_excel(temp_file_path, sheet_name=self.sheet_name, index=self.include_index, engine="openpyxl")

            logger.info(f"[ExcelOutput] Saved to temp file: {temp_file_path}")

            # 5. Upload to resource management system
            self.status = _format_i18n("components.input_output.excel_output.status.uploading")
            upload_result = await upload_file_to_folder(
                folder_id=folder_id_int, file_path=temp_file_path, filename=self.filename
            )

            # 6. Build result
            result_info = {
                "success": True,
                "file_id": upload_result.get("id"),
                "file_name": self.filename,
                "folder_id": folder_id,
                "rows_exported": len(df),
                "columns": len(df.columns),
                "sheet_name": self.sheet_name,
            }

            success_msg = _format_i18n(
                "components.input_output.excel_output.status.success", rows=len(df), filename=self.filename
            )
            self.status = success_msg
            logger.info(f"[ExcelOutput] {success_msg}")

            return Data(data=result_info)

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # Format error message
            formatted_error = _format_i18n(
                "components.input_output.excel_output.errors.export_failed", error_type=error_type, error=error_msg
            )

            self.status = formatted_error
            logger.exception(f"[ExcelOutput] Export failed: {formatted_error}")
            raise ValueError(formatted_error) from e

        finally:
            # 7. Cleanup temporary file
            if temp_file_path:
                cleanup_temp_file(temp_file_path)
