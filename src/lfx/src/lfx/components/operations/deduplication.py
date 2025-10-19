import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, Output, TableInput
from lfx.schema import Data


class ETLDeduplicationComponent(Component):
    display_name = i18n.t("components.operations.deduplication.display_name")
    description = i18n.t("components.operations.deduplication.description")
    icon = "filter"
    name = "ETLDeduplication"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.operations.deduplication.data_input.display_name"),
            info=i18n.t("components.operations.deduplication.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="key_columns",
            display_name=i18n.t("components.operations.deduplication.key_columns.display_name"),
            info=i18n.t("components.operations.deduplication.key_columns.info"),
            table_schema=[{"name": "column", "display_name": "Column Name", "type": "str"}],
            value=[],
        ),
        DropdownInput(
            name="keep_strategy",
            display_name=i18n.t("components.operations.deduplication.keep_strategy.display_name"),
            info=i18n.t("components.operations.deduplication.keep_strategy.info"),
            options=["first", "last", "none"],
            value="first",
        ),
        BoolInput(
            name="ignore_null",
            display_name=i18n.t("components.operations.deduplication.ignore_null.display_name"),
            info=i18n.t("components.operations.deduplication.ignore_null.info"),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t("components.operations.deduplication.case_sensitive.display_name"),
            info=i18n.t("components.operations.deduplication.case_sensitive.info"),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="trim_whitespace",
            display_name=i18n.t("components.operations.deduplication.trim_whitespace.display_name"),
            info=i18n.t("components.operations.deduplication.trim_whitespace.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="data", display_name="Deduplicated Data", method="deduplicate"),
        Output(name="dedup_stats", display_name="Deduplication Statistics", method="get_dedup_stats"),
        Output(name="duplicates", display_name="Removed Duplicates", method="get_duplicates"),
    ]

    def deduplicate(self) -> list[Data]:
        """Remove duplicate records based on configurable key columns."""
        try:
            self.status = i18n.t("components.operations.deduplication.status.deduplicating")

            if not self.data_input:
                raise ValueError(i18n.t("components.operations.deduplication.errors.no_data"))

            # Convert to DataFrame
            df = self._convert_to_dataframe(self.data_input)

            # Get key columns
            if self.key_columns:
                subset_cols = [col["column"] for col in self.key_columns]
            else:
                subset_cols = None  # Use all columns

            # Preprocess data if needed
            if subset_cols and self.trim_whitespace:
                for col in subset_cols:
                    if col in df.columns and df[col].dtype == "object":
                        df[col] = df[col].astype(str).str.strip()

            if subset_cols and not self.case_sensitive:
                for col in subset_cols:
                    if col in df.columns and df[col].dtype == "object":
                        df[col] = df[col].astype(str).str.lower()

            # Remove duplicates
            keep_param = self.keep_strategy if self.keep_strategy != "none" else False

            deduplicated_df = df.drop_duplicates(subset=subset_cols, keep=keep_param)

            # Convert back to Data objects
            result_data = []
            for _, row in deduplicated_df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            removed_count = len(df) - len(deduplicated_df)
            self.status = i18n.t(
                "components.operations.deduplication.status.success", unique=len(result_data), duplicates=removed_count
            )

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.deduplication.errors.dedup_failed", error=str(e))
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

    def get_dedup_stats(self) -> Data:
        """Get deduplication statistics."""
        original_count = len(self.data_input) if self.data_input else 0
        deduplicated = self.deduplicate()
        unique_count = len(deduplicated)
        duplicate_count = original_count - unique_count

        stats = {
            "original_count": original_count,
            "unique_count": unique_count,
            "duplicate_count": duplicate_count,
            "deduplication_rate": round(duplicate_count / original_count * 100, 2) if original_count > 0 else 0,
            "key_columns": [col["column"] for col in self.key_columns] if self.key_columns else "all",
            "keep_strategy": self.keep_strategy,
        }

        return Data(data=stats)

    def get_duplicates(self) -> list[Data]:
        """Get the removed duplicate records."""
        if not self.data_input:
            return []

        df = self._convert_to_dataframe(self.data_input)

        if self.key_columns:
            subset_cols = [col["column"] for col in self.key_columns]
        else:
            subset_cols = None

        # Mark duplicates
        duplicates_mask = df.duplicated(
            subset=subset_cols, keep=self.keep_strategy if self.keep_strategy != "none" else False
        )
        duplicates_df = df[duplicates_mask]

        # Convert to Data objects
        duplicate_data = []
        for _, row in duplicates_df.iterrows():
            row_dict = row.to_dict()
            duplicate_data.append(Data(data=row_dict))

        return duplicate_data
