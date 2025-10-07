import sqlite3
import pandas as pd
from typing import Any, Optional
from pathlib import Path
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, MultilineInput, DropdownInput, BoolInput, IntInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class SQLExecutorComponent(Component):
    display_name = i18n.t('components.data.sql_executor.display_name')
    description = i18n.t('components.data.sql_executor.description')
    icon = "database"
    name = "SQLExecutor"

    inputs = [
        MessageTextInput(
            name="database_url",
            display_name=i18n.t(
                'components.data.sql_executor.database_url.display_name'),
            info=i18n.t('components.data.sql_executor.database_url.info'),
            placeholder="sqlite:///database.db or postgresql://user:pass@host:port/db",
        ),
        MessageTextInput(
            name="database_path",
            display_name=i18n.t(
                'components.data.sql_executor.database_path.display_name'),
            info=i18n.t('components.data.sql_executor.database_path.info'),
            placeholder="/path/to/database.db",
        ),
        DropdownInput(
            name="database_type",
            display_name=i18n.t(
                'components.data.sql_executor.database_type.display_name'),
            info=i18n.t('components.data.sql_executor.database_type.info'),
            options=["sqlite", "postgresql", "mysql", "mssql", "oracle"],
            value="sqlite",
            real_time_refresh=True,
        ),
        MultilineInput(
            name="sql_query",
            display_name=i18n.t(
                'components.data.sql_executor.sql_query.display_name'),
            info=i18n.t('components.data.sql_executor.sql_query.info'),
            required=True,
            placeholder="SELECT * FROM table_name WHERE condition;",
        ),
        DropdownInput(
            name="operation_type",
            display_name=i18n.t(
                'components.data.sql_executor.operation_type.display_name'),
            info=i18n.t('components.data.sql_executor.operation_type.info'),
            options=["select", "insert", "update",
                     "delete", "create", "drop", "alter"],
            value="select",
            advanced=True,
        ),
        BoolInput(
            name="return_only_text",
            display_name=i18n.t(
                'components.data.sql_executor.return_only_text.display_name'),
            info=i18n.t('components.data.sql_executor.return_only_text.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="include_columns",
            display_name=i18n.t(
                'components.data.sql_executor.include_columns.display_name'),
            info=i18n.t('components.data.sql_executor.include_columns.info'),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="limit_rows",
            display_name=i18n.t(
                'components.data.sql_executor.limit_rows.display_name'),
            info=i18n.t('components.data.sql_executor.limit_rows.info'),
            value=1000,
            range_spec=(1, 10000),
            advanced=True,
        ),
        BoolInput(
            name="safe_mode",
            display_name=i18n.t(
                'components.data.sql_executor.safe_mode.display_name'),
            info=i18n.t('components.data.sql_executor.safe_mode.info'),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.sql_executor.text_key.display_name'),
            info=i18n.t('components.data.sql_executor.text_key.info'),
            value="text",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result_data",
            display_name=i18n.t(
                'components.data.sql_executor.outputs.result_data.display_name'),
            method="execute_sql"
        ),
        Output(
            name="result_dataframe",
            display_name=i18n.t(
                'components.data.sql_executor.outputs.result_dataframe.display_name'),
            method="execute_sql_dataframe"
        ),
        Output(
            name="execution_info",
            display_name=i18n.t(
                'components.data.sql_executor.outputs.execution_info.display_name'),
            method="get_execution_info"
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on database type selection."""
        if field_name == "database_type":
            if field_value == "sqlite":
                build_config["database_path"]["show"] = True
                build_config["database_url"]["show"] = False
            else:
                build_config["database_path"]["show"] = False
                build_config["database_url"]["show"] = True
        return build_config

    def execute_sql(self) -> list[Data]:
        """Execute SQL query and return results as Data objects."""
        try:
            # Validate inputs
            if not self.sql_query.strip():
                error_message = i18n.t(
                    'components.data.sql_executor.errors.empty_query')
                self.status = error_message
                raise ValueError(error_message)

            # Safety check for destructive operations
            if self.safe_mode and self._is_destructive_query():
                error_message = i18n.t(
                    'components.data.sql_executor.errors.destructive_query_blocked')
                self.status = error_message
                raise ValueError(error_message)

            # Get database connection
            connection = self._get_database_connection()

            try:
                # Execute query
                if self.database_type == "sqlite":
                    df = pd.read_sql_query(self.sql_query, connection)
                else:
                    # For other database types, use pandas with SQLAlchemy
                    df = pd.read_sql_query(self.sql_query, connection)

                # Limit rows if specified
                if self.limit_rows > 0:
                    df = df.head(self.limit_rows)

                if df.empty:
                    self.status = i18n.t(
                        'components.data.sql_executor.warnings.no_results')
                    return []

                # Convert DataFrame to Data objects
                result = []
                for index, row in df.iterrows():
                    row_dict = row.to_dict()

                    # Add row index
                    row_dict["_row_index"] = index

                    # Create text representation
                    if self.return_only_text:
                        text_content = " | ".join(
                            [f"{k}: {v}" for k, v in row_dict.items()])
                    else:
                        text_content = str(row_dict)

                    row_dict["text"] = text_content
                    result.append(Data(data=row_dict, text_key=self.text_key))

                success_message = i18n.t('components.data.sql_executor.success.query_executed',
                                         rows=len(result), operation=self.operation_type.upper())
                self.status = success_message
                return result

            finally:
                if connection:
                    connection.close()

        except Exception as e:
            error_message = i18n.t(
                'components.data.sql_executor.errors.execution_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def execute_sql_dataframe(self) -> DataFrame:
        """Execute SQL query and return results as DataFrame."""
        try:
            if not self.sql_query.strip():
                error_message = i18n.t(
                    'components.data.sql_executor.errors.empty_query')
                raise ValueError(error_message)

            if self.safe_mode and self._is_destructive_query():
                error_message = i18n.t(
                    'components.data.sql_executor.errors.destructive_query_blocked')
                raise ValueError(error_message)

            connection = self._get_database_connection()

            try:
                df = pd.read_sql_query(self.sql_query, connection)

                if self.limit_rows > 0:
                    df = df.head(self.limit_rows)

                return DataFrame(data=df)

            finally:
                if connection:
                    connection.close()

        except Exception as e:
            error_message = i18n.t(
                'components.data.sql_executor.errors.dataframe_error', error=str(e))
            raise ValueError(error_message) from e

    def get_execution_info(self) -> Data:
        """Get information about the SQL execution."""
        try:
            connection = self._get_database_connection()

            try:
                # Get basic database info
                info = {
                    "database_type": self.database_type,
                    "query": self.sql_query,
                    "operation_type": self.operation_type,
                    "safe_mode": self.safe_mode,
                    "limit_rows": self.limit_rows,
                }

                # Add database-specific info
                if self.database_type == "sqlite":
                    cursor = connection.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall()]
                    info["available_tables"] = tables
                    info["database_path"] = self.database_path
                else:
                    info["database_url"] = self.database_url

                return Data(data=info, text_key="query")

            finally:
                if connection:
                    connection.close()

        except Exception as e:
            error_message = i18n.t(
                'components.data.sql_executor.errors.info_error', error=str(e))
            raise ValueError(error_message) from e

    def _get_database_connection(self):
        """Get database connection based on database type."""
        if self.database_type == "sqlite":
            if not self.database_path:
                error_message = i18n.t(
                    'components.data.sql_executor.errors.missing_database_path')
                raise ValueError(error_message)

            # Check if database file exists for SQLite
            db_path = Path(self.database_path)
            if not db_path.exists():
                error_message = i18n.t(
                    'components.data.sql_executor.errors.database_not_found', path=self.database_path)
                raise ValueError(error_message)

            return sqlite3.connect(self.database_path)

        else:
            if not self.database_url:
                error_message = i18n.t(
                    'components.data.sql_executor.errors.missing_database_url')
                raise ValueError(error_message)

            try:
                from sqlalchemy import create_engine
                engine = create_engine(self.database_url)
                return engine.connect()
            except ImportError:
                error_message = i18n.t(
                    'components.data.sql_executor.errors.sqlalchemy_required')
                raise ValueError(error_message)

    def _is_destructive_query(self) -> bool:
        """Check if the query contains potentially destructive operations."""
        query_upper = self.sql_query.upper().strip()
        destructive_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT',
            'ALTER', 'CREATE', 'REPLACE', 'MERGE'
        ]

        # Check if query starts with destructive keywords
        for keyword in destructive_keywords:
            if query_upper.startswith(keyword):
                return True

        return False
