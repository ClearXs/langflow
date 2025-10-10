import os
from datetime import datetime, timezone
from typing import Any

import i18n
from astrapy import Collection, DataAPIClient, Database
from langchain_core.tools import StructuredTool, Tool
from pydantic import BaseModel, Field, create_model

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.io import BoolInput, DictInput, HandleInput, IntInput, SecretStrInput, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.table import EditMode


class AstraDBToolComponent(LCToolComponent):
    display_name: str = i18n.t('components.datastax.astradb_tool.display_name')
    description: str = i18n.t('components.datastax.astradb_tool.description')
    documentation: str = "https://docs.langflow.org/components-bundle-components"
    icon: str = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="tool_name",
            display_name=i18n.t(
                'components.datastax.astradb_tool.tool_name.display_name'),
            info=i18n.t('components.datastax.astradb_tool.tool_name.info'),
            required=True,
        ),
        StrInput(
            name="tool_description",
            display_name=i18n.t(
                'components.datastax.astradb_tool.tool_description.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.tool_description.info'),
            required=True,
        ),
        StrInput(
            name="keyspace",
            display_name=i18n.t(
                'components.datastax.astradb_tool.keyspace.display_name'),
            info=i18n.t('components.datastax.astradb_tool.keyspace.info'),
            value="default_keyspace",
            advanced=True,
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.datastax.astradb_tool.collection_name.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.collection_name.info'),
            required=True,
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.astradb_tool.token.display_name'),
            info=i18n.t('components.datastax.astradb_tool.token.info'),
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
        ),
        SecretStrInput(
            name="api_endpoint",
            display_name=i18n.t('components.datastax.astradb_tool.api_endpoint.display_name_enhanced'
                                if os.getenv("ASTRA_ENHANCED", "false").lower() == "true"
                                else 'components.datastax.astradb_tool.api_endpoint.display_name'),
            info=i18n.t('components.datastax.astradb_tool.api_endpoint.info'),
            value="ASTRA_DB_API_ENDPOINT",
            required=True,
        ),
        StrInput(
            name="projection_attributes",
            display_name=i18n.t(
                'components.datastax.astradb_tool.projection_attributes.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.projection_attributes.info'),
            required=True,
            value="*",
            advanced=True,
        ),
        TableInput(
            trigger_text=i18n.t(
                'components.inputs.input_mixin.open_table'),
            name="tools_params_v2",
            display_name=i18n.t(
                'components.datastax.astradb_tool.tools_params_v2.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.tools_params_v2.info'),
            required=False,
            table_schema=[
                {
                    "name": "name",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.name.description'),
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "attribute_name",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.attribute_name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.attribute_name.description'),
                    "default": "",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.description.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.description.description'),
                    "default": "description of field",
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "metadata",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.metadata.display_name'),
                    "type": "boolean",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.metadata.description'),
                    "options": ["True", "False"],
                    "default": "False",
                },
                {
                    "name": "mandatory",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.mandatory.display_name'),
                    "type": "boolean",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.mandatory.description'),
                    "options": ["True", "False"],
                    "default": "False",
                },
                {
                    "name": "is_timestamp",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.is_timestamp.display_name'),
                    "type": "boolean",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.is_timestamp.description'),
                    "options": ["True", "False"],
                    "default": "False",
                },
                {
                    "name": "operator",
                    "display_name": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.operator.display_name'),
                    "type": "str",
                    "description": i18n.t('components.datastax.astradb_tool.tools_params_v2.schema.operator.description'),
                    "default": "$eq",
                    "options": ["$gt", "$gte", "$lt", "$lte", "$eq", "$ne", "$in", "$nin", "$exists", "$all", "$size"],
                    "edit_mode": EditMode.INLINE,
                },
            ],
            value=[],
        ),
        DictInput(
            name="tool_params",
            info=i18n.t('components.datastax.astradb_tool.tool_params.info'),
            display_name=i18n.t(
                'components.datastax.astradb_tool.tool_params.display_name'),
            is_list=True,
            advanced=True,
        ),
        DictInput(
            name="static_filters",
            info=i18n.t(
                'components.datastax.astradb_tool.static_filters.info'),
            display_name=i18n.t(
                'components.datastax.astradb_tool.static_filters.display_name'),
            advanced=True,
            is_list=True,
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.datastax.astradb_tool.number_of_results.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.number_of_results.info'),
            advanced=True,
            value=5,
        ),
        BoolInput(
            name="use_search_query",
            display_name=i18n.t(
                'components.datastax.astradb_tool.use_search_query.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.use_search_query.info'),
            advanced=False,
            value=False,
        ),
        BoolInput(
            name="use_vectorize",
            display_name=i18n.t(
                'components.datastax.astradb_tool.use_vectorize.display_name'),
            info=i18n.t('components.datastax.astradb_tool.use_vectorize.info'),
            advanced=False,
            value=False,
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.datastax.astradb_tool.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        StrInput(
            name="semantic_search_instruction",
            display_name=i18n.t(
                'components.datastax.astradb_tool.semantic_search_instruction.display_name'),
            info=i18n.t(
                'components.datastax.astradb_tool.semantic_search_instruction.info'),
            required=True,
            value="Search query to find relevant documents.",
            advanced=True,
        ),
    ]

    _cached_client: DataAPIClient | None = None
    _cached_db: Database | None = None
    _cached_collection: Collection | None = None

    def _build_collection(self):
        try:
            from astrapy.admin import parse_api_endpoint
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.astrapy_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.astradb_tool.errors.astrapy_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        if self._cached_collection:
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.using_cached_collection'))
            return self._cached_collection

        try:
            logger.info(i18n.t('components.datastax.astradb_tool.logs.building_collection',
                               collection=self.collection_name,
                               keyspace=self.keyspace))

            environment = parse_api_endpoint(self.api_endpoint).environment
            logger.debug(i18n.t('components.datastax.astradb_tool.logs.environment_detected',
                                environment=environment))

            cached_client = DataAPIClient(self.token, environment=environment)
            cached_db = cached_client.get_database(
                self.api_endpoint, keyspace=self.keyspace)
            self._cached_collection = cached_db.get_collection(
                self.collection_name)

            logger.info(
                i18n.t('components.datastax.astradb_tool.logs.collection_built'))
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_tool.errors.build_collection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
        else:
            return self._cached_collection

    def create_args_schema(self) -> dict[str, BaseModel]:
        """DEPRECATED: This method is deprecated. Please use create_args_schema_v2 instead.

        It is keep only for backward compatibility.
        """
        logger.warning(
            i18n.t('components.datastax.astradb_tool.logs.deprecated_method_warning'))
        args: dict[str, tuple[Any, Field] | list[str]] = {}

        for key in self.tool_params:
            if key.startswith("!"):  # Mandatory
                args[key[1:]] = (str, Field(description=self.tool_params[key]))
            else:  # Optional
                args[key] = (str | None, Field(
                    description=self.tool_params[key], default=None))

        if self.use_search_query:
            args["search_query"] = (
                str | None,
                Field(
                    description="Search query to find relevant documents.", default=None),
            )

        model = create_model("ToolInput", **args, __base__=BaseModel)
        logger.debug(i18n.t('components.datastax.astradb_tool.logs.args_schema_created_v1',
                            field_count=len(args)))
        return {"ToolInput": model}

    def create_args_schema_v2(self) -> dict[str, BaseModel]:
        """Create the tool input schema using the new tool parameters configuration."""
        logger.debug(
            i18n.t('components.datastax.astradb_tool.logs.creating_args_schema_v2'))
        args: dict[str, tuple[Any, Field] | list[str]] = {}

        for tool_param in self.tools_params_v2:
            if tool_param["mandatory"]:
                args[tool_param["name"]] = (str, Field(
                    description=tool_param["description"]))
            else:
                args[tool_param["name"]] = (str | None, Field(
                    description=tool_param["description"], default=None))

        if self.use_search_query:
            args["search_query"] = (
                str,
                Field(description=self.semantic_search_instruction),
            )

        model = create_model("ToolInput", **args, __base__=BaseModel)
        logger.debug(i18n.t('components.datastax.astradb_tool.logs.args_schema_created_v2',
                            field_count=len(args)))
        return {"ToolInput": model}

    def build_tool(self) -> Tool:
        """Builds an Astra DB Collection tool.

        Returns:
            Tool: The built Astra DB tool.
        """
        logger.info(i18n.t('components.datastax.astradb_tool.logs.building_tool',
                           tool_name=self.tool_name))

        schema_dict = self.create_args_schema() if len(
            self.tool_params.keys()) > 0 else self.create_args_schema_v2()

        tool = StructuredTool.from_function(
            name=self.tool_name,
            args_schema=schema_dict["ToolInput"],
            description=self.tool_description,
            func=self.run_model,
            return_direct=False,
        )

        success_msg = i18n.t(
            'components.datastax.astradb_tool.status.tool_created')
        self.status = success_msg
        logger.info(i18n.t('components.datastax.astradb_tool.logs.tool_built',
                           tool_name=self.tool_name))

        return tool

    def projection_args(self, input_str: str) -> dict | None:
        """Build the projection arguments for the Astra DB query."""
        logger.debug(i18n.t('components.datastax.astradb_tool.logs.building_projection',
                            input_str=input_str))

        elements = input_str.split(",")
        result = {}

        if elements == ["*"]:
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.projection_all'))
            return None

        # Force the projection to exclude the $vector field as it is not required by the tool
        result["$vector"] = False

        # Fields with ! as prefix should be removed from the projection
        for element in elements:
            if element.startswith("!"):
                result[element[1:]] = False
            else:
                result[element] = True

        logger.debug(i18n.t('components.datastax.astradb_tool.logs.projection_built',
                            field_count=len(result)))
        return result

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse a timestamp string into Astra DB REST API format.

        Args:
            timestamp_str (str): Input timestamp string

        Returns:
            datetime: Datetime object

        Raises:
            ValueError: If the timestamp cannot be parsed
        """
        logger.debug(i18n.t('components.datastax.astradb_tool.logs.parsing_timestamp',
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
                result = date_obj.astimezone(timezone.utc)
                logger.debug(i18n.t('components.datastax.astradb_tool.logs.timestamp_parsed',
                                    result=result.isoformat()))
                return result

            except ValueError:
                continue

        error_msg = i18n.t('components.datastax.astradb_tool.errors.timestamp_parse_failed',
                           timestamp=timestamp_str)
        logger.error(error_msg)
        raise ValueError(error_msg)

    def build_filter(self, args: dict, filter_settings: list) -> dict:
        """Build filter dictionary for Astra DB query.

        Args:
            args: Dictionary of arguments from the tool
            filter_settings: List of filter settings from tools_params_v2
        Returns:
            Dictionary containing the filter conditions
        """
        logger.debug(
            i18n.t('components.datastax.astradb_tool.logs.building_filter'))
        filters = {**self.static_filters}

        for key, value in args.items():
            # Skip search_query as it's handled separately
            if key == "search_query":
                continue

            filter_setting = next(
                (x for x in filter_settings if x["name"] == key), None)
            if filter_setting and value is not None:
                field_name = filter_setting["attribute_name"] if filter_setting["attribute_name"] else key
                filter_key = field_name if not filter_setting[
                    "metadata"] else f"metadata.{field_name}"

                if filter_setting["operator"] == "$exists":
                    filters[filter_key] = {
                        **filters.get(filter_key, {}), filter_setting["operator"]: True}
                elif filter_setting["operator"] in ["$in", "$nin", "$all"]:
                    filters[filter_key] = {
                        **filters.get(filter_key, {}),
                        filter_setting["operator"]: value.split(",") if isinstance(value, str) else value,
                    }
                elif filter_setting["is_timestamp"] == True:  # noqa: E712
                    try:
                        filters[filter_key] = {
                            **filters.get(filter_key, {}),
                            filter_setting["operator"]: self.parse_timestamp(value),
                        }
                    except ValueError as e:
                        error_msg = i18n.t('components.datastax.astradb_tool.errors.timestamp_error',
                                           error=str(e))
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                else:
                    filters[filter_key] = {
                        **filters.get(filter_key, {}), filter_setting["operator"]: value}

        logger.debug(i18n.t('components.datastax.astradb_tool.logs.filter_built',
                            filter_count=len(filters)))
        return filters

    def run_model(self, **args) -> Data | list[Data]:
        """Run the query to get the data from the Astra DB collection."""
        logger.info(i18n.t('components.datastax.astradb_tool.logs.running_tool',
                           tool_name=self.tool_name))

        collection = self._build_collection()
        sort = {}

        # Build filters using the new method
        filters = self.build_filter(args, self.tools_params_v2)

        # Build the vector search on
        if self.use_search_query and args.get("search_query") is not None and args["search_query"] != "":
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.using_semantic_search'))

            if self.use_vectorize:
                logger.debug(
                    i18n.t('components.datastax.astradb_tool.logs.using_vectorize'))
                sort["$vectorize"] = args["search_query"]
            else:
                if self.embedding is None:
                    error_msg = i18n.t(
                        'components.datastax.astradb_tool.errors.embedding_not_set')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(
                    i18n.t('components.datastax.astradb_tool.logs.generating_embedding'))
                embedding_query = self.embedding.embed_query(
                    args["search_query"])
                sort["$vector"] = embedding_query
            del args["search_query"]

        find_options = {
            "filter": filters,
            "limit": self.number_of_results,
            "sort": sort,
        }

        projection = self.projection_args(self.projection_attributes)
        if projection and len(projection) > 0:
            find_options["projection"] = projection
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.projection_added'))

        try:
            logger.debug(
                i18n.t('components.datastax.astradb_tool.logs.executing_query'))
            results = collection.find(**find_options)
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_tool.errors.query_failed',
                               tool_name=self.tool_name,
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        logger.info(i18n.t('components.datastax.astradb_tool.logs.tool_executed',
                           tool_name=self.tool_name))

        data: list[Data] = [Data(data=doc) for doc in results]
        logger.info(i18n.t('components.datastax.astradb_tool.logs.results_processed',
                           count=len(data)))

        self.status = data
        return data
