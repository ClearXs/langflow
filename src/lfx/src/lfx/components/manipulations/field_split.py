import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, IntInput, MessageTextInput, Output
from lfx.schema import Data


class ETLFieldSplitComponent(Component):
    display_name = i18n.t("components.manipulations.field_split.display_name")
    description = i18n.t("components.manipulations.field_split.description")
    icon = "scissors"
    name = "ETLFieldSplit"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_split.data_input.display_name"),
            info=i18n.t("components.manipulations.field_split.data_input.info"),
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="source_field",
            display_name=i18n.t("components.manipulations.field_split.source_field.display_name"),
            info=i18n.t("components.manipulations.field_split.source_field.info"),
            required=True,
        ),
        MessageTextInput(
            name="delimiter",
            display_name=i18n.t("components.manipulations.field_split.delimiter.display_name"),
            info=i18n.t("components.manipulations.field_split.delimiter.info"),
            value=",",
            required=True,
        ),
        MessageTextInput(
            name="new_field_names",
            display_name=i18n.t("components.manipulations.field_split.new_field_names.display_name"),
            info=i18n.t("components.manipulations.field_split.new_field_names.info"),
            placeholder="field1,field2,field3",
        ),
        IntInput(
            name="max_splits",
            display_name=i18n.t("components.manipulations.field_split.max_splits.display_name"),
            info=i18n.t("components.manipulations.field_split.max_splits.info"),
            value=-1,
            advanced=True,
        ),
        BoolInput(
            name="drop_source_field",
            display_name=i18n.t("components.manipulations.field_split.drop_source_field.display_name"),
            info=i18n.t("components.manipulations.field_split.drop_source_field.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [Output(name="data", display_name="Split Data", method="split_field")]

    def split_field(self) -> list[Data]:
        try:
            if not self.data_input or not self.source_field:
                raise ValueError(i18n.t("components.manipulations.field_split.errors.missing_config"))
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])
            if self.source_field not in df.columns:
                raise ValueError(
                    i18n.t("components.manipulations.field_split.errors.field_not_found", field=self.source_field)
                )
            split_cols = df[self.source_field].str.split(
                self.delimiter, n=self.max_splits if self.max_splits > 0 else -1, expand=True
            )
            if self.new_field_names:
                field_names = [f.strip() for f in self.new_field_names.split(",")]
                split_cols.columns = field_names[: len(split_cols.columns)]
            else:
                split_cols.columns = [f"{self.source_field}_{i}" for i in range(len(split_cols.columns))]
            df = pd.concat([df, split_cols], axis=1)
            if self.drop_source_field:
                df = df.drop(columns=[self.source_field])
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t("components.manipulations.field_split.status.success", count=len(result))
            return result
        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_split.errors.split_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
