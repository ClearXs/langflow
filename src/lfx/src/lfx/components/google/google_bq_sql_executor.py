import i18n
import json
import re
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from lfx.custom import Component
from lfx.io import BoolInput, FileInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame


class BigQueryExecutorComponent(Component):
    display_name = "BigQuery"
    description = i18n.t(
        'components.google.google_bq_sql_executor.description')
    name = "BigQueryExecutor"
    icon = "Google"
    beta: bool = True

    inputs = [
        FileInput(
            name="service_account_json_file",
            display_name=i18n.t(
                'components.google.google_bq_sql_executor.service_account_json_file.display_name'),
            info=i18n.t(
                'components.google.google_bq_sql_executor.service_account_json_file.info'),
            file_types=["json"],
            required=True,
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.google.google_bq_sql_executor.query.display_name'),
            info=i18n.t('components.google.google_bq_sql_executor.query.info'),
            required=True,
            tool_mode=True,
        ),
        BoolInput(
            name="clean_query",
            display_name=i18n.t(
                'components.google.google_bq_sql_executor.clean_query.display_name'),
            info=i18n.t(
                'components.google.google_bq_sql_executor.clean_query.info'),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_bq_sql_executor.outputs.query_results.display_name'),
            name="query_results",
            method="execute_sql"
        ),
    ]

    def _clean_sql_query(self, query: str) -> str:
        """Clean SQL query by removing surrounding quotes and whitespace.

        Also extracts SQL statements from text that might contain other content.

        Args:
            query: The SQL query to clean

        Returns:
            The cleaned SQL query
        """
        logger.debug(i18n.t('components.google.google_bq_sql_executor.logs.cleaning_query',
                            length=len(query)))

        # First, try to extract SQL from code blocks
        sql_pattern = r"```(?:sql)?\s*([\s\S]*?)\s*```"
        sql_matches = re.findall(sql_pattern, query, re.IGNORECASE)

        if sql_matches:
            # If we found SQL in code blocks, use the first match
            query = sql_matches[0]
            logger.debug(i18n.t(
                'components.google.google_bq_sql_executor.logs.extracted_from_code_block'))
        else:
            # If no code block, try to find SQL statements
            # Look for common SQL keywords at the start of lines
            sql_keywords = r"(?i)(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|MERGE)"
            lines = query.split("\n")
            sql_lines = []
            in_sql = False

            for _line in lines:
                line = _line.strip()
                if re.match(sql_keywords, line):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                if line.endswith(";"):
                    in_sql = False

            if sql_lines:
                query = "\n".join(sql_lines)
                logger.debug(i18n.t(
                    'components.google.google_bq_sql_executor.logs.extracted_sql_statements'))

        # Remove any backticks that might be at the start or end
        query = query.strip("`")

        # Then remove surrounding quotes (single or double) if they exist
        query = query.strip()
        if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
            query = query[1:-1]
            logger.debug(
                i18n.t('components.google.google_bq_sql_executor.logs.removed_quotes'))

        # Finally, clean up any remaining whitespace and ensure no backticks remain
        query = query.strip()
        # Remove any remaining backticks, but preserve them if they're part of a table/column name
        # This regex will remove backticks that are not part of a valid identifier
        cleaned_query = re.sub(
            r"`(?![a-zA-Z0-9_])|(?<![a-zA-Z0-9_])`", "", query)

        logger.debug(i18n.t('components.google.google_bq_sql_executor.logs.query_cleaned',
                            original_length=len(query),
                            cleaned_length=len(cleaned_query)))

        return cleaned_query

    def execute_sql(self) -> DataFrame:
        """Execute SQL query on Google BigQuery.

        Returns:
            DataFrame: Query results as a DataFrame.

        Raises:
            ValueError: If credentials are invalid or query execution fails.
        """
        logger.info(
            i18n.t('components.google.google_bq_sql_executor.logs.executing_query'))

        try:
            # First try to read the file
            try:
                logger.debug(
                    i18n.t('components.google.google_bq_sql_executor.logs.reading_credentials'))
                service_account_path = Path(self.service_account_json_file)

                with service_account_path.open() as f:
                    credentials_json = json.load(f)
                    project_id = credentials_json.get("project_id")

                    if not project_id:
                        error_msg = i18n.t(
                            'components.google.google_bq_sql_executor.errors.no_project_id')
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                logger.debug(i18n.t('components.google.google_bq_sql_executor.logs.credentials_read',
                                    project_id=project_id))

            except FileNotFoundError as e:
                error_msg = i18n.t('components.google.google_bq_sql_executor.errors.file_not_found',
                                   error=str(e))
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            except json.JSONDecodeError as e:
                error_msg = i18n.t(
                    'components.google.google_bq_sql_executor.errors.invalid_json')
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            # Then try to load credentials
            try:
                logger.debug(
                    i18n.t('components.google.google_bq_sql_executor.logs.loading_credentials'))
                credentials = Credentials.from_service_account_file(
                    self.service_account_json_file)
                logger.debug(
                    i18n.t('components.google.google_bq_sql_executor.logs.credentials_loaded'))
            except Exception as e:
                error_msg = i18n.t('components.google.google_bq_sql_executor.errors.credentials_load_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.google.google_bq_sql_executor.errors.execution_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        try:
            logger.debug(i18n.t('components.google.google_bq_sql_executor.logs.creating_client',
                                project_id=project_id))
            client = bigquery.Client(
                credentials=credentials, project=project_id)
            logger.debug(
                i18n.t('components.google.google_bq_sql_executor.logs.client_created'))

            # Check for empty or whitespace-only query before cleaning
            if not str(self.query).strip():
                error_msg = i18n.t(
                    'components.google.google_bq_sql_executor.errors.empty_query')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Always clean the query if it contains code block markers, quotes, or if clean_query is enabled
            should_clean = "```" in str(self.query) or '"' in str(
                self.query) or "'" in str(self.query) or self.clean_query

            if should_clean:
                logger.debug(
                    i18n.t('components.google.google_bq_sql_executor.logs.cleaning_enabled'))
                sql_query = self._clean_sql_query(str(self.query))
            else:
                # At minimum, strip whitespace
                sql_query = str(self.query).strip()
                logger.debug(
                    i18n.t('components.google.google_bq_sql_executor.logs.cleaning_skipped'))

            logger.info(i18n.t(
                'components.google.google_bq_sql_executor.logs.executing_query_on_bigquery'))
            logger.debug(i18n.t('components.google.google_bq_sql_executor.logs.query_preview',
                                preview=sql_query[:200] + ("..." if len(sql_query) > 200 else "")))

            query_job = client.query(sql_query)
            results = query_job.result()
            output_dict = [dict(row) for row in results]

            logger.info(i18n.t('components.google.google_bq_sql_executor.logs.query_executed',
                               rows=len(output_dict)))

        except RefreshError as e:
            error_msg = i18n.t(
                'components.google.google_bq_sql_executor.errors.auth_refresh_failed')
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t('components.google.google_bq_sql_executor.errors.query_execution_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        df = DataFrame(output_dict)
        self.status = df
        return df
