from typing import Any
from pathlib import Path
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, BoolInput, Output
from lfx.schema import Data


class ETLCSVOutputComponent(Component):
    display_name = i18n.t('components.input_output.csv_output.display_name')
    description = i18n.t('components.input_output.csv_output.description')
    icon = "file"
    name = "ETLCSVOutput"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.input_output.csv_output.data_input.display_name'), info=i18n.t('components.input_output.csv_output.data_input.info'), is_list=True, required=True),
        MessageTextInput(name="file_path", display_name=i18n.t('components.input_output.csv_output.file_path.display_name'), info=i18n.t('components.input_output.csv_output.file_path.info'), required=True),
        MessageTextInput(name="delimiter", display_name=i18n.t('components.input_output.csv_output.delimiter.display_name'), info=i18n.t('components.input_output.csv_output.delimiter.info'), value=",", advanced=True),
        MessageTextInput(name="encoding", display_name=i18n.t('components.input_output.csv_output.encoding.display_name'), info=i18n.t('components.input_output.csv_output.encoding.info'), value="utf-8", advanced=True),
        BoolInput(name="include_header", display_name=i18n.t('components.input_output.csv_output.include_header.display_name'), info=i18n.t('components.input_output.csv_output.include_header.info'), value=True, advanced=True)
    ]

    outputs = [Output(name="result", display_name="Export Result", method="export_to_csv")]

    def export_to_csv(self) -> Data:
        try:
            self.status = i18n.t('components.input_output.csv_output.status.exporting')
            if not self.data_input:
                raise ValueError(i18n.t('components.input_output.csv_output.errors.no_data'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            file_path = Path(self.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(file_path, sep=self.delimiter, encoding=self.encoding, index=False, header=self.include_header)
            result_info = {"file_path": str(file_path), "rows_exported": len(df), "delimiter": self.delimiter}
            self.status = i18n.t('components.input_output.csv_output.status.success', rows=len(df))
            return Data(data=result_info)
        except Exception as e:
            error_msg = i18n.t('components.input_output.csv_output.errors.export_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
