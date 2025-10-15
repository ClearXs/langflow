from typing import Any
import i18n
import json
from datetime import datetime

from lfx.custom.custom_component.component import Component
from lfx.io import (
    MessageTextInput,
    DropdownInput,
    BoolInput,
    IntInput,
    Output
)
from lfx.schema import Data


class ETLCDCStreamInputComponent(Component):
    display_name = i18n.t('components.input_output.cdc_input.display_name')
    description = i18n.t('components.input_output.cdc_input.description')
    icon = "database"
    name = "ETLCDCStreamInput"

    inputs = [
        MessageTextInput(
            name="connection_string",
            display_name=i18n.t('components.input_output.cdc_input.connection_string.display_name'),
            info=i18n.t('components.input_output.cdc_input.connection_string.info'),
            required=True,
            placeholder="postgresql://user:password@host:port/database"
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t('components.input_output.cdc_input.table_name.display_name'),
            info=i18n.t('components.input_output.cdc_input.table_name.info'),
            required=True
        ),
        DropdownInput(
            name="cdc_mode",
            display_name=i18n.t('components.input_output.cdc_input.cdc_mode.display_name'),
            info=i18n.t('components.input_output.cdc_input.cdc_mode.info'),
            options=["Timestamp", "Log-Based", "Trigger-Based"],
            value="Timestamp"
        ),
        MessageTextInput(
            name="timestamp_column",
            display_name=i18n.t('components.input_output.cdc_input.timestamp_column.display_name'),
            info=i18n.t('components.input_output.cdc_input.timestamp_column.info'),
            value="updated_at",
            advanced=True
        ),
        MessageTextInput(
            name="last_sync_time",
            display_name=i18n.t('components.input_output.cdc_input.last_sync_time.display_name'),
            info=i18n.t('components.input_output.cdc_input.last_sync_time.info'),
            placeholder="2024-01-01 00:00:00",
            advanced=True
        ),
        IntInput(
            name="poll_interval_seconds",
            display_name=i18n.t('components.input_output.cdc_input.poll_interval_seconds.display_name'),
            info=i18n.t('components.input_output.cdc_input.poll_interval_seconds.info'),
            value=5,
            advanced=True
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t('components.input_output.cdc_input.batch_size.display_name'),
            info=i18n.t('components.input_output.cdc_input.batch_size.info'),
            value=1000,
            advanced=True
        ),
        BoolInput(
            name="capture_deletes",
            display_name=i18n.t('components.input_output.cdc_input.capture_deletes.display_name'),
            info=i18n.t('components.input_output.cdc_input.capture_deletes.info'),
            value=True,
            advanced=True
        ),
        BoolInput(
            name="include_change_type",
            display_name=i18n.t('components.input_output.cdc_input.include_change_type.display_name'),
            info=i18n.t('components.input_output.cdc_input.include_change_type.info'),
            value=True,
            advanced=True
        ),
        MessageTextInput(
            name="primary_keys",
            display_name=i18n.t('components.input_output.cdc_input.primary_keys.display_name'),
            info=i18n.t('components.input_output.cdc_input.primary_keys.info'),
            placeholder="id,uuid",
            advanced=True
        )
    ]

    outputs = [
        Output(name="data", display_name="Data", method="capture_changes"),
        Output(name="change_summary", display_name="Change Summary", method="get_change_summary")
    ]

    def capture_changes(self) -> list[Data]:
        """Capture database changes using Change Data Capture (CDC) in real-time."""
        try:
            self.status = i18n.t('components.input_output.cdc_input.status.capturing')

            if self.cdc_mode == "Timestamp":
                return self._capture_timestamp_based()
            elif self.cdc_mode == "Log-Based":
                return self._capture_log_based()
            elif self.cdc_mode == "Trigger-Based":
                return self._capture_trigger_based()
            else:
                raise ValueError(i18n.t('components.input_output.cdc_input.errors.invalid_mode'))

        except Exception as e:
            error_msg = i18n.t('components.input_output.cdc_input.errors.capture_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _capture_timestamp_based(self) -> list[Data]:
        """Capture changes using timestamp-based tracking."""
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool
        import pandas as pd

        engine = create_engine(self.connection_string, poolclass=NullPool)
        result_data = []

        with engine.connect() as connection:
            # Build query to fetch changes since last sync
            last_sync = self.last_sync_time if self.last_sync_time else '1970-01-01 00:00:00'

            query = f"""
                SELECT * FROM {self.table_name}
                WHERE {self.timestamp_column} > '{last_sync}'
                ORDER BY {self.timestamp_column}
                LIMIT {self.batch_size}
            """

            df = pd.read_sql_query(text(query), connection)

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                if self.include_change_type:
                    row_dict["_change_type"] = "INSERT/UPDATE"
                    row_dict["_capture_time"] = datetime.now().isoformat()

                result_data.append(Data(data=row_dict))

        self.status = i18n.t('components.input_output.cdc_input.status.success', changes=len(result_data))
        return result_data

    def _capture_log_based(self) -> list[Data]:
        """Capture changes using database transaction logs."""
        # This would typically integrate with tools like Debezium, Maxwell, etc.
        # For now, provide a placeholder implementation
        self.log("Log-based CDC requires integration with Debezium or similar tools")

        result_data = []
        info = {
            "message": "Log-based CDC requires additional setup with Debezium/Maxwell",
            "table": self.table_name,
            "mode": "log-based"
        }
        result_data.append(Data(data=info))

        return result_data

    def _capture_trigger_based(self) -> list[Data]:
        """Capture changes using database triggers and audit tables."""
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool
        import pandas as pd

        engine = create_engine(self.connection_string, poolclass=NullPool)
        result_data = []

        # Assume audit table exists with naming convention: {table_name}_audit
        audit_table = f"{self.table_name}_audit"

        with engine.connect() as connection:
            last_sync = self.last_sync_time if self.last_sync_time else '1970-01-01 00:00:00'

            query = f"""
                SELECT * FROM {audit_table}
                WHERE audit_timestamp > '{last_sync}'
                ORDER BY audit_timestamp
                LIMIT {self.batch_size}
            """

            try:
                df = pd.read_sql_query(text(query), connection)

                for _, row in df.iterrows():
                    row_dict = row.to_dict()

                    if self.include_change_type:
                        row_dict["_change_type"] = row_dict.get("operation_type", "UNKNOWN")
                        row_dict["_capture_time"] = datetime.now().isoformat()

                    result_data.append(Data(data=row_dict))

            except Exception as e:
                self.log(f"Audit table {audit_table} may not exist: {e}")
                raise ValueError(i18n.t('components.input_output.cdc_input.errors.audit_table_missing'))

        self.status = i18n.t('components.input_output.cdc_input.status.success', changes=len(result_data))
        return result_data

    def get_change_summary(self) -> Data:
        """Get summary of captured changes."""
        changes = self.capture_changes()
        summary = {
            "table_name": self.table_name,
            "cdc_mode": self.cdc_mode,
            "total_changes": len(changes),
            "capture_time": datetime.now().isoformat()
        }
        return Data(data=summary)
