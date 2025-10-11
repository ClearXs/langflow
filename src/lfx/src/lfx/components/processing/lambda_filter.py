from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, HandleInput, IntInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.utils.data_structure import get_data_structure

if TYPE_CHECKING:
    from collections.abc import Callable


class LambdaFilterComponent(Component):
    display_name = "Smart Transform"
    description = "Uses an LLM to generate a function for filtering or transforming structured data."
    documentation: str = "https://docs.langflow.org/components-processing#smart-transform"
    icon = "square-function"
    name = "Smart Transform"

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t(
                'components.processing.lambda_filter.data.display_name'),
            info=i18n.t('components.processing.lambda_filter.data.info'),
            is_list=True,
            required=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.processing.lambda_filter.llm.display_name'),
            info=i18n.t('components.processing.lambda_filter.llm.info'),
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="filter_instruction",
            display_name=i18n.t(
                'components.processing.lambda_filter.filter_instruction.display_name'),
            info=i18n.t(
                'components.processing.lambda_filter.filter_instruction.info'),
            value=i18n.t(
                'components.processing.lambda_filter.filter_instruction.default_value'),
            required=True,
        ),
        IntInput(
            name="sample_size",
            display_name=i18n.t(
                'components.processing.lambda_filter.sample_size.display_name'),
            info=i18n.t(
                'components.processing.lambda_filter.sample_size.info'),
            value=1000,
            advanced=True,
        ),
        IntInput(
            name="max_size",
            display_name=i18n.t(
                'components.processing.lambda_filter.max_size.display_name'),
            info=i18n.t('components.processing.lambda_filter.max_size.info'),
            value=30000,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.lambda_filter.outputs.filtered_data.display_name'),
            name="filtered_data",
            method="filter_data",
        ),
    ]

    def get_data_structure(self, data):
        """Extract the structure of a dictionary, replacing values with their types."""
        return {k: get_data_structure(v) for k, v in data.items()}

    def _validate_lambda(self, lambda_text: str) -> bool:
        """Validate the provided lambda function text."""
        # Return False if the lambda function does not start with 'lambda' or does not contain a colon
        return lambda_text.strip().startswith("lambda") and ":" in lambda_text

    async def filter_data(self) -> list[Data]:
        try:
            self.log(str(self.data))
            data = self.data[0].data if isinstance(
                self.data, list) else self.data.data

            if not data:
                warning_msg = i18n.t(
                    'components.processing.lambda_filter.warnings.empty_data')
                self.status = warning_msg
                return []

            dump = json.dumps(data)
            self.log(str(data))

            llm = self.llm
            instruction = self.filter_instruction
            sample_size = self.sample_size

            # Validate inputs
            if not instruction or not instruction.strip():
                error_msg = i18n.t(
                    'components.processing.lambda_filter.errors.empty_instruction')
                self.status = error_msg
                raise ValueError(error_msg)

            # Get data structure and samples
            data_structure = self.get_data_structure(data)
            dump_structure = json.dumps(data_structure)
            self.log(dump_structure)

            # For large datasets, sample from head and tail
            if len(dump) > self.max_size:
                data_sample = i18n.t('components.processing.lambda_filter.data_sample_large',
                                     head=dump[:sample_size], tail=dump[-sample_size:])
            else:
                data_sample = dump

            self.log(data_sample)

            # Create prompt with i18n support
            prompt = i18n.t('components.processing.lambda_filter.llm_prompt',
                            data_structure=dump_structure,
                            data_sample=data_sample,
                            instruction=instruction)

            # Get LLM response
            try:
                response = await llm.ainvoke(prompt)
                response_text = response.content if hasattr(
                    response, "content") else str(response)
                self.log(response_text)
            except Exception as e:
                error_msg = i18n.t(
                    'components.processing.lambda_filter.errors.llm_invocation_failed', error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Extract lambda using regex
            lambda_match = re.search(
                r"lambda\s+\w+\s*:.*?(?=\n|$)", response_text)
            if not lambda_match:
                error_msg = i18n.t(
                    'components.processing.lambda_filter.errors.lambda_not_found', response=response_text)
                self.status = error_msg
                raise ValueError(error_msg)

            lambda_text = lambda_match.group().strip()
            self.log(lambda_text)

            # Validate lambda function
            if not self._validate_lambda(lambda_text):
                error_msg = i18n.t(
                    'components.processing.lambda_filter.errors.invalid_lambda_format', lambda_text=lambda_text)
                self.status = error_msg
                raise ValueError(error_msg)

            # Create and apply the function
            try:
                fn: Callable[[Any], Any] = eval(lambda_text)  # noqa: S307
            except Exception as e:
                error_msg = i18n.t('components.processing.lambda_filter.errors.lambda_evaluation_failed',
                                   lambda_text=lambda_text, error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Apply the lambda function to the data
            try:
                processed_data = fn(data)
            except Exception as e:
                error_msg = i18n.t(
                    'components.processing.lambda_filter.errors.lambda_execution_failed', error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Convert result to Data objects
            result = self._convert_to_data_objects(processed_data)

            success_msg = i18n.t('components.processing.lambda_filter.success.data_processed',
                                 count=len(result))
            self.status = success_msg

            return result

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.lambda_filter.errors.processing_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _convert_to_data_objects(self, processed_data: Any) -> list[Data]:
        """Convert processed data to Data objects."""
        try:
            # If it's a dict, wrap it in a Data object
            if isinstance(processed_data, dict):
                return [Data(**processed_data)]
            # If it's a list, convert each item to a Data object
            if isinstance(processed_data, list):
                result = []
                for item in processed_data:
                    if isinstance(item, dict):
                        result.append(Data(**item))
                    else:
                        result.append(Data(text=str(item)))
                return result
            # If it's anything else, convert to string and wrap in a Data object
            return [Data(text=str(processed_data))]

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.lambda_filter.errors.data_conversion_failed', error=str(e))
            raise ValueError(error_msg) from e
