from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING, Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, HandleInput, IntInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame

if TYPE_CHECKING:
    from collections.abc import Callable


class LambdaFilterComponent(Component):
    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    display_name = i18n.t("components.processing.lambda_filter.display_name")
    description = i18n.t("components.processing.lambda_filter.description")
    documentation: str = "https://docs.langflow.org/components-processing#smart-transform"
    icon = "square-function"
    name = "Smart Transform"

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t("components.processing.lambda_filter.data.display_name"),
            info=i18n.t("components.processing.lambda_filter.data.info"),
            input_types=["Data", "DataFrame"],
            is_list=True,
            required=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t("components.processing.lambda_filter.llm.display_name"),
            info=i18n.t("components.processing.lambda_filter.llm.info"),
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="filter_instruction",
            display_name=i18n.t("components.processing.lambda_filter.filter_instruction.display_name"),
            info=i18n.t("components.processing.lambda_filter.filter_instruction.info"),
            value=i18n.t("components.processing.lambda_filter.filter_instruction.default_value"),
            required=True,
        ),
        IntInput(
            name="sample_size",
            display_name=i18n.t("components.processing.lambda_filter.sample_size.display_name"),
            info=i18n.t("components.processing.lambda_filter.sample_size.info"),
            value=1000,
            advanced=True,
        ),
        IntInput(
            name="max_size",
            display_name=i18n.t("components.processing.lambda_filter.max_size.display_name"),
            info=i18n.t("components.processing.lambda_filter.max_size.info"),
            value=30000,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Output",
            name="data_output",
            method="process_as_data",
        ),
        Output(
            name="dataframe_output",
            method="process_as_dataframe",
            display_name=i18n.t("components.processing.lambda_filter.outputs.filtered_data.display_name"),
        ),
    ]

    def get_data_structure(self, data):
        """Extract the structure of data, replacing values with their types."""
        if isinstance(data, list):
            # For lists, get structure of first item if available
            if data:
                return [self.get_data_structure(data[0])]
            return []
        if isinstance(data, dict):
            return {k: self.get_data_structure(v) for k, v in data.items()}
        # For primitive types, return the type name
        return type(data).__name__

    def _validate_lambda(self, lambda_text: str) -> bool:
        """Validate the provided lambda function text."""
        # Return False if the lambda function does not start with 'lambda' or does not contain a colon
        return lambda_text.strip().startswith("lambda") and ":" in lambda_text

    async def _execute_lambda(self) -> Any:
        self.log(str(self.data))

        # Convert input to a unified format
        if isinstance(self.data, list):
            # Handle list of Data or DataFrame objects
            combined_data = []
            for item in self.data:
                if isinstance(item, DataFrame):
                    # DataFrame to list of dicts
                    combined_data.extend(item.to_dict(orient="records"))
                elif hasattr(item, "data"):
                    # Data object
                    if isinstance(item.data, dict):
                        combined_data.append(item.data)
                    elif isinstance(item.data, list):
                        combined_data.extend(item.data)

            # If we have a single dict, unwrap it so lambdas can access it directly
            if len(combined_data) == 1 and isinstance(combined_data[0], dict):
                data = combined_data[0]
            elif len(combined_data) == 0:
                data = {}
            else:
                data = combined_data  # type: ignore[assignment]
        elif isinstance(self.data, DataFrame):
            # Single DataFrame to list of dicts
            data = self.data.to_dict(orient="records")
        elif hasattr(self.data, "data"):
            # Single Data object
            data = self.data.data
        else:
            data = self.data

        dump = json.dumps(data)
        self.log(str(data))

        llm = self.llm
        instruction = self.filter_instruction
        sample_size = self.sample_size

        # Validate inputs
        if not instruction or not instruction.strip():
            error_msg = i18n.t("components.processing.lambda_filter.errors.empty_instruction")
            self.status = error_msg
            raise ValueError(error_msg)

        # Get data structure and samples
        data_structure = self.get_data_structure(data)
        dump_structure = json.dumps(data_structure)
        self.log(dump_structure)

        # For large datasets, sample from head and tail
        if len(dump) > self.max_size:
            data_sample = i18n.t(
                "components.processing.lambda_filter.data_sample_large",
                head=dump[:sample_size],
                tail=dump[-sample_size:],
            )
        else:
            data_sample = dump

        self.log(data_sample)

        # Create prompt with i18n support
        prompt = i18n.t(
            "components.processing.lambda_filter.llm_prompt",
            data_structure=dump_structure,
            data_sample=data_sample,
            instruction=instruction,
        )

        # Get LLM response
        try:
            response = await llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)
            self.log(response_text)
        except Exception as e:
            error_msg = i18n.t("components.processing.lambda_filter.errors.llm_invocation_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

        # Extract lambda using regex
        lambda_match = re.search(r"lambda\s+\w+\s*:.*?(?=\n|$)", response_text)
        if not lambda_match:
            error_msg = i18n.t("components.processing.lambda_filter.errors.lambda_not_found", response=response_text)
            self.status = error_msg
            raise ValueError(error_msg)

        lambda_text = lambda_match.group().strip()
        self.log(lambda_text)

        # Validate lambda function
        if not self._validate_lambda(lambda_text):
            error_msg = i18n.t(
                "components.processing.lambda_filter.errors.invalid_lambda_format", lambda_text=lambda_text
            )
            self.status = error_msg
            raise ValueError(error_msg)

        # Create and apply the function
        try:
            fn: Callable[[Any], Any] = eval(lambda_text)  # noqa: S307
        except Exception as e:
            error_msg = i18n.t(
                "components.processing.lambda_filter.errors.lambda_evaluation_failed",
                lambda_text=lambda_text,
                error=str(e),
            )
            self.status = error_msg
            raise ValueError(error_msg) from e

        # Apply the lambda function to the data
        return fn(data)

    async def process_as_data(self) -> Data:
        """Process the data and return as a Data object."""
        result = await self._execute_lambda()

        # Convert result to Data based on type
        if isinstance(result, dict):
            return Data(data=result)
        if isinstance(result, list):
            return Data(data={"_results": result})
        # For other types, convert to string
        return Data(data={"text": str(result)})

    async def process_as_dataframe(self) -> DataFrame:
        """Process the data and return as a DataFrame."""
        result = await self._execute_lambda()

        # Convert result to DataFrame based on type
        if isinstance(result, list):
            # Check if it's a list of dicts
            if all(isinstance(item, dict) for item in result):
                return DataFrame(result)
            # List of non-dicts: wrap each value
            return DataFrame([{"value": item} for item in result])
        if isinstance(result, dict):
            # Single dict becomes single-row DataFrame
            return DataFrame([result])
        # Other types: convert to string and wrap
        return DataFrame([{"value": str(result)}])

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
            error_msg = i18n.t("components.processing.lambda_filter.errors.data_conversion_failed", error=str(e))
            raise ValueError(error_msg) from e
