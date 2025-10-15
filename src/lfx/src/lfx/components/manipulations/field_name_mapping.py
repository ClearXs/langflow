from typing import Any
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, TableInput, BoolInput, Output
from lfx.schema import Data


class ETLFieldNameMappingComponent(Component):
    display_name = i18n.t('components.manipulations.field_name_mapping.display_name')
    description = i18n.t('components.manipulations.field_name_mapping.description')
    icon = "shuffle"
    name = "ETLFieldNameMapping"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t('components.manipulations.field_name_mapping.data_input.display_name'),
            info=i18n.t('components.manipulations.field_name_mapping.data_input.info'),
            is_list=True,
            required=True
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t('components.manipulations.field_name_mapping.field_mappings.display_name'),
            info=i18n.t('components.manipulations.field_name_mapping.field_mappings.info'),
            table_schema=[
                {"name": "source_field", "display_name": "Source Field", "type": "str"},
                {"name": "target_field", "display_name": "Target Field", "type": "str"}
            ],
            value=[],
            required=True
        ),
        BoolInput(
            name="drop_unmapped",
            display_name=i18n.t('components.manipulations.field_name_mapping.drop_unmapped.display_name'),
            info=i18n.t('components.manipulations.field_name_mapping.drop_unmapped.info'),
            value=False,
            advanced=True
        )
    ]

    outputs = [
        Output(name="data", display_name="Mapped Data", method="map_field_names")
    ]

    def map_field_names(self) -> list[Data]:
        """Map source field names to target field names."""
        try:
            if not self.data_input or not self.field_mappings:
                raise ValueError(i18n.t('components.manipulations.field_name_mapping.errors.missing_config'))

            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])

            mapping_dict = {m['source_field']: m['target_field'] for m in self.field_mappings}
            df = df.rename(columns=mapping_dict)

            if self.drop_unmapped:
                mapped_fields = list(mapping_dict.values())
                df = df[mapped_fields]

            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t('components.manipulations.field_name_mapping.status.success', count=len(result))
            return result

        except Exception as e:
            error_msg = i18n.t('components.manipulations.field_name_mapping.errors.mapping_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
