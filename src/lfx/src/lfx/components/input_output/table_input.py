from typing import Any
import i18n
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.custom.custom_component.component import Component
from lfx.io import (
    MessageTextInput,
    MultilineInput,
    DropdownInput,
    BoolInput,
    IntInput,
    TableInput,
    Output
)
from lfx.schema import Data


class ETLTableInputComponent(Component):
    display_name = i18n.t('components.input_output.table_input.display_name')
    description = i18n.t('components.input_output.table_input.description')
    icon = "database"
    name = "ETLTableInput"

    inputs = [
        MessageTextInput(
            name="connection_string",
            display_name=i18n.t('components.input_output.table_input.connection_string.display_name'),
            info=i18n.t('components.input_output.table_input.connection_string.info'),
            required=True,
            placeholder="postgresql://user:password@host:port/database"
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t('components.input_output.table_input.table_name.display_name'),
            info=i18n.t('components.input_output.table_input.table_name.info'),
            required=True,
            placeholder="table_name"
        ),
        MultilineInput(
            name="sql_query",
            display_name=i18n.t('components.input_output.table_input.sql_query.display_name'),
            info=i18n.t('components.input_output.table_input.sql_query.info'),
            placeholder="SELECT * FROM {table_name}",
            advanced=True
        ),
        BoolInput(
            name="use_pagination",
            display_name=i18n.t('components.input_output.table_input.use_pagination.display_name'),
            info=i18n.t('components.input_output.table_input.use_pagination.info'),
            value=True,
            advanced=True
        ),
        IntInput(
            name="page_size",
            display_name=i18n.t('components.input_output.table_input.page_size.display_name'),
            info=i18n.t('components.input_output.table_input.page_size.info'),
            value=1000,
            range_spec={"min": 1, "max": 100000},
            advanced=True
        ),
        IntInput(
            name="max_records",
            display_name=i18n.t('components.input_output.table_input.max_records.display_name'),
            info=i18n.t('components.input_output.table_input.max_records.info'),
            value=0,
            advanced=True
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t('components.input_output.table_input.enable_transaction.display_name'),
            info=i18n.t('components.input_output.table_input.enable_transaction.info'),
            value=False,
            advanced=True
        ),
        DropdownInput(
            name="isolation_level",
            display_name=i18n.t('components.input_output.table_input.isolation_level.display_name'),
            info=i18n.t('components.input_output.table_input.isolation_level.info'),
            options=["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "DEFAULT"],
            value="DEFAULT",
            advanced=True
        ),
        MessageTextInput(
            name="incremental_timestamp_init",
            display_name=i18n.t('components.input_output.table_input.incremental_timestamp_init.display_name'),
            info=i18n.t('components.input_output.table_input.incremental_timestamp_init.info'),
            placeholder="2024-01-01 00:00:00",
            advanced=True
        ),
        IntInput(
            name="incremental_offset_seconds",
            display_name=i18n.t('components.input_output.table_input.incremental_offset_seconds.display_name'),
            info=i18n.t('components.input_output.table_input.incremental_offset_seconds.info'),
            value=0,
            advanced=True
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t('components.input_output.table_input.field_mappings.display_name'),
            info=i18n.t('components.input_output.table_input.field_mappings.info'),
            table_schema=[
                {"name": "field_name", "display_name": "Field Name", "type": "str"},
                {"name": "data_type", "display_name": "Data Type", "type": "str"},
                {"name": "default_value", "display_name": "Default Value", "type": "str"},
                {"name": "transformation_rule", "display_name": "Transformation Rule", "type": "str"}
            ],
            value=[],
            advanced=True
        )
    ]

    outputs = [
        Output(name="data", display_name="Data", method="extract_data"),
        Output(name="row_count", display_name="Row Count", method="get_row_count")
    ]

    def extract_data(self) -> list[Data]:
        """Extract data from database table with SQL support, pagination, and transaction handling."""
        try:
            self.status = i18n.t('components.input_output.table_input.status.connecting')

            # Validate inputs
            if not self.connection_string or not self.table_name:
                raise ValueError(i18n.t('components.input_output.table_input.errors.missing_config'))

            # Build SQL query
            sql_query = self.sql_query.strip() if self.sql_query else f"SELECT * FROM {self.table_name}"

            # Replace table name placeholder
            sql_query = sql_query.replace("{table_name}", self.table_name)

            # Create database engine
            engine = create_engine(
                self.connection_string,
                poolclass=NullPool,
                isolation_level=self.isolation_level if self.isolation_level != "DEFAULT" else None
            )

            result_data = []
            total_records = 0

            with engine.connect() as connection:
                # Start transaction if enabled
                if self.enable_transaction:
                    trans = connection.begin()
                    try:
                        result_data = self._fetch_data(connection, sql_query)
                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        raise e
                else:
                    result_data = self._fetch_data(connection, sql_query)

            total_records = len(result_data)
            self.status = i18n.t('components.input_output.table_input.status.success', records=total_records)

            return result_data

        except Exception as e:
            error_msg = i18n.t('components.input_output.table_input.errors.extraction_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _fetch_data(self, connection, sql_query: str) -> list[Data]:
        """Fetch data with pagination support."""
        result_data = []

        if self.use_pagination:
            offset = 0
            while True:
                # Apply pagination to query
                paginated_query = f"{sql_query} LIMIT {self.page_size} OFFSET {offset}"

                df = pd.read_sql_query(text(paginated_query), connection)

                if df.empty:
                    break

                # Convert DataFrame to Data objects
                for _, row in df.iterrows():
                    row_dict = row.to_dict()

                    # Apply field transformations if configured
                    if self.field_mappings:
                        row_dict = self._apply_field_transformations(row_dict)

                    result_data.append(Data(data=row_dict))

                offset += self.page_size

                # Check max records limit
                if self.max_records > 0 and len(result_data) >= self.max_records:
                    result_data = result_data[:self.max_records]
                    break
        else:
            # Fetch all data at once
            df = pd.read_sql_query(text(sql_query), connection)

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                if self.field_mappings:
                    row_dict = self._apply_field_transformations(row_dict)

                result_data.append(Data(data=row_dict))

                if self.max_records > 0 and len(result_data) >= self.max_records:
                    break

        return result_data

    def _apply_field_transformations(self, row_dict: dict) -> dict:
        """Apply field transformations based on field mappings."""
        if not isinstance(self.field_mappings, list):
            return row_dict

        for mapping in self.field_mappings:
            field_name = mapping.get('field_name')
            default_value = mapping.get('default_value')

            # Apply default value if field is None or missing
            if field_name and default_value:
                if field_name not in row_dict or row_dict[field_name] is None:
                    row_dict[field_name] = default_value

        return row_dict

    def get_row_count(self) -> Data:
        """Get the count of extracted rows."""
        data = self.extract_data()
        count = len(data)
        return Data(data={"row_count": count, "table": self.table_name})
