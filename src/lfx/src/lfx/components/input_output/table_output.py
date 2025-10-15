from typing import Any
import i18n
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.pool import NullPool

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, DropdownInput, BoolInput, IntInput, TableInput, Output
from lfx.schema import Data


class ETLTableOutputComponent(Component):
    display_name = i18n.t('components.input_output.table_output.display_name')
    description = i18n.t('components.input_output.table_output.description')
    icon = "database"
    name = "ETLTableOutput"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.input_output.table_output.data_input.display_name'), info=i18n.t('components.input_output.table_output.data_input.info'), is_list=True, required=True),
        MessageTextInput(name="connection_string", display_name=i18n.t('components.input_output.table_output.connection_string.display_name'), info=i18n.t('components.input_output.table_output.connection_string.info'), required=True),
        MessageTextInput(name="table_name", display_name=i18n.t('components.input_output.table_output.table_name.display_name'), info=i18n.t('components.input_output.table_output.table_name.info'), required=True),
        DropdownInput(name="write_mode", display_name=i18n.t('components.input_output.table_output.write_mode.display_name'), info=i18n.t('components.input_output.table_output.write_mode.info'), options=["append", "replace", "upsert", "fail"], value="append"),
        TableInput(name="key_columns", display_name=i18n.t('components.input_output.table_output.key_columns.display_name'), info=i18n.t('components.input_output.table_output.key_columns.info'), table_schema=[{"name": "column", "display_name": "Column", "type": "str"}], value=[], advanced=True),
        BoolInput(name="auto_create_table", display_name=i18n.t('components.input_output.table_output.auto_create_table.display_name'), info=i18n.t('components.input_output.table_output.auto_create_table.info'), value=True, advanced=True),
        IntInput(name="batch_size", display_name=i18n.t('components.input_output.table_output.batch_size.display_name'), info=i18n.t('components.input_output.table_output.batch_size.info'), value=1000, advanced=True),
        BoolInput(name="truncate_first", display_name=i18n.t('components.input_output.table_output.truncate_first.display_name'), info=i18n.t('components.input_output.table_output.truncate_first.info'), value=False, advanced=True)
    ]

    outputs = [Output(name="result", display_name="Write Result", method="write_to_table")]

    def write_to_table(self) -> Data:
        try:
            self.status = i18n.t('components.input_output.table_output.status.writing')
            if not self.data_input:
                raise ValueError(i18n.t('components.input_output.table_output.errors.no_data'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            engine = create_engine(self.connection_string, poolclass=NullPool)
            with engine.connect() as connection:
                if self.truncate_first and self.write_mode != "replace":
                    connection.execute(text(f"TRUNCATE TABLE {self.table_name}"))
                    connection.commit()
                if self.write_mode == "upsert":
                    self._upsert_data(df, connection)
                else:
                    if_exists = 'replace' if self.write_mode == 'replace' else 'append'
                    df.to_sql(self.table_name, connection, if_exists=if_exists, index=False, chunksize=self.batch_size)
            result_info = {"table": self.table_name, "rows_written": len(df), "write_mode": self.write_mode}
            self.status = i18n.t('components.input_output.table_output.status.success', rows=len(df))
            return Data(data=result_info)
        except Exception as e:
            error_msg = i18n.t('components.input_output.table_output.errors.write_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _upsert_data(self, df, connection):
        if not self.key_columns:
            raise ValueError(i18n.t('components.input_output.table_output.errors.no_keys_for_upsert'))
        key_cols = [col['column'] for col in self.key_columns]
        for _, row in df.iterrows():
            where_clause = " AND ".join([f"{col} = :{col}" for col in key_cols])
            update_set = ", ".join([f"{col} = :{col}" for col in df.columns if col not in key_cols])
            params = row.to_dict()
            check_query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
            result = connection.execute(text(check_query), params).scalar()
            if result > 0:
                if update_set:
                    update_query = f"UPDATE {self.table_name} SET {update_set} WHERE {where_clause}"
                    connection.execute(text(update_query), params)
            else:
                cols = ", ".join(df.columns)
                placeholders = ", ".join([f":{col}" for col in df.columns])
                insert_query = f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholders})"
                connection.execute(text(insert_query), params)
        connection.commit()
