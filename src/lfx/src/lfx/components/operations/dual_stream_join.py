import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, MessageTextInput, Output, TableInput
from lfx.schema import Data


class ETLDualStreamJoinComponent(Component):
    display_name = i18n.t("components.operations.dual_stream_join.display_name")
    description = i18n.t("components.operations.dual_stream_join.description")
    icon = "git-merge"
    name = "ETLDualStreamJoin"

    inputs = [
        DataInput(
            name="left_stream",
            display_name=i18n.t("components.operations.dual_stream_join.left_stream.display_name"),
            info=i18n.t("components.operations.dual_stream_join.left_stream.info"),
            is_list=True,
            required=True,
        ),
        DataInput(
            name="right_stream",
            display_name=i18n.t("components.operations.dual_stream_join.right_stream.display_name"),
            info=i18n.t("components.operations.dual_stream_join.right_stream.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="join_type",
            display_name=i18n.t("components.operations.dual_stream_join.join_type.display_name"),
            info=i18n.t("components.operations.dual_stream_join.join_type.info"),
            options=["inner", "left", "right", "outer"],
            value="inner",
        ),
        TableInput(
            name="join_conditions",
            display_name=i18n.t("components.operations.dual_stream_join.join_conditions.display_name"),
            info=i18n.t("components.operations.dual_stream_join.join_conditions.info"),
            table_schema=[
                {"name": "left_key", "display_name": "Left Key", "type": "str"},
                {"name": "right_key", "display_name": "Right Key", "type": "str"},
                {"name": "operator", "display_name": "Operator", "type": "str"},
            ],
            value=[],
            required=True,
        ),
        MessageTextInput(
            name="left_prefix",
            display_name=i18n.t("components.operations.dual_stream_join.left_prefix.display_name"),
            info=i18n.t("components.operations.dual_stream_join.left_prefix.info"),
            value="left_",
            advanced=True,
        ),
        MessageTextInput(
            name="right_prefix",
            display_name=i18n.t("components.operations.dual_stream_join.right_prefix.display_name"),
            info=i18n.t("components.operations.dual_stream_join.right_prefix.info"),
            value="right_",
            advanced=True,
        ),
        BoolInput(
            name="drop_duplicates",
            display_name=i18n.t("components.operations.dual_stream_join.drop_duplicates.display_name"),
            info=i18n.t("components.operations.dual_stream_join.drop_duplicates.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="data", display_name="Joined Data", method="join_streams"),
        Output(name="join_stats", display_name="Join Statistics", method="get_join_stats"),
    ]

    def join_streams(self) -> list[Data]:
        """Join two data streams using inner/left/right/outer join operations."""
        try:
            self.status = i18n.t("components.operations.dual_stream_join.status.joining")

            # Validate inputs
            if not self.left_stream or not self.right_stream:
                raise ValueError(i18n.t("components.operations.dual_stream_join.errors.missing_streams"))

            if not self.join_conditions:
                raise ValueError(i18n.t("components.operations.dual_stream_join.errors.missing_conditions"))

            # Convert Data objects to DataFrames
            left_df = self._convert_to_dataframe(self.left_stream)
            right_df = self._convert_to_dataframe(self.right_stream)

            # Extract join keys
            left_keys = [cond["left_key"] for cond in self.join_conditions]
            right_keys = [cond["right_key"] for cond in self.join_conditions]

            # Perform join
            joined_df = pd.merge(
                left_df,
                right_df,
                left_on=left_keys,
                right_on=right_keys,
                how=self.join_type,
                suffixes=(f"_{self.left_prefix}", f"_{self.right_prefix}"),
            )

            # Drop duplicates if requested
            if self.drop_duplicates:
                joined_df = joined_df.drop_duplicates()

            # Convert back to Data objects
            result_data = []
            for _, row in joined_df.iterrows():
                row_dict = row.to_dict()
                row_dict["_join_type"] = self.join_type
                result_data.append(Data(data=row_dict))

            self.status = i18n.t("components.operations.dual_stream_join.status.success", records=len(result_data))
            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.dual_stream_join.errors.join_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _convert_to_dataframe(self, data_list: list[Data]) -> pd.DataFrame:
        """Convert list of Data objects to pandas DataFrame."""
        records = []
        for data_obj in data_list:
            if hasattr(data_obj, "data") and isinstance(data_obj.data, dict):
                records.append(data_obj.data)
            elif isinstance(data_obj, dict):
                records.append(data_obj)

        return pd.DataFrame(records)

    def get_join_stats(self) -> Data:
        """Get statistics about the join operation."""
        joined = self.join_streams()

        stats = {
            "join_type": self.join_type,
            "left_stream_count": len(self.left_stream) if self.left_stream else 0,
            "right_stream_count": len(self.right_stream) if self.right_stream else 0,
            "joined_count": len(joined),
            "join_keys": [cond["left_key"] + "=" + cond["right_key"] for cond in self.join_conditions],
        }

        return Data(data=stats)
