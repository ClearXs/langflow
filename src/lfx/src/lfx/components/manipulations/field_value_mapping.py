from typing import Any
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, TableInput, MessageTextInput, BoolInput, Output
from lfx.schema import Data


class ETLFieldValueMappingComponent(Component):
    display_name = i18n.t('components.manipulations.field_value_mapping.display_name')
    description = i18n.t('components.manipulations.field_value_mapping.description')
    icon = "map"
    name = "ETLFieldValueMapping"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.manipulations.field_value_mapping.data_input.display_name'), info=i18n.t('components.manipulations.field_value_mapping.data_input.info'), is_list=True, required=True),
        MessageTextInput(name="field_name", display_name=i18n.t('components.manipulations.field_value_mapping.field_name.display_name'), info=i18n.t('components.manipulations.field_value_mapping.field_name.info'), required=True),
        TableInput(name="value_mappings", display_name=i18n.t('components.manipulations.field_value_mapping.value_mappings.display_name'), info=i18n.t('components.manipulations.field_value_mapping.value_mappings.info'), table_schema=[{"name": "source_value", "display_name": "Source Value", "type": "str"}, {"name": "target_value", "display_name": "Target Value", "type": "str"}], value=[], required=True),
        MessageTextInput(name="default_value", display_name=i18n.t('components.manipulations.field_value_mapping.default_value.display_name'), info=i18n.t('components.manipulations.field_value_mapping.default_value.info'), advanced=True)
    ]

    outputs = [Output(name="data", display_name="Mapped Data", method="map_field_values")]

    def map_field_values(self) -> list[Data]:
        try:
            if not self.data_input or not self.value_mappings:
                raise ValueError(i18n.t('components.manipulations.field_value_mapping.errors.missing_config'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            mapping_dict = {str(m['source_value']): str(m['target_value']) for m in self.value_mappings}
            if self.field_name in df.columns:
                df[self.field_name] = df[self.field_name].astype(str).map(mapping_dict).fillna(self.default_value if self.default_value else df[self.field_name])
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t('components.manipulations.field_value_mapping.status.success', count=len(result))
            return result
        except Exception as e:
            error_msg = i18n.t('components.manipulations.field_value_mapping.errors.mapping_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
