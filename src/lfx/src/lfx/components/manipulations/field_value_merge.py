import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output, TableInput
from lfx.schema import Data


class ETLFieldValueMergeComponent(Component):
    display_name = i18n.t("components.manipulations.field_value_merge.display_name")
    description = i18n.t("components.manipulations.field_value_merge.description")
    icon = "git-merge"
    name = "ETLFieldValueMerge"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_value_merge.data_input.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="merge_configs",
            display_name=i18n.t("components.manipulations.field_value_merge.merge_configs.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.merge_configs.info"),
            table_schema=[
                {"name": "source_fields", "display_name": "Source Fields (comma-separated)", "type": "str"},
                {"name": "target_field", "display_name": "Target Field", "type": "str"},
                {"name": "separator", "display_name": "Separator", "type": "str"},
            ],
            value=[],
            required=True,
        ),
        BoolInput(
            name="drop_source_fields",
            display_name=i18n.t("components.manipulations.field_value_merge.drop_source_fields.display_name"),
            info=i18n.t("components.manipulations.field_value_merge.drop_source_fields.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [Output(name="data", display_name="Merged Data", method="merge_field_values")]

    def merge_field_values(self) -> list[Data]:
        """Merge multiple field values into one with separator."""
        try:
            if not self.data_input or not self.merge_configs:
                raise ValueError(i18n.t("components.manipulations.field_value_merge.errors.missing_config"))

            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            for config in self.merge_configs:
                source_fields = [f.strip() for f in config["source_fields"].split(",")]
                target_field = config["target_field"]
                separator = config.get("separator", " ")

                df[target_field] = df[source_fields].astype(str).agg(separator.join, axis=1)

                if self.drop_source_fields:
                    df = df.drop(columns=source_fields, errors="ignore")

            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t("components.manipulations.field_value_merge.status.success", count=len(result))
            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_value_merge.errors.merge_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
