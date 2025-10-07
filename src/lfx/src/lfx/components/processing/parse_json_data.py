import json
from json import JSONDecodeError
import i18n

import jq
from json_repair import repair_json

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, MessageTextInput
from lfx.io import Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.message import Message


class ParseJSONDataComponent(Component):
    display_name = i18n.t('components.processing.parse_json_data.display_name')
    description = i18n.t('components.processing.parse_json_data.description')
    icon = "braces"
    name = "ParseJSONData"
    legacy: bool = True
    replacement = ["processing.ParserComponent"]

    inputs = [
        HandleInput(
            name="input_value",
            display_name=i18n.t(
                'components.processing.parse_json_data.input_value.display_name'),
            info=i18n.t(
                'components.processing.parse_json_data.input_value.info'),
            required=True,
            input_types=["Message", "Data"],
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.processing.parse_json_data.query.display_name'),
            info=i18n.t('components.processing.parse_json_data.query.info'),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.parse_json_data.outputs.filtered_data.display_name'),
            name="filtered_data",
            method="filter_data"
        ),
    ]

    def _parse_data(self, input_value) -> str:
        """Parse input value to string format."""
        try:
            if isinstance(input_value, Message) and isinstance(input_value.text, str):
                return input_value.text
            if isinstance(input_value, Data):
                return json.dumps(input_value.data)
            return str(input_value)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_json_data.errors.data_parsing_failed', error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _repair_and_parse_json(self, json_str: str) -> dict | list:
        """Repair and parse JSON string."""
        try:
            # First try to parse as-is
            return json.loads(json_str)
        except JSONDecodeError:
            try:
                # Try to repair and parse
                repaired_json = repair_json(json_str)
                return json.loads(repaired_json)
            except JSONDecodeError as e:
                error_msg = i18n.t(
                    'components.processing.parse_json_data.errors.invalid_json', error=str(e))
                raise ValueError(error_msg) from e

    def filter_data(self) -> list[Data]:
        """Filter JSON data using JQ query."""
        try:
            to_filter = self.input_value

            if not to_filter:
                warning_msg = i18n.t(
                    'components.processing.parse_json_data.warnings.empty_input')
                self.status = warning_msg
                return []

            # Parse input data
            if isinstance(to_filter, list):
                parsed_items = []
                for i, item in enumerate(to_filter):
                    try:
                        parsed_item = self._parse_data(item)
                        parsed_items.append(parsed_item)
                    except ValueError as e:
                        error_msg = i18n.t('components.processing.parse_json_data.errors.list_item_parsing_failed',
                                           index=i, error=str(e))
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                to_filter = parsed_items
            else:
                to_filter = self._parse_data(to_filter)

            # Process JSON data
            if isinstance(to_filter, list):
                # Handle list of JSON strings
                to_filter_as_dict = []
                for i, json_str in enumerate(to_filter):
                    try:
                        parsed_json = self._repair_and_parse_json(json_str)
                        to_filter_as_dict.append(parsed_json)
                    except ValueError as e:
                        error_msg = i18n.t('components.processing.parse_json_data.errors.list_json_parsing_failed',
                                           index=i, error=str(e))
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
            else:
                # Handle single JSON string
                to_filter_as_dict = self._repair_and_parse_json(to_filter)

            # Convert to JSON string for JQ processing
            full_filter_str = json.dumps(to_filter_as_dict)

            logger.info(f"Input data for JQ: {to_filter_as_dict}")

            # Validate JQ query
            if not self.query or not self.query.strip():
                error_msg = i18n.t(
                    'components.processing.parse_json_data.errors.empty_query')
                self.status = error_msg
                raise ValueError(error_msg)

            # Apply JQ filter
            try:
                jq_filter = jq.compile(self.query)
                results = jq_filter.input_text(full_filter_str).all()
                logger.info(f"JQ filter results: {results}")
            except Exception as e:
                error_msg = i18n.t('components.processing.parse_json_data.errors.jq_filter_failed',
                                   query=self.query, error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Convert results to Data objects
            if not results:
                warning_msg = i18n.t('components.processing.parse_json_data.warnings.no_results',
                                     query=self.query)
                self.status = warning_msg
                return []

            data_results = []
            for i, value in enumerate(results):
                try:
                    if isinstance(value, dict):
                        data_results.append(Data(data=value))
                    else:
                        data_results.append(Data(text=str(value)))
                except Exception as e:
                    error_msg = i18n.t('components.processing.parse_json_data.errors.result_conversion_failed',
                                       index=i, error=str(e))
                    logger.error(error_msg)
                    # Continue with other results instead of failing completely

            success_msg = i18n.t('components.processing.parse_json_data.success.data_filtered',
                                 query=self.query, results=len(data_results))
            self.status = success_msg

            return data_results

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_json_data.errors.filtering_failed', error=str(e))
            self.status = error_msg
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e
