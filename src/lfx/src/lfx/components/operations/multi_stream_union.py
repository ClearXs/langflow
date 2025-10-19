import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, MessageTextInput, Output
from lfx.schema import Data


class ETLMultiStreamUnionComponent(Component):
    display_name = i18n.t("components.operations.multi_stream_union.display_name")
    description = i18n.t("components.operations.multi_stream_union.description")
    icon = "layers"
    name = "ETLMultiStreamUnion"

    inputs = [
        DataInput(
            name="stream_1",
            display_name=i18n.t("components.operations.multi_stream_union.stream_1.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_1.info"),
            is_list=True,
            required=True,
        ),
        DataInput(
            name="stream_2",
            display_name=i18n.t("components.operations.multi_stream_union.stream_2.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_2.info"),
            is_list=True,
        ),
        DataInput(
            name="stream_3",
            display_name=i18n.t("components.operations.multi_stream_union.stream_3.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_3.info"),
            is_list=True,
            advanced=True,
        ),
        DataInput(
            name="stream_4",
            display_name=i18n.t("components.operations.multi_stream_union.stream_4.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_4.info"),
            is_list=True,
            advanced=True,
        ),
        DataInput(
            name="stream_5",
            display_name=i18n.t("components.operations.multi_stream_union.stream_5.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_5.info"),
            is_list=True,
            advanced=True,
        ),
        BoolInput(
            name="drop_duplicates",
            display_name=i18n.t("components.operations.multi_stream_union.drop_duplicates.display_name"),
            info=i18n.t("components.operations.multi_stream_union.drop_duplicates.info"),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="align_schemas",
            display_name=i18n.t("components.operations.multi_stream_union.align_schemas.display_name"),
            info=i18n.t("components.operations.multi_stream_union.align_schemas.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="source_column",
            display_name=i18n.t("components.operations.multi_stream_union.source_column.display_name"),
            info=i18n.t("components.operations.multi_stream_union.source_column.info"),
            value="_source_stream",
            advanced=True,
        ),
        BoolInput(
            name="include_source_info",
            display_name=i18n.t("components.operations.multi_stream_union.include_source_info.display_name"),
            info=i18n.t("components.operations.multi_stream_union.include_source_info.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="data", display_name="Merged Data", method="union_streams"),
        Output(name="union_stats", display_name="Union Statistics", method="get_union_stats"),
    ]

    def union_streams(self) -> list[Data]:
        """Merge multiple data streams with schema alignment and deduplication."""
        try:
            self.status = i18n.t("components.operations.multi_stream_union.status.merging")

            # Collect all streams
            all_streams = []
            stream_names = []

            for i in range(1, 6):
                stream = getattr(self, f"stream_{i}", None)
                if stream:
                    all_streams.append(stream)
                    stream_names.append(f"stream_{i}")

            if not all_streams:
                raise ValueError(i18n.t("components.operations.multi_stream_union.errors.no_streams"))

            # Convert to DataFrames
            dataframes = []
            for idx, stream in enumerate(all_streams):
                df = self._convert_to_dataframe(stream)

                if self.include_source_info:
                    df[self.source_column] = stream_names[idx]

                dataframes.append(df)

            # Merge all DataFrames
            if self.align_schemas:
                merged_df = pd.concat(dataframes, ignore_index=True, sort=False)
                merged_df = merged_df.fillna("")
            else:
                merged_df = pd.concat(dataframes, ignore_index=True)

            # Drop duplicates if requested
            if self.drop_duplicates:
                merged_df = merged_df.drop_duplicates()

            # Convert back to Data objects
            result_data = []
            for _, row in merged_df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            self.status = i18n.t("components.operations.multi_stream_union.status.success", records=len(result_data))
            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.multi_stream_union.errors.union_failed", error=str(e))
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

    def get_union_stats(self) -> Data:
        """Get statistics about the union operation."""
        merged = self.union_streams()

        stream_counts = []
        for i in range(1, 6):
            stream = getattr(self, f"stream_{i}", None)
            if stream:
                stream_counts.append(len(stream))

        stats = {
            "total_streams": len(stream_counts),
            "stream_counts": stream_counts,
            "merged_count": len(merged),
            "drop_duplicates": self.drop_duplicates,
            "align_schemas": self.align_schemas,
        }

        return Data(data=stats)
