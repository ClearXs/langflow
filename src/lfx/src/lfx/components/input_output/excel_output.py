from typing import Any
from pathlib import Path
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, BoolInput, Output
from lfx.schema import Data


class ETLExcelOutputComponent(Component):
    display_name = i18n.t('components.input_output.excel_output.display_name')
    description = i18n.t('components.input_output.excel_output.description')
    icon = "file-text"
    name = "ETLExcelOutput"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.input_output.excel_output.data_input.display_name'), info=i18n.t('components.input_output.excel_output.data_input.info'), is_list=True, required=True),
        MessageTextInput(name="file_path", display_name=i18n.t('components.input_output.excel_output.file_path.display_name'), info=i18n.t('components.input_output.excel_output.file_path.info'), required=True),
        MessageTextInput(name="sheet_name", display_name=i18n.t('components.input_output.excel_output.sheet_name.display_name'), info=i18n.t('components.input_output.excel_output.sheet_name.info'), value="Sheet1"),
        BoolInput(name="include_index", display_name=i18n.t('components.input_output.excel_output.include_index.display_name'), info=i18n.t('components.input_output.excel_output.include_index.info'), value=False, advanced=True)
    ]

    outputs = [Output(name="result", display_name="Export Result", method="export_to_excel")]

    def export_to_excel(self) -> Data:
        try:
            self.status = i18n.t('components.input_output.excel_output.status.exporting')
            if not self.data_input:
                raise ValueError(i18n.t('components.input_output.excel_output.errors.no_data'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            file_path = Path(self.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(file_path, sheet_name=self.sheet_name, index=self.include_index)
            result_info = {"file_path": str(file_path), "rows_exported": len(df), "sheet_name": self.sheet_name}
            self.status = i18n.t('components.input_output.excel_output.status.success', rows=len(df))
            return Data(data=result_info)
        except Exception as e:
            error_msg = i18n.t('components.input_output.excel_output.errors.export_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
