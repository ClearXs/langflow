import i18n
from pydantic import BaseModel, Field, create_model
from trustcall import create_extractor

from lfx.base.models.chat_result import get_chat_result
from lfx.custom.custom_component.component import Component
from lfx.helpers.base_model import build_model_from_schema
from lfx.io import (
    HandleInput,
    MessageTextInput,
    MultilineInput,
    Output,
    TableInput,
)
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.table import EditMode


class StructuredOutputComponent(Component):
    display_name = i18n.t(
        'components.processing.structured_output.display_name')
    description = i18n.t('components.processing.structured_output.description')
    documentation: str = "https://docs.langflow.org/components-processing#structured-output"
    name = "StructuredOutput"
    icon = "braces"

    inputs = [
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.processing.structured_output.llm.display_name'),
            info=i18n.t('components.processing.structured_output.llm.info'),
            input_types=["LanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.processing.structured_output.input_value.display_name'),
            info=i18n.t(
                'components.processing.structured_output.input_value.info'),
            tool_mode=True,
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.processing.structured_output.system_prompt.display_name'),
            info=i18n.t(
                'components.processing.structured_output.system_prompt.info'),
            value=i18n.t(
                'components.processing.structured_output.system_prompt.default_value'),
            required=True,
            advanced=True,
        ),
        MessageTextInput(
            name="schema_name",
            display_name=i18n.t(
                'components.processing.structured_output.schema_name.display_name'),
            info=i18n.t(
                'components.processing.structured_output.schema_name.info'),
            advanced=True,
        ),
        TableInput(
            trigger_text=i18n.t(
                'components.inputs.input_mixin.open_table'),
            name="output_schema",
            display_name=i18n.t(
                'components.processing.structured_output.output_schema.display_name'),
            info=i18n.t(
                'components.processing.structured_output.output_schema.info'),
            required=True,
            table_schema=[
                {
                    "name": "name",
                    "display_name": i18n.t('components.processing.structured_output.table_schema.name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.processing.structured_output.table_schema.name.description'),
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": i18n.t('components.processing.structured_output.table_schema.description.display_name'),
                    "type": "str",
                    "description": i18n.t('components.processing.structured_output.table_schema.description.description'),
                    "default": i18n.t('components.processing.structured_output.table_schema.description.default'),
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "type",
                    "display_name": i18n.t('components.processing.structured_output.table_schema.type.display_name'),
                    "type": "str",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.processing.structured_output.table_schema.type.description'),
                    "options": ["str", "int", "float", "bool", "dict"],
                    "default": "str",
                },
                {
                    "name": "multiple",
                    "display_name": i18n.t('components.processing.structured_output.table_schema.multiple.display_name'),
                    "type": "boolean",
                    "description": i18n.t('components.processing.structured_output.table_schema.multiple.description'),
                    "default": "False",
                    "edit_mode": EditMode.INLINE,
                },
            ],
            value=[
                {
                    "name": "field",
                    "description": i18n.t('components.processing.structured_output.table_schema.description.default'),
                    "type": "str",
                    "multiple": "False",
                }
            ],
        ),
    ]

    outputs = [
        Output(
            name="structured_output",
            display_name=i18n.t(
                'components.processing.structured_output.outputs.structured_output.display_name'),
            info=i18n.t(
                'components.processing.structured_output.outputs.structured_output.info'),
            method="build_structured_output",
        ),
        Output(
            name="dataframe_output",
            display_name=i18n.t(
                'components.processing.structured_output.outputs.dataframe_output.display_name'),
            info=i18n.t(
                'components.processing.structured_output.outputs.dataframe_output.info'),
            method="build_structured_dataframe",
        ),
    ]

    def build_structured_output_base(self):
        """Core structured output processing logic."""
        try:
            schema_name = self.schema_name or "OutputModel"

            # Validate LLM support for structured output
            if not hasattr(self.llm, "with_structured_output"):
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.llm_no_structured_support')
                self.status = error_msg
                raise TypeError(error_msg)

            # Validate output schema
            if not self.output_schema:
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.empty_output_schema')
                self.status = error_msg
                raise ValueError(error_msg)

            # Validate input value
            if not self.input_value or not self.input_value.strip():
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.empty_input_value')
                self.status = error_msg
                raise ValueError(error_msg)

            # Update status
            self.status = i18n.t(
                'components.processing.structured_output.status.building_model')

            # Build output model from schema
            try:
                output_model_ = build_model_from_schema(self.output_schema)
            except Exception as e:
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.model_build_failed', error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Create wrapper model for list of objects
            output_model = create_model(
                schema_name,
                __doc__=f"A list of {schema_name}.",
                # type: ignore[valid-type]
                objects=(list[output_model_], Field(
                    description=f"A list of {schema_name}.")),
            )

            # Create extractor with structured output
            self.status = i18n.t(
                'components.processing.structured_output.status.creating_extractor')
            try:
                llm_with_structured_output = create_extractor(
                    self.llm, tools=[output_model])
            except NotImplementedError as exc:
                error_msg = i18n.t('components.processing.structured_output.errors.llm_not_supported',
                                   llm_name=self.llm.__class__.__name__)
                self.status = error_msg
                raise TypeError(error_msg) from exc
            except Exception as e:
                error_msg = i18n.t('components.processing.structured_output.errors.extractor_creation_failed',
                                   error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Execute structured output generation
            self.status = i18n.t(
                'components.processing.structured_output.status.generating_output')
            config_dict = {
                "run_name": self.display_name,
                "project_name": self.get_project_name(),
                "callbacks": self.get_langchain_callbacks(),
            }

            try:
                result = get_chat_result(
                    runnable=llm_with_structured_output,
                    system_message=self.system_prompt,
                    input_value=self.input_value,
                    config=config_dict,
                )
            except Exception as e:
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.chat_result_failed', error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Process the result
            self.status = i18n.t(
                'components.processing.structured_output.status.processing_result')

            # Handle non-dict responses (shouldn't happen with trustcall, but defensive)
            if not isinstance(result, dict):
                warning_msg = i18n.t('components.processing.structured_output.warnings.unexpected_result_type',
                                     result_type=type(result).__name__)
                self.log(warning_msg, "warning")
                return result

            # Extract first response and convert BaseModel to dict
            responses = result.get("responses", [])
            if not responses:
                warning_msg = i18n.t(
                    'components.processing.structured_output.warnings.no_responses')
                self.log(warning_msg, "warning")
                return result

            # Convert BaseModel to dict (creates the "objects" key)
            first_response = responses[0]
            structured_data = first_response.model_dump() if isinstance(
                first_response, BaseModel) else first_response

            # Extract the objects array (guaranteed to exist due to our Pydantic model structure)
            extracted_objects = structured_data.get("objects", structured_data)

            success_msg = i18n.t('components.processing.structured_output.success.objects_extracted',
                                 count=len(extracted_objects) if isinstance(extracted_objects, list) else 1)
            self.status = success_msg
            self.log(success_msg)

            return extracted_objects

        except (TypeError, ValueError):
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.structured_output.errors.base_processing_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def build_structured_output(self) -> Data:
        """Build structured output as Data object."""
        try:
            output = self.build_structured_output_base()

            if not isinstance(output, list) or not output:
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.no_structured_output')
                self.status = error_msg
                raise ValueError(error_msg)

            if len(output) == 1:
                success_msg = i18n.t(
                    'components.processing.structured_output.success.single_data_created')
                self.status = success_msg
                return Data(data=output[0])
            elif len(output) > 1:
                success_msg = i18n.t('components.processing.structured_output.success.multiple_data_created',
                                     count=len(output))
                self.status = success_msg
                # Multiple outputs - wrap them in a results container
                return Data(data={"results": output})
            else:
                warning_msg = i18n.t(
                    'components.processing.structured_output.warnings.empty_output_list')
                self.status = warning_msg
                return Data()

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.structured_output.errors.data_creation_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def build_structured_dataframe(self) -> DataFrame:
        """Build structured output as DataFrame."""
        try:
            output = self.build_structured_output_base()

            if not isinstance(output, list) or not output:
                error_msg = i18n.t(
                    'components.processing.structured_output.errors.no_structured_output')
                self.status = error_msg
                raise ValueError(error_msg)

            if len(output) == 1:
                success_msg = i18n.t(
                    'components.processing.structured_output.success.single_row_dataframe_created')
                self.status = success_msg
                # For single dictionary, wrap in a list to create DataFrame with one row
                return DataFrame([output[0]])
            elif len(output) > 1:
                success_msg = i18n.t('components.processing.structured_output.success.multi_row_dataframe_created',
                                     rows=len(output))
                self.status = success_msg
                # Multiple outputs - convert to DataFrame directly
                return DataFrame(output)
            else:
                warning_msg = i18n.t(
                    'components.processing.structured_output.warnings.empty_output_list')
                self.status = warning_msg
                return DataFrame()

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.structured_output.errors.dataframe_creation_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e
