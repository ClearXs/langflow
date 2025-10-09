import json
import urllib
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

import i18n
import requests
from langchain_core.tools import StructuredTool, Tool
from pydantic import BaseModel, Field, create_model

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.io import DictInput, IntInput, SecretStrInput, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.table import EditMode


class AstraDBCQLToolComponent(LCToolComponent):
    display_name: str = i18n.t('components.datastax.astradb_cql.display_name')
    description: str = i18n.t('components.datastax.astradb_cql.description')
    documentation: str = "https://docs.langflow.org/Components/components-tools#astra-db-cql-tool"
    icon: str = "AstraDB"

    inputs = [
        StrInput(
            name="tool_name",
            display_name=i18n.t(
                'components.datastax.astradb_cql.tool_name.display_name'),
            info=i18n.t('components.datastax.astradb_cql.tool_name.info'),
            required=True
        ),
        StrInput(
            name="tool_description",
            display_name=i18n.t(
                'components.datastax.astradb_cql.tool_description.display_name'),
            info=i18n.t(
                'components.datastax.astradb_cql.tool_description.info'),
            required=True,
        ),
        StrInput(
            name="keyspace",
            display_name=i18n.t(
                'components.datastax.astradb_cql.keyspace.display_name'),
            value="default_keyspace",
            info=i18n.t('components.datastax.astradb_cql.keyspace.info'),
            required=True,
            advanced=True,
        ),
        StrInput(
            name="table_name",
            display_name=i18n.t(
                'components.datastax.astradb_cql.table_name.display_name'),
            info=i18n.t('components.datastax.astradb_cql.table_name.info'),
            required=True,
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.astradb_cql.token.display_name'),
            info=i18n.t('components.datastax.astradb_cql.token.info'),
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
        ),
        StrInput(
            name="api_endpoint",
            display_name=i18n.t(
                'components.datastax.astradb_cql.api_endpoint.display_name'),
            info=i18n.t('components.datastax.astradb_cql.api_endpoint.info'),
            value="ASTRA_DB_API_ENDPOINT",
            required=True,
        ),
        StrInput(
            name="projection_fields",
            display_name=i18n.t(
                'components.datastax.astradb_cql.projection_fields.display_name'),
            info=i18n.t(
                'components.datastax.astradb_cql.projection_fields.info'),
            required=True,
            value="*",
            advanced=True,
        ),
        TableInput(
            name="tools_params",
            display_name=i18n.t(
                'components.datastax.astradb_cql.tools_params.display_name'),
            info=i18n.t('components.datastax.astradb_cql.tools_params.info'),
            required=False,
            table_schema=[
                {
                    "name": "name",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.name.description'),
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "field_name",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.field_name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.field_name.description'),
                    "default": "",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.description.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.description.description'),
                    "default": "description of tool parameter",
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "mandatory",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.mandatory.display_name'),
                    "type": "boolean",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.mandatory.description'),
                    "options": ["True", "False"],
                    "default": "False",
                },
                {
                    "name": "is_timestamp",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.is_timestamp.display_name'),
                    "type": "boolean",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.is_timestamp.description'),
                    "options": ["True", "False"],
                    "default": "False",
                },
                {
                    "name": "operator",
                    "display_name": i18n.t('components.datastax.astradb_cql.tools_params.schema.operator.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_cql.tools_params.schema.operator.description'),
                    "default": "$eq",
                    "options": ["$gt", "$gte", "$lt", "$lte", "$eq", "$ne", "$in", "$nin", "$exists", "$all", "$size"],
                    "edit_mode": EditMode.INLINE,
                },
            ],
            value=[],
        ),
        DictInput(
            name="partition_keys",
            display_name=i18n.t(
                'components.datastax.astradb_cql.partition_keys.display_name'),
            is_list=True,
            info=i18n.t('components.datastax.astradb_cql.partition_keys.info'),
            required=False,
            advanced=True,
        ),
        DictInput(
            name="clustering_keys",
            display_name=i18n.t(
                'components.datastax.astradb_cql.clustering_keys.display_name'),
            is_list=True,
            info=i18n.t(
                'components.datastax.astradb_cql.clustering_keys.info'),
            required=False,
            advanced=True,
        ),
        DictInput(
            name="static_filters",
            display_name=i18n.t(
                'components.datastax.astradb_cql.static_filters.display_name'),
            is_list=True,
            advanced=True,
            info=i18n.t('components.datastax.astradb_cql.static_filters.info'),
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.datastax.astradb_cql.number_of_results.display_name'),
            info=i18n.t(
                'components.datastax.astradb_cql.number_of_results.info'),
            advanced=True,
            value=5,
        ),
    ]

    def parse_timestamp(self, timestamp_str: str) -> str:
        """Parse a timestamp string into Astra DB REST API format.

        Args:
            timestamp_str (str): Input timestamp string

        Returns:
            str: Formatted timestamp string in YYYY-MM-DDTHH:MI:SS.000Z format

        Raises:
            ValueError: If the timestamp cannot be parsed
        """
        logger.debug(i18n.t('components.datastax.astradb_cql.logs.parsing_timestamp',
                            timestamp=timestamp_str))

        # Common datetime formats to try
        formats = [
            "%Y-%m-%d",  # 2024-03-21
            "%Y-%m-%dT%H:%M:%S",  # 2024-03-21T15:30:00
            "%Y-%m-%dT%H:%M:%S%z",  # 2024-03-21T15:30:00+0000
            "%Y-%m-%d %H:%M:%S",  # 2024-03-21 15:30:00
            "%d/%m/%Y",  # 21/03/2024
            "%Y/%m/%d",  # 2024/03/21
        ]

        for fmt in formats:
            try:
                # Parse the date string
                date_obj = datetime.strptime(timestamp_str, fmt).astimezone()

                # If the parsed date has no timezone info, assume UTC
                if date_obj.tzinfo is None:
                    date_obj = date_obj.replace(tzinfo=timezone.utc)

                # Convert to UTC and format
                utc_date = date_obj.astimezone(timezone.utc)
                formatted = utc_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                logger.debug(i18n.t('components.datastax.astradb_cql.logs.timestamp_parsed',
                                    formatted=formatted))
                return formatted
            except ValueError:
                continue

        error_msg = i18n.t('components.datastax.astradb_cql.errors.timestamp_parse_failed',
                           timestamp=timestamp_str)
        logger.error(error_msg)
        raise ValueError(error_msg)

    def astra_rest(self, args):
        logger.info(i18n.t('components.datastax.astradb_cql.logs.making_request',
                           table=self.table_name,
                           keyspace=self.keyspace))

        headers = {"Accept": "application/json",
                   "X-Cassandra-Token": f"{self.token}"}
        astra_url = f"{self.api_endpoint}/api/rest/v2/keyspaces/{self.keyspace}/{self.table_name}/"
        where = {}

        logger.debug(i18n.t('components.datastax.astradb_cql.logs.processing_params',
                            count=len(self.tools_params)))

        for param in self.tools_params:
            field_name = param["field_name"] if param["field_name"] else param["name"]
            field_value = None

            if field_name in self.static_filters:
                field_value = self.static_filters[field_name]
                logger.debug(i18n.t('components.datastax.astradb_cql.logs.using_static_filter',
                                    field=field_name))
            elif param["name"] in args:
                field_value = args[param["name"]]
                logger.debug(i18n.t('components.datastax.astradb_cql.logs.using_arg_value',
                                    param=param["name"]))

            if field_value is None:
                continue

            if param["is_timestamp"] == True:  # noqa: E712
                try:
                    field_value = self.parse_timestamp(field_value)
                except ValueError as e:
                    error_msg = i18n.t('components.datastax.astradb_cql.errors.timestamp_error',
                                       error=str(e))
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e

            if param["operator"] == "$exists":
                where[field_name] = {
                    **where.get(field_name, {}), param["operator"]: True}
            elif param["operator"] in ["$in", "$nin", "$all"]:
                where[field_name] = {
                    **where.get(field_name, {}),
                    param["operator"]: field_value.split(",") if isinstance(field_value, str) else field_value,
                }
            else:
                where[field_name] = {
                    **where.get(field_name, {}), param["operator"]: field_value}

        url = f"{astra_url}?page-size={self.number_of_results}"
        url += f"&where={json.dumps(where)}"

        if self.projection_fields != "*":
            url += f"&fields={urllib.parse.quote(self.projection_fields.replace(' ', ''))}"

        logger.debug(i18n.t('components.datastax.astradb_cql.logs.request_url',
                            url=url))

        res = requests.request("GET", url=url, headers=headers, timeout=10)

        if int(res.status_code) >= HTTPStatus.BAD_REQUEST:
            error_msg = i18n.t('components.datastax.astradb_cql.errors.request_failed',
                               tool_name=self.tool_name,
                               response=res.text)
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            res_data = res.json()
            result_count = len(res_data["data"])
            logger.info(i18n.t('components.datastax.astradb_cql.logs.request_successful',
                               count=result_count))
            return res_data["data"]
        except ValueError:
            logger.warning(i18n.t('components.datastax.astradb_cql.logs.no_json_response',
                                  status_code=res.status_code))
            return res.status_code

    def create_args_schema(self) -> dict[str, BaseModel]:
        logger.debug(
            i18n.t('components.datastax.astradb_cql.logs.creating_args_schema'))
        args: dict[str, tuple[Any, Field]] = {}

        for param in self.tools_params:
            field_name = param["field_name"] if param["field_name"] else param["name"]
            if field_name not in self.static_filters:
                if param["mandatory"]:
                    args[param["name"]] = (str, Field(
                        description=param["description"]))
                else:
                    args[param["name"]] = (str | None, Field(
                        description=param["description"], default=None))

        model = create_model("ToolInput", **args, __base__=BaseModel)
        logger.debug(i18n.t('components.datastax.astradb_cql.logs.args_schema_created',
                            field_count=len(args)))
        return {"ToolInput": model}

    def build_tool(self) -> Tool:
        """Builds a Astra DB CQL Table tool.

        Returns:
            Tool: The built Astra DB CQL tool.
        """
        logger.info(i18n.t('components.datastax.astradb_cql.logs.building_tool',
                           tool_name=self.tool_name))

        schema_dict = self.create_args_schema()
        tool = StructuredTool.from_function(
            name=self.tool_name,
            args_schema=schema_dict["ToolInput"],
            description=self.tool_description,
            func=self.run_model,
            return_direct=False,
        )

        logger.info(i18n.t('components.datastax.astradb_cql.logs.tool_built',
                           tool_name=self.tool_name))
        return tool

    def projection_args(self, input_str: str) -> dict:
        logger.debug(i18n.t('components.datastax.astradb_cql.logs.parsing_projection',
                            input_str=input_str))
        elements = input_str.split(",")
        result = {}

        for element in elements:
            if element.startswith("!"):
                result[element[1:]] = False
            else:
                result[element] = True

        logger.debug(i18n.t('components.datastax.astradb_cql.logs.projection_parsed',
                            count=len(result)))
        return result

    def run_model(self, **args) -> Data | list[Data]:
        logger.info(i18n.t('components.datastax.astradb_cql.logs.running_tool',
                           tool_name=self.tool_name))

        results = self.astra_rest(args)
        data: list[Data] = []

        if isinstance(results, list):
            data = [Data(data=doc) for doc in results]
            logger.info(i18n.t('components.datastax.astradb_cql.logs.tool_completed',
                               count=len(data)))
        else:
            logger.warning(
                i18n.t('components.datastax.astradb_cql.logs.no_results'))
            self.status = results
            return []

        self.status = data
        return data
