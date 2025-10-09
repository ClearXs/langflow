import i18n
from typing import Any

from docling_core.types.doc import ImageRefMode

from lfx.base.data.docling_utils import extract_docling_documents
from lfx.custom import Component
from lfx.io import DropdownInput, HandleInput, MessageTextInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data, DataFrame


class ExportDoclingDocumentComponent(Component):
    display_name: str = i18n.t(
        'components.docling.export_docling_document.display_name')
    description: str = i18n.t(
        'components.docling.export_docling_document.description')
    documentation = "https://docling-project.github.io/docling/"
    icon = "Docling"
    name = "ExportDoclingDocument"

    inputs = [
        HandleInput(
            name="data_inputs",
            display_name=i18n.t(
                'components.docling.export_docling_document.data_inputs.display_name'),
            info=i18n.t(
                'components.docling.export_docling_document.data_inputs.info'),
            input_types=["Data", "DataFrame"],
            required=True,
        ),
        DropdownInput(
            name="export_format",
            display_name=i18n.t(
                'components.docling.export_docling_document.export_format.display_name'),
            options=["Markdown", "HTML", "Plaintext", "DocTags"],
            info=i18n.t(
                'components.docling.export_docling_document.export_format.info'),
            value="Markdown",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="image_mode",
            display_name=i18n.t(
                'components.docling.export_docling_document.image_mode.display_name'),
            options=["placeholder", "embedded"],
            info=i18n.t(
                'components.docling.export_docling_document.image_mode.info'),
            value="placeholder",
        ),
        StrInput(
            name="md_image_placeholder",
            display_name=i18n.t(
                'components.docling.export_docling_document.md_image_placeholder.display_name'),
            info=i18n.t(
                'components.docling.export_docling_document.md_image_placeholder.info'),
            value="<!-- image -->",
            advanced=True,
        ),
        StrInput(
            name="md_page_break_placeholder",
            display_name=i18n.t(
                'components.docling.export_docling_document.md_page_break_placeholder.display_name'),
            info=i18n.t(
                'components.docling.export_docling_document.md_page_break_placeholder.info'),
            value="",
            advanced=True,
        ),
        MessageTextInput(
            name="doc_key",
            display_name=i18n.t(
                'components.docling.export_docling_document.doc_key.display_name'),
            info=i18n.t(
                'components.docling.export_docling_document.doc_key.info'),
            value="doc",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.docling.export_docling_document.outputs.data.display_name'),
            name="data",
            method="export_document"
        ),
        Output(
            display_name=i18n.t(
                'components.docling.export_docling_document.outputs.dataframe.display_name'),
            name="dataframe",
            method="as_dataframe"
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        """Update build configuration based on export format selection.

        Args:
            build_config: The build configuration dictionary.
            field_value: The new field value.
            field_name: The name of the field being updated.

        Returns:
            dict: The updated build configuration.
        """
        if field_name == "export_format" and field_value == "Markdown":
            build_config["md_image_placeholder"]["show"] = True
            build_config["md_page_break_placeholder"]["show"] = True
            build_config["image_mode"]["show"] = True
            logger.debug(i18n.t(
                'components.docling.export_docling_document.logs.markdown_options_enabled'))
        elif field_name == "export_format" and field_value == "HTML":
            build_config["md_image_placeholder"]["show"] = False
            build_config["md_page_break_placeholder"]["show"] = False
            build_config["image_mode"]["show"] = True
            logger.debug(
                i18n.t('components.docling.export_docling_document.logs.html_options_enabled'))
        elif field_name == "export_format" and field_value in {"Plaintext", "DocTags"}:
            build_config["md_image_placeholder"]["show"] = False
            build_config["md_page_break_placeholder"]["show"] = False
            build_config["image_mode"]["show"] = False
            logger.debug(i18n.t('components.docling.export_docling_document.logs.text_options_enabled',
                                format=field_value))

        return build_config

    def export_document(self) -> list[Data]:
        """Export DoclingDocument to the specified format.

        Returns:
            list[Data]: List of exported documents.

        Raises:
            TypeError: If document extraction or export fails.
        """
        try:
            logger.info(i18n.t('components.docling.export_docling_document.logs.extracting_documents',
                               doc_key=self.doc_key))
            documents = extract_docling_documents(
                self.data_inputs, self.doc_key)
            logger.info(i18n.t('components.docling.export_docling_document.logs.documents_extracted',
                               count=len(documents)))
        except Exception as e:
            error_msg = i18n.t('components.docling.export_docling_document.errors.extraction_failed',
                               error=str(e))
            logger.error(error_msg)
            raise TypeError(error_msg) from e

        results: list[Data] = []

        try:
            image_mode = ImageRefMode(self.image_mode)
            logger.info(i18n.t('components.docling.export_docling_document.logs.exporting_documents',
                               format=self.export_format,
                               image_mode=self.image_mode,
                               count=len(documents)))

            for idx, doc in enumerate(documents, 1):
                logger.debug(i18n.t('components.docling.export_docling_document.logs.exporting_document',
                                    index=idx,
                                    total=len(documents)))

                content = ""
                if self.export_format == "Markdown":
                    content = doc.export_to_markdown(
                        image_mode=image_mode,
                        image_placeholder=self.md_image_placeholder,
                        page_break_placeholder=self.md_page_break_placeholder,
                    )
                    logger.debug(i18n.t('components.docling.export_docling_document.logs.markdown_exported',
                                        length=len(content)))
                elif self.export_format == "HTML":
                    content = doc.export_to_html(image_mode=image_mode)
                    logger.debug(i18n.t('components.docling.export_docling_document.logs.html_exported',
                                        length=len(content)))
                elif self.export_format == "Plaintext":
                    content = doc.export_to_text()
                    logger.debug(i18n.t('components.docling.export_docling_document.logs.text_exported',
                                        length=len(content)))
                elif self.export_format == "DocTags":
                    content = doc.export_to_doctags()
                    logger.debug(i18n.t('components.docling.export_docling_document.logs.doctags_exported',
                                        length=len(content)))

                results.append(Data(text=content))

            logger.info(i18n.t('components.docling.export_docling_document.logs.export_completed',
                               count=len(results)))
            return results

        except Exception as e:
            error_msg = i18n.t('components.docling.export_docling_document.errors.export_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise TypeError(error_msg) from e

    def as_dataframe(self) -> DataFrame:
        """Convert exported documents to DataFrame.

        Returns:
            DataFrame: DataFrame containing exported documents.
        """
        try:
            logger.info(
                i18n.t('components.docling.export_docling_document.logs.creating_dataframe'))
            df = DataFrame(self.export_document())
            logger.info(i18n.t('components.docling.export_docling_document.logs.dataframe_created',
                               rows=len(df)))
            return df
        except Exception as e:
            error_msg = i18n.t('components.docling.export_docling_document.errors.dataframe_creation_failed',
                               error=str(e))
            logger.error(error_msg)
            raise TypeError(error_msg) from e
