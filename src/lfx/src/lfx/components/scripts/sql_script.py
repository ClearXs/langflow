"""SQL Script Component for executing SQL statements on selected datasource."""

from typing import Any

import i18n
import pandas as pd
import sqlparse
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, MessageTextInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLSQLScriptComponent(Component):
    """Execute SQL scripts on selected datasource with transaction support."""

    display_name = i18n.t("components.scripts.sql_script.display_name")
    description = i18n.t("components.scripts.sql_script.description")
    icon = "database"
    name = "ETLSQLScript"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.scripts.sql_script.datasource_selector.display_name"),
            info=i18n.t("components.scripts.sql_script.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],  # Will be loaded dynamically
            real_time_refresh=True,
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        MultilineInput(
            name="sql_script",
            display_name=i18n.t("components.scripts.sql_script.sql_script.display_name"),
            info=i18n.t("components.scripts.sql_script.sql_script.info"),
            required=True,
            placeholder="-- SQL Script\nCREATE TABLE ...\nINSERT INTO ...\nSELECT * FROM ...",
            advanced=False,
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t("components.scripts.sql_script.enable_transaction.display_name"),
            info=i18n.t("components.scripts.sql_script.enable_transaction.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="statement_separator",
            display_name=i18n.t("components.scripts.sql_script.statement_separator.display_name"),
            info=i18n.t("components.scripts.sql_script.statement_separator.info"),
            value=";",
            advanced=True,
        ),
        BoolInput(
            name="continue_on_error",
            display_name=i18n.t("components.scripts.sql_script.continue_on_error.display_name"),
            info=i18n.t("components.scripts.sql_script.continue_on_error.info"),
            value=False,
            advanced=True,
        ),
        TableInput(
            name="execution_results",
            display_name=i18n.t("components.scripts.sql_script.execution_results.display_name"),
            info=i18n.t("components.scripts.sql_script.execution_results.info"),
            table_schema=[
                {
                    "name": "statement_index",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.statement_index"),
                    "type": "int",
                    "disable_edit": True,
                },
                {
                    "name": "statement_type",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.statement_type"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "rows_affected",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.rows_affected"),
                    "type": "int",
                    "disable_edit": True,
                },
                {
                    "name": "execution_status",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.status"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "error_message",
                    "display_name": i18n.t("components.scripts.sql_script.execution_results.error"),
                    "type": "str",
                    "disable_edit": True,
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "execute_script",
                        "label": i18n.t("components.scripts.sql_script.execution_results.execute_button"),
                        "icon": "Play",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="execution_summary",
            display_name=i18n.t("components.scripts.sql_script.outputs.execution_summary"),
            method="execute_sql_script",
        ),
        Output(
            name="query_results",
            display_name=i18n.t("components.scripts.sql_script.outputs.query_results"),
            method="get_query_results",
        ),
        Output(
            name="total_rows_affected",
            display_name=i18n.t("components.scripts.sql_script.outputs.total_rows_affected"),
            method="get_total_rows_affected",
        ),
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates based on field changes and action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(
            f"[SQLScript] update_build_config called - field_name: {field_name}, "
            f"field_value type: {type(field_value).__name__}, action: {action}"
        )

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        # Load datasources on initial load or refresh
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"[SQLScript] Loading datasources (field_name={field_name})")
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources")

                    if response.status_code == 200:
                        datasources = response.json()
                        logger.debug(f"[SQLScript] Loaded {len(datasources)} datasources from API")

                        options = []
                        options_metadata = []

                        for ds in datasources:
                            display_name = f"{ds['name']} ({ds['type']})"
                            options.append(display_name)
                            options_metadata.append({"id": ds["id"], "name": ds["name"], "type": ds["type"]})

                        build_config["datasource_selector"]["options"] = options
                        build_config["datasource_selector"]["options_metadata"] = options_metadata
                        logger.debug(f"[SQLScript] Set datasource_selector options: {options}")
                    else:
                        logger.warning(f"[SQLScript] Failed to load datasources, status: {response.status_code}")
            except Exception as e:
                logger.error(f"[SQLScript] Error loading datasources: {e}")

        # Handle execute script button click
        if field_name == "execution_results" and action == "execute_script":
            logger.info("[SQLScript] Execute script triggered by action button")

            try:
                current_sql = build_config.get("sql_script", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("[SQLScript] No SQL script provided")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_script")
                    return build_config

                if not current_datasource:
                    logger.warning("[SQLScript] No datasource selected")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_datasource")
                    return build_config

                # Get datasource ID from metadata
                datasource_id = self._get_datasource_id_from_metadata(
                    current_datasource, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if not datasource_id:
                    logger.error(f"[SQLScript] Cannot find datasource ID for: {current_datasource}")
                    self.status = i18n.t("components.scripts.sql_script.errors.no_datasource")
                    return build_config

                # Execute the script
                logger.info("[SQLScript] Starting script execution...")
                self.status = i18n.t("components.scripts.sql_script.status.connecting")

                # Get other configuration values
                enable_transaction = build_config.get("enable_transaction", {}).get("value", True)
                continue_on_error = build_config.get("continue_on_error", {}).get("value", False)
                statement_separator = build_config.get("statement_separator", {}).get("value", ";")

                # Execute script and get results
                results = self._execute_script_preview(
                    datasource_id=datasource_id,
                    sql_script=current_sql,
                    enable_transaction=enable_transaction,
                    continue_on_error=continue_on_error,
                    statement_separator=statement_separator,
                )

                # Update execution results table
                build_config["execution_results"]["value"] = results

                success_count = sum(1 for r in results if r["execution_status"] == "success")
                total_count = len(results)

                self.status = self._format_i18n(
                    "components.scripts.sql_script.status.success", success=success_count, total=total_count
                )
                logger.info(f"[SQLScript] Script execution completed: {success_count}/{total_count} successful")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[SQLScript] Script execution failed: {error_msg}")
                self.status = self._format_i18n(
                    "components.scripts.sql_script.errors.execution_failed", error=error_msg
                )

        return build_config

    def _get_datasource_id_from_metadata(self, display_name: str, options_metadata: list[dict]) -> str | None:
        """Get datasource ID from metadata based on display name."""
        for metadata in options_metadata:
            meta_display_name = f"{metadata.get('name')} ({metadata.get('type')})"
            if meta_display_name == display_name:
                datasource_id = metadata.get("id")
                logger.debug(f"[SQLScript] Found datasource ID '{datasource_id}' for display name '{display_name}'")
                return datasource_id

        logger.warning(f"[SQLScript] No metadata found for display name: {display_name}")
        return None

    def _format_i18n(self, key: str, **kwargs) -> str:
        """Format i18n text with parameter substitution."""
        text = i18n.t(key)
        for param_key, param_value in kwargs.items():
            text = text.replace(f"{{{param_key}}}", str(param_value))
        return text

    def _get_connection_string(self, datasource_id: str) -> str:
        """Get connection string for datasource."""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                if response.status_code != 200:
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError("Connection string is empty")

                return connection_string
        except Exception as e:
            logger.error(f"[SQLScript] Error getting connection string: {e}")
            raise

    def _parse_sql_statements(self, sql_script: str, separator: str = ";") -> list[str]:
        """Parse SQL script into individual statements.

        Args:
            sql_script: The SQL script to parse
            separator: Statement separator (default: semicolon)

        Returns:
            List of SQL statements
        """
        try:
            # Use sqlparse to properly handle SQL
            parsed = sqlparse.parse(sql_script)
            statements = []

            for statement in parsed:
                # Remove comments and whitespace
                sql = statement.value.strip()
                if sql and not sql.startswith("--"):
                    statements.append(sql)

            logger.debug(f"[SQLScript] Parsed {len(statements)} statements from script")
            return statements

        except Exception as e:
            logger.error(f"[SQLScript] Failed to parse SQL script: {e}")
            raise ValueError(self._format_i18n("components.scripts.sql_script.errors.parse_failed", error=str(e)))

    def _classify_statement_type(self, statement: str) -> str:
        """Classify SQL statement type.

        Args:
            statement: SQL statement

        Returns:
            Statement type: DDL, DML, DQL, or OTHER
        """
        statement_upper = statement.strip().upper()

        # DDL statements
        if any(statement_upper.startswith(kw) for kw in ["CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"]):
            return "DDL"

        # DML statements
        if any(statement_upper.startswith(kw) for kw in ["INSERT", "UPDATE", "DELETE", "MERGE"]):
            return "DML"

        # DQL statements
        if statement_upper.startswith("SELECT"):
            return "DQL"

        # Other (e.g., SET, USE, etc.)
        return "OTHER"

    def _execute_single_statement(
        self, connection, statement: str, index: int, total: int
    ) -> dict[str, str | int | list]:
        """Execute a single SQL statement.

        Args:
            connection: Database connection
            statement: SQL statement to execute
            index: Statement index (1-based)
            total: Total number of statements

        Returns:
            Execution result dictionary with query_data for SELECT statements
        """
        try:
            stmt_type = self._classify_statement_type(statement)
            logger.debug(f"[SQLScript] Executing statement {index}/{total} ({stmt_type}): {statement[:50]}...")

            self.status = self._format_i18n("components.scripts.sql_script.status.executing", index=index, total=total)

            result = connection.execute(text(statement))

            # Get rows affected
            rows_affected = result.rowcount if hasattr(result, "rowcount") else 0

            # For SELECT queries, fetch the actual data
            query_data = []
            if stmt_type == "DQL":
                try:
                    # Fetch all rows from SELECT query
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    query_data = df.to_dict("records")  # Convert to list of dicts
                    logger.debug(f"[SQLScript] Fetched {len(query_data)} rows from SELECT query")
                except Exception as fetch_error:
                    logger.warning(f"[SQLScript] Could not fetch query results: {fetch_error}")
                    query_data = []

            return {
                "statement_index": index,
                "statement_type": stmt_type,
                "rows_affected": rows_affected,
                "execution_status": "success",
                "error_message": "",
                "query_data": query_data,  # Add query results
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[SQLScript] Statement {index} failed: {error_msg}")

            return {
                "statement_index": index,
                "statement_type": self._classify_statement_type(statement),
                "rows_affected": 0,
                "execution_status": "failed",
                "error_message": error_msg,
                "query_data": [],
            }

    def _execute_script_preview(
        self,
        datasource_id: str,
        sql_script: str,
        enable_transaction: bool,
        continue_on_error: bool,
        statement_separator: str,
    ) -> list[dict]:
        """Execute SQL script and return results for preview.

        This is called during configuration to preview execution results.
        """
        try:
            # Parse statements
            self.status = i18n.t("components.scripts.sql_script.status.parsing")
            statements = self._parse_sql_statements(sql_script, statement_separator)

            if not statements:
                logger.warning("[SQLScript] No statements to execute")
                return []

            # Get connection
            connection_string = self._get_connection_string(datasource_id)
            engine = create_engine(connection_string, poolclass=NullPool)

            results = []

            try:
                with engine.connect() as connection:
                    # Start transaction if enabled
                    if enable_transaction:
                        trans = connection.begin()

                    try:
                        # Execute each statement
                        for idx, statement in enumerate(statements, start=1):
                            result = self._execute_single_statement(connection, statement, idx, len(statements))
                            results.append(result)

                            # If error and not continuing, break
                            if result["execution_status"] == "failed" and not continue_on_error:
                                if enable_transaction:
                                    trans.rollback()
                                    logger.info("[SQLScript] Transaction rolled back due to error")
                                break

                        # Commit transaction if all successful
                        if enable_transaction:
                            if all(r["execution_status"] == "success" for r in results):
                                trans.commit()
                                logger.info("[SQLScript] Transaction committed successfully")
                            else:
                                trans.rollback()
                                logger.info("[SQLScript] Transaction rolled back due to errors")

                    except Exception as e:
                        if enable_transaction:
                            trans.rollback()
                        logger.error(f"[SQLScript] Script execution failed: {e}")
                        raise

            finally:
                engine.dispose()

            return results

        except Exception as e:
            logger.error(f"[SQLScript] Preview execution failed: {e}")
            raise

    def _get_datasource_id(self) -> str:
        """Get datasource ID from selected display name."""
        if not self.datasource_selector:
            raise ValueError("No datasource selected")

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources")
                if response.status_code == 200:
                    datasources = response.json()

                    for ds in datasources:
                        display_name = f"{ds['name']} ({ds['type']})"
                        if display_name == self.datasource_selector:
                            datasource_id = ds["id"]
                            logger.debug(
                                f"[SQLScript] Found datasource ID '{datasource_id}' for '{self.datasource_selector}'"
                            )
                            return datasource_id

                    logger.warning(
                        f"[SQLScript] Display name '{self.datasource_selector}' not found, trying as direct ID"
                    )
                    return self.datasource_selector

                logger.error(f"[SQLScript] Failed to load datasources from API, status: {response.status_code}")
                raise ValueError(f"Failed to load datasources: HTTP {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"[SQLScript] HTTP error when fetching datasources: {e}")
            raise ValueError(f"Failed to fetch datasources: {e}")

        except Exception as e:
            logger.error(f"[SQLScript] Unexpected error: {e}")
            raise ValueError(f"Cannot determine datasource ID: {e}")

    def execute_sql_script(self) -> Data:
        """Execute SQL script on selected datasource.

        Returns:
            Execution summary with all statement results
        """
        try:
            logger.info("[SQLScript] execute_sql_script called")
            self.status = i18n.t("components.scripts.sql_script.status.connecting")

            # Validate inputs
            if not self.datasource_selector or not self.sql_script:
                logger.warning("[SQLScript] Missing datasource or SQL script")
                raise ValueError(i18n.t("components.scripts.sql_script.errors.no_datasource"))

            # Get datasource ID
            datasource_id = self._get_datasource_id()
            logger.debug(f"[SQLScript] Using datasource ID: {datasource_id}")

            # Parse statements
            self.status = i18n.t("components.scripts.sql_script.status.parsing")
            statements = self._parse_sql_statements(self.sql_script, self.statement_separator)

            if not statements:
                logger.warning("[SQLScript] No statements to execute")
                return Data(
                    data={
                        "total_statements": 0,
                        "successful_statements": 0,
                        "failed_statements": 0,
                        "total_rows_affected": 0,
                        "results": [],
                    }
                )

            # Get connection
            connection_string = self._get_connection_string(datasource_id)
            engine = create_engine(connection_string, poolclass=NullPool)

            results = []
            total_rows_affected = 0

            try:
                with engine.connect() as connection:
                    # Start transaction if enabled
                    if self.enable_transaction:
                        trans = connection.begin()

                    try:
                        # Execute each statement
                        for idx, statement in enumerate(statements, start=1):
                            result = self._execute_single_statement(connection, statement, idx, len(statements))
                            results.append(result)

                            if result["execution_status"] == "success":
                                total_rows_affected += result["rows_affected"]

                            # If error and not continuing, break
                            if result["execution_status"] == "failed" and not self.continue_on_error:
                                if self.enable_transaction:
                                    trans.rollback()
                                    logger.info("[SQLScript] Transaction rolled back due to error")
                                break

                        # Commit transaction if enabled and all successful
                        if self.enable_transaction:
                            if all(r["execution_status"] == "success" for r in results):
                                self.status = i18n.t("components.scripts.sql_script.status.committing")
                                trans.commit()
                                logger.info("[SQLScript] Transaction committed successfully")
                            else:
                                trans.rollback()
                                logger.info("[SQLScript] Transaction rolled back due to errors")

                    except Exception as e:
                        if self.enable_transaction:
                            trans.rollback()
                        raise e

            finally:
                engine.dispose()

            # Build summary
            successful_count = sum(1 for r in results if r["execution_status"] == "success")
            failed_count = len(results) - successful_count

            summary_data = {
                "total_statements": len(statements),
                "successful_statements": successful_count,
                "failed_statements": failed_count,
                "total_rows_affected": total_rows_affected,
                "results": results,
            }

            self.status = self._format_i18n(
                "components.scripts.sql_script.status.success", success=successful_count, total=len(statements)
            )
            logger.info(f"[SQLScript] Execution completed: {successful_count}/{len(statements)} successful")

            return Data(data=summary_data)

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[SQLScript] execute_sql_script failed: {error_msg}")

            try:
                status_msg = i18n.t("components.scripts.sql_script.errors.execution_failed", error=error_msg)
            except Exception:
                status_msg = f"Script execution failed: {error_msg}"

            self.status = status_msg
            raise ValueError(status_msg) from e

    def get_total_rows_affected(self) -> Data:
        """Get total rows affected by the script execution.

        Returns:
            Data object with total rows affected count
        """
        try:
            summary = self.execute_sql_script()
            total_rows = summary.data.get("total_rows_affected", 0)

            return Data(data={"total_rows_affected": total_rows})

        except Exception as e:
            logger.error(f"[SQLScript] Failed to get total rows affected: {e}")
            return Data(data={"total_rows_affected": 0, "error": str(e)})

    def get_query_results(self) -> list[Data]:
        """Get query results from SELECT statements.

        Returns:
            List of Data objects containing query results from all SELECT statements
        """
        try:
            logger.info("[SQLScript] get_query_results called")
            summary = self.execute_sql_script()

            # Extract query data from all successful DQL statements
            all_query_data = []
            results = summary.data.get("results", [])

            for result in results:
                if result.get("statement_type") == "DQL" and result.get("execution_status") == "success":
                    query_data = result.get("query_data", [])
                    # Convert each row dict to a Data object
                    for row_dict in query_data:
                        all_query_data.append(Data(data=row_dict))

                    logger.debug(
                        f"[SQLScript] Statement {result.get('statement_index')}: "
                        f"Added {len(query_data)} rows to query results"
                    )

            logger.info(f"[SQLScript] Returning {len(all_query_data)} total query result rows")
            return all_query_data

        except Exception as e:
            logger.error(f"[SQLScript] Failed to get query results: {e}")
            return []
