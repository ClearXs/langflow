import i18n

from langchain_text_splitters import CharacterTextSplitter

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, HandleInput, IntInput, MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from lfx.utils.util import unescape_string


class SplitTextComponent(Component):
    display_name: str = i18n.t('components.processing.split_text.display_name')
    description: str = i18n.t('components.processing.split_text.description')
    documentation: str = "https://docs.langflow.org/components-processing#split-text"
    icon = "scissors-line-dashed"
    name = "SplitText"

    inputs = [
        HandleInput(
            name="data_inputs",
            display_name=i18n.t(
                'components.processing.split_text.data_inputs.display_name'),
            info=i18n.t('components.processing.split_text.data_inputs.info'),
            input_types=["Data", "DataFrame", "Message"],
            required=True,
        ),
        IntInput(
            name="chunk_overlap",
            display_name=i18n.t(
                'components.processing.split_text.chunk_overlap.display_name'),
            info=i18n.t('components.processing.split_text.chunk_overlap.info'),
            value=200,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.processing.split_text.chunk_size.display_name'),
            info=i18n.t('components.processing.split_text.chunk_size.info'),
            value=1000,
        ),
        MessageTextInput(
            name="separator",
            display_name=i18n.t(
                'components.processing.split_text.separator.display_name'),
            info=i18n.t('components.processing.split_text.separator.info'),
            value="\n",
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.processing.split_text.text_key.display_name'),
            info=i18n.t('components.processing.split_text.text_key.info'),
            value="text",
            advanced=True,
        ),
        DropdownInput(
            name="keep_separator",
            display_name=i18n.t(
                'components.processing.split_text.keep_separator.display_name'),
            info=i18n.t(
                'components.processing.split_text.keep_separator.info'),
            options=[
                i18n.t(
                    'components.processing.split_text.keep_separator.options.false'),
                i18n.t('components.processing.split_text.keep_separator.options.true'),
                i18n.t(
                    'components.processing.split_text.keep_separator.options.start'),
                i18n.t('components.processing.split_text.keep_separator.options.end'),
            ],
            value=i18n.t(
                'components.processing.split_text.keep_separator.options.false'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.split_text.outputs.chunks.display_name'),
            name="dataframe",
            method="split_text"
        ),
    ]

    def _docs_to_data(self, docs) -> list[Data]:
        """Convert documents to Data objects."""
        try:
            return [Data(text=doc.page_content, data=doc.metadata) for doc in docs]
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.split_text.errors.docs_to_data_failed', error=str(e))
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def _fix_separator(self, separator: str) -> str:
        """Fix common separator issues and convert to proper format."""
        try:
            if separator == "/n":
                return "\n"
            if separator == "/t":
                return "\t"
            return separator
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.split_text.errors.separator_fix_failed', error=str(e))
            self.log(error_msg, "warning")
            return separator  # Return original if fixing fails

    def _map_keep_separator_option(self, option: str) -> str | bool:
        """Map localized keep_separator options to internal values."""
        try:
            option_map = {
                # Localized options
                i18n.t('components.processing.split_text.keep_separator.options.false'): False,
                i18n.t('components.processing.split_text.keep_separator.options.true'): True,
                i18n.t('components.processing.split_text.keep_separator.options.start'): "start",
                i18n.t('components.processing.split_text.keep_separator.options.end'): "end",
                # English options for backwards compatibility
                "False": False,
                "True": True,
                "Start": "start",
                "End": "end",
                # Lowercase variations
                "false": False,
                "true": True,
                "start": "start",
                "end": "end",
            }

            return option_map.get(option, False)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.split_text.errors.option_mapping_failed', error=str(e))
            self.log(error_msg, "warning")
            return False  # Default to False if mapping fails

    def split_text_base(self):
        """Base text splitting functionality."""
        try:
            # Validate inputs
            if not hasattr(self, 'data_inputs') or not self.data_inputs:
                error_msg = i18n.t(
                    'components.processing.split_text.errors.no_data_inputs')
                self.status = error_msg
                raise ValueError(error_msg)

            # Fix and validate separator
            separator = self._fix_separator(
                self.separator if self.separator is not None else "\n")
            separator = unescape_string(separator)

            # Process different input types
            documents = []

            if isinstance(self.data_inputs, DataFrame):
                if len(self.data_inputs) == 0:
                    error_msg = i18n.t(
                        'components.processing.split_text.errors.empty_dataframe')
                    self.status = error_msg
                    raise ValueError(error_msg)

                self.data_inputs.text_key = self.text_key
                try:
                    documents = self.data_inputs.to_lc_documents()
                    self.log(i18n.t('components.processing.split_text.logs.dataframe_converted',
                                    count=len(documents)))
                except Exception as e:
                    error_msg = i18n.t('components.processing.split_text.errors.dataframe_conversion_failed',
                                       error=str(e))
                    self.status = error_msg
                    raise ValueError(error_msg) from e

            elif isinstance(self.data_inputs, Message):
                # Convert Message to Data and recursively call
                self.data_inputs = [self.data_inputs.to_data()]
                return self.split_text_base()

            elif isinstance(self.data_inputs, Data):
                # Single Data object
                self.data_inputs.text_key = self.text_key
                try:
                    documents = [self.data_inputs.to_lc_document()]
                    self.log(
                        i18n.t('components.processing.split_text.logs.single_data_converted'))
                except Exception as e:
                    error_msg = i18n.t('components.processing.split_text.errors.data_conversion_failed',
                                       error=str(e))
                    self.status = error_msg
                    raise ValueError(error_msg) from e

            elif isinstance(self.data_inputs, list):
                # List of Data objects
                try:
                    valid_documents = []
                    for i, input_item in enumerate(self.data_inputs):
                        if isinstance(input_item, Data):
                            input_item.text_key = self.text_key
                            valid_documents.append(input_item.to_lc_document())
                        else:
                            warning_msg = i18n.t('components.processing.split_text.warnings.invalid_list_item',
                                                 index=i, type=type(input_item).__name__)
                            self.log(warning_msg, "warning")

                    if not valid_documents:
                        error_msg = i18n.t(
                            'components.processing.split_text.errors.no_valid_data_in_list')
                        self.status = error_msg
                        raise ValueError(error_msg)

                    documents = valid_documents
                    self.log(i18n.t('components.processing.split_text.logs.list_converted',
                                    count=len(documents), total=len(self.data_inputs)))

                except AttributeError as e:
                    error_msg = i18n.t('components.processing.split_text.errors.list_conversion_failed',
                                       error=str(e))
                    self.status = error_msg
                    raise ValueError(error_msg) from e
            else:
                error_msg = i18n.t('components.processing.split_text.errors.unsupported_input_type',
                                   type=type(self.data_inputs).__name__)
                self.status = error_msg
                raise ValueError(error_msg)

            # Configure text splitter
            try:
                keep_sep = self._map_keep_separator_option(self.keep_separator)

                splitter = CharacterTextSplitter(
                    chunk_overlap=self.chunk_overlap or 200,
                    chunk_size=self.chunk_size or 1000,
                    separator=separator,
                    keep_separator=keep_sep,
                )

                self.log(i18n.t('components.processing.split_text.logs.splitter_configured',
                                separator=repr(separator), chunk_size=self.chunk_size,
                                chunk_overlap=self.chunk_overlap, keep_separator=keep_sep))

            except Exception as e:
                error_msg = i18n.t('components.processing.split_text.errors.splitter_configuration_failed',
                                   error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Split documents
            try:
                split_docs = splitter.split_documents(documents)

                success_msg = i18n.t('components.processing.split_text.success.text_split',
                                     original_docs=len(documents), split_docs=len(split_docs))
                self.status = success_msg
                self.log(success_msg)

                return split_docs

            except Exception as e:
                error_msg = i18n.t('components.processing.split_text.errors.text_splitting_failed',
                                   error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.split_text.errors.split_base_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def split_text(self) -> DataFrame:
        """Split text and return as DataFrame."""
        try:
            split_documents = self.split_text_base()
            data_objects = self._docs_to_data(split_documents)

            result_df = DataFrame(data_objects)

            success_msg = i18n.t('components.processing.split_text.success.dataframe_created',
                                 chunks=len(data_objects))
            self.status = success_msg

            return result_df

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.split_text.errors.final_processing_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e
