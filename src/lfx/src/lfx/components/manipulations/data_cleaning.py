from typing import Any
import i18n
import pandas as pd
import re

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, TableInput, BoolInput, DropdownInput, Output
from lfx.schema import Data


class ETLDataCleaningComponent(Component):
    display_name = i18n.t('components.manipulations.data_cleaning.display_name')
    description = i18n.t('components.manipulations.data_cleaning.description')
    icon = "eraser"
    name = "ETLDataCleaning"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.manipulations.data_cleaning.data_input.display_name'), info=i18n.t('components.manipulations.data_cleaning.data_input.info'), is_list=True, required=True),
        BoolInput(name="trim_whitespace", display_name=i18n.t('components.manipulations.data_cleaning.trim_whitespace.display_name'), info=i18n.t('components.manipulations.data_cleaning.trim_whitespace.info'), value=True),
        BoolInput(name="remove_duplicates", display_name=i18n.t('components.manipulations.data_cleaning.remove_duplicates.display_name'), info=i18n.t('components.manipulations.data_cleaning.remove_duplicates.info'), value=False),
        BoolInput(name="remove_null_rows", display_name=i18n.t('components.manipulations.data_cleaning.remove_null_rows.display_name'), info=i18n.t('components.manipulations.data_cleaning.remove_null_rows.info'), value=False),
        BoolInput(name="remove_special_chars", display_name=i18n.t('components.manipulations.data_cleaning.remove_special_chars.display_name'), info=i18n.t('components.manipulations.data_cleaning.remove_special_chars.info'), value=False, advanced=True),
        BoolInput(name="normalize_case", display_name=i18n.t('components.manipulations.data_cleaning.normalize_case.display_name'), info=i18n.t('components.manipulations.data_cleaning.normalize_case.info'), value=False, advanced=True),
        DropdownInput(name="case_type", display_name=i18n.t('components.manipulations.data_cleaning.case_type.display_name'), info=i18n.t('components.manipulations.data_cleaning.case_type.info'), options=["lower", "upper", "title"], value="lower", advanced=True)
    ]

    outputs = [Output(name="data", display_name="Cleaned Data", method="clean_data")]

    def clean_data(self) -> list[Data]:
        try:
            if not self.data_input:
                raise ValueError(i18n.t('components.manipulations.data_cleaning.errors.no_data'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            if self.trim_whitespace:
                for col in df.select_dtypes(include=['object']).columns:
                    df[col] = df[col].str.strip()
            if self.remove_duplicates:
                df = df.drop_duplicates()
            if self.remove_null_rows:
                df = df.dropna()
            if self.remove_special_chars:
                for col in df.select_dtypes(include=['object']).columns:
                    df[col] = df[col].apply(lambda x: re.sub(r'[^A-Za-z0-9\s]', '', str(x)) if pd.notnull(x) else x)
            if self.normalize_case:
                for col in df.select_dtypes(include=['object']).columns:
                    if self.case_type == "lower":
                        df[col] = df[col].str.lower()
                    elif self.case_type == "upper":
                        df[col] = df[col].str.upper()
                    elif self.case_type == "title":
                        df[col] = df[col].str.title()
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t('components.manipulations.data_cleaning.status.success', count=len(result))
            return result
        except Exception as e:
            error_msg = i18n.t('components.manipulations.data_cleaning.errors.cleaning_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
