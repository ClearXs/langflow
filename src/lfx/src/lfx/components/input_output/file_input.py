"""File input component for selecting files from file management system.

This component allows users to select structured data files (CSV, Excel, JSON)
through the file management UI and outputs file information for downstream processing.
"""

from __future__ import annotations

from typing import Any

import i18n

from lfx.base.data.base_file import BaseFileComponent
from lfx.io import FileInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message


class ETLFileInputComponent(BaseFileComponent):
    """File input component for selecting structured data files from file management system.

    This component provides a file selection interface that allows users to:
    - Select single or multiple structured data files from the file management system
    - Supported formats: CSV, Excel (xlsx, xls), JSON
    - Output file information for downstream processing nodes
    """

    display_name = i18n.t("components.input_output.file_input.display_name")
    description = i18n.t("components.input_output.file_input.description")
    documentation: str = "https://docs.langflow.org/components-input-output#file-input"
    icon = "file-input"
    name = "ETLFileInput"

    # Define supported file extensions - only structured data files
    VALID_EXTENSIONS = [
        "csv",
        "xlsx",
        "xls",
        "json",
    ]

    # Configure base inputs from BaseFileComponent
    _base_inputs = BaseFileComponent.get_base_inputs()

    # Customize the FileInput to use file table UI (temp_file=False)
    for input_item in _base_inputs:
        if isinstance(input_item, FileInput) and input_item.name == "path":
            # Configure path field to use FileTableInputComponent
            input_item.temp_file = False  # Enable FileTableInputComponent in frontend
            input_item.display_name = i18n.t("components.input_output.file_input.path.display_name")
            input_item.info = i18n.t("components.input_output.file_input.path.info")
            # Ensure path field is visible
            input_item.advanced = False
            if hasattr(input_item, "show"):
                input_item.show = True
        else:
            # Hide all other inputs
            if hasattr(input_item, "advanced"):
                input_item.advanced = True
            if hasattr(input_item, "show"):
                input_item.show = False

    # Use all base inputs (they are all needed for BaseFileComponent to work properly)
    inputs = _base_inputs

    outputs = [
        Output(
            display_name=i18n.t("components.input_output.file_input.outputs.file_data.display_name"),
            name="file_data",
            method="get_file_data",
        ),
        Output(
            display_name=i18n.t("components.input_output.file_input.outputs.file_path.display_name"),
            name="file_paths",
            method="get_file_paths",
        ),
        Output(
            display_name=i18n.t("components.input_output.file_input.outputs.message.display_name"),
            name="message",
            method="get_file_message",
        ),
    ]

    def process_files(
        self,
        file_list: list[BaseFileComponent.BaseFile],
    ) -> list[BaseFileComponent.BaseFile]:
        """Process selected files and extract metadata.

        This method processes each file in the list and builds basic metadata information.
        The metadata is stored in the file's Data object for downstream processing.

        Args:
            file_list: List of BaseFile objects representing selected files

        Returns:
            List of BaseFile objects with updated Data containing file metadata

        Raises:
            ValueError: If no files are selected
        """
        if not file_list:
            msg = i18n.t("components.input_output.file_input.errors.no_files_selected")
            # Fallback if i18n returns the key unchanged
            if not msg or "components.input_output" in msg:
                msg = "No files selected. Please select at least one file."
            if not self.silent_errors:
                raise ValueError(msg)
            return []

        processed_files = []

        for file in file_list:
            file_path = file.path

            # Build basic metadata
            metadata: dict[str, Any] = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_extension": file_path.suffix,
                "file_stem": file_path.stem,  # filename without extension
            }

            # Add file size if file exists
            if file_path.exists():
                try:
                    stat = file_path.stat()
                    metadata.update(
                        {
                            "file_size": stat.st_size,
                            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "file_size_kb": round(stat.st_size / 1024, 2),
                        }
                    )
                except Exception as e:
                    self.log(f"Failed to get file size for {file_path}: {e}")
                    if not self.silent_errors:
                        raise

            # Create Data object with metadata
            file.data = Data(data=metadata)
            processed_files.append(file)

            # Log success
            if "file_size_mb" in metadata:
                self.log(
                    i18n.t(
                        "components.input_output.file_input.success.file_selected_with_metadata",
                        name=metadata["file_name"],
                        size=metadata["file_size_mb"],
                    )
                )
            else:
                self.log(
                    i18n.t(
                        "components.input_output.file_input.success.file_selected",
                        name=metadata["file_name"],
                    )
                )

        # Update status with file count
        status_msg = i18n.t(
            "components.input_output.file_input.status.files_processed",
            count=len(processed_files),
        )
        # Fallback if i18n returns the key unchanged
        if not status_msg or "components.input_output" in status_msg:
            status_msg = f"Processed {len(processed_files)} file(s)"
        self.status = status_msg

        return processed_files

    def get_file_data(self) -> list[Data]:
        """Return file information as Data objects.

        Each Data object contains file metadata including path, name, extension, and file size.

        Returns:
            List of Data objects containing file metadata
        """
        return self.load_files_base()

    def get_file_paths(self) -> list[str]:
        """Return list of file paths as strings.

        This output is useful for passing file paths to other components
        that need file locations as simple string values.

        Returns:
            List of file path strings
        """
        files = self.load_files_base()
        if not files:
            return []
        return [str(data.data.get("file_path", "")) for data in files]

    def get_file_message(self) -> Message:
        """Return file information as a Message object.

        Creates a formatted message containing information about all selected files,
        including names and sizes.

        Returns:
            Message object with formatted file information
        """
        files = self.load_files_base()

        if not files:
            no_files_msg = i18n.t("components.input_output.file_input.message.no_files")
            # Fallback if i18n returns the key unchanged
            if not no_files_msg or "components.input_output" in no_files_msg:
                no_files_msg = "No files selected"
            return Message(text=no_files_msg)

        file_info = []
        for data in files:
            name = data.data.get("file_name", "")
            size_mb = data.data.get("file_size_mb")

            if size_mb is not None:
                file_info.append(f"- {name} ({size_mb} MB)")
            else:
                file_info.append(f"- {name}")

        # Build message with count
        files_selected_msg = i18n.t(
            "components.input_output.file_input.message.files_selected",
            count=len(files),
        )
        # Fallback if i18n returns the key unchanged
        if not files_selected_msg or "components.input_output" in files_selected_msg:
            files_selected_msg = f"Selected {len(files)} file(s):"

        text = files_selected_msg + "\n" + "\n".join(file_info)

        return Message(text=text)
