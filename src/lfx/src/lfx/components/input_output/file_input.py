import csv
import json
from pathlib import Path
from typing import Any
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import (
    MessageTextInput,
    DropdownInput,
    BoolInput,
    IntInput,
    Output
)
from lfx.schema import Data


class ETLFileInputComponent(Component):
    display_name = i18n.t('components.input_output.file_input.display_name')
    description = i18n.t('components.input_output.file_input.description')
    icon = "file-text"
    name = "ETLFileInput"

    inputs = [
        MessageTextInput(
            name="file_path",
            display_name=i18n.t('components.input_output.file_input.file_path.display_name'),
            info=i18n.t('components.input_output.file_input.file_path.info'),
            required=True,
            placeholder="/path/to/file.csv"
        ),
        DropdownInput(
            name="file_type",
            display_name=i18n.t('components.input_output.file_input.file_type.display_name'),
            info=i18n.t('components.input_output.file_input.file_type.info'),
            options=["CSV", "Excel", "JSON", "Auto-Detect"],
            value="Auto-Detect"
        ),
        MessageTextInput(
            name="encoding",
            display_name=i18n.t('components.input_output.file_input.encoding.display_name'),
            info=i18n.t('components.input_output.file_input.encoding.info'),
            value="utf-8",
            advanced=True
        ),
        MessageTextInput(
            name="delimiter",
            display_name=i18n.t('components.input_output.file_input.delimiter.display_name'),
            info=i18n.t('components.input_output.file_input.delimiter.info'),
            value=",",
            advanced=True
        ),
        BoolInput(
            name="has_header",
            display_name=i18n.t('components.input_output.file_input.has_header.display_name'),
            info=i18n.t('components.input_output.file_input.has_header.info'),
            value=True,
            advanced=True
        ),
        IntInput(
            name="skip_rows",
            display_name=i18n.t('components.input_output.file_input.skip_rows.display_name'),
            info=i18n.t('components.input_output.file_input.skip_rows.info'),
            value=0,
            advanced=True
        ),
        IntInput(
            name="max_rows",
            display_name=i18n.t('components.input_output.file_input.max_rows.display_name'),
            info=i18n.t('components.input_output.file_input.max_rows.info'),
            value=0,
            advanced=True
        ),
        MessageTextInput(
            name="sheet_name",
            display_name=i18n.t('components.input_output.file_input.sheet_name.display_name'),
            info=i18n.t('components.input_output.file_input.sheet_name.info'),
            value="Sheet1",
            advanced=True
        )
    ]

    outputs = [
        Output(name="data", display_name="Data", method="read_file"),
        Output(name="file_info", display_name="File Info", method="get_file_info")
    ]

    def read_file(self) -> list[Data]:
        """Read data from CSV, Excel, or JSON files with encoding support."""
        try:
            self.status = i18n.t('components.input_output.file_input.status.reading')

            file_path = Path(self.file_path)

            if not file_path.exists():
                raise FileNotFoundError(i18n.t('components.input_output.file_input.errors.file_not_found', path=self.file_path))

            # Detect file type
            file_type = self._detect_file_type(file_path)

            # Read file based on type
            if file_type == "CSV":
                df = self._read_csv(file_path)
            elif file_type == "Excel":
                df = self._read_excel(file_path)
            elif file_type == "JSON":
                df = self._read_json(file_path)
            else:
                raise ValueError(i18n.t('components.input_output.file_input.errors.unsupported_type', type=file_type))

            # Convert to Data objects
            result_data = []
            max_rows = self.max_rows if self.max_rows > 0 else len(df)

            for idx, row in df.head(max_rows).iterrows():
                row_dict = row.to_dict()
                row_dict["_row_number"] = idx
                result_data.append(Data(data=row_dict))

            self.status = i18n.t('components.input_output.file_input.status.success', rows=len(result_data))
            return result_data

        except Exception as e:
            error_msg = i18n.t('components.input_output.file_input.errors.read_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension or user selection."""
        if self.file_type != "Auto-Detect":
            return self.file_type

        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return "CSV"
        elif suffix in [".xlsx", ".xls"]:
            return "Excel"
        elif suffix == ".json":
            return "JSON"
        else:
            return "CSV"

    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        """Read CSV file with encoding and delimiter support."""
        return pd.read_csv(
            file_path,
            encoding=self.encoding,
            delimiter=self.delimiter,
            header=0 if self.has_header else None,
            skiprows=self.skip_rows
        )

    def _read_excel(self, file_path: Path) -> pd.DataFrame:
        """Read Excel file with sheet name support."""
        return pd.read_excel(
            file_path,
            sheet_name=self.sheet_name,
            header=0 if self.has_header else None,
            skiprows=self.skip_rows
        )

    def _read_json(self, file_path: Path) -> pd.DataFrame:
        """Read JSON file with encoding support."""
        with open(file_path, 'r', encoding=self.encoding) as f:
            data = json.load(f)

        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise ValueError(i18n.t('components.input_output.file_input.errors.invalid_json'))

    def get_file_info(self) -> Data:
        """Get file information."""
        file_path = Path(self.file_path)
        info = {
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "file_type": self._detect_file_type(file_path),
            "encoding": self.encoding
        }
        return Data(data=info)
