from typing import cast
import i18n

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import BoolInput, IntInput, MessageTextInput, MultilineInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class WikipediaAPIComponent(LCToolComponent):
    display_name = i18n.t('components.tools.wikipedia_api.display_name')
    description = i18n.t('components.tools.wikipedia_api.description')
    name = "WikipediaAPI"
    icon = "Wikipedia"
    legacy = True
    replacement = ["wikipedia.WikipediaComponent"]

    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.tools.wikipedia_api.input_value.display_name'),
            info=i18n.t('components.tools.wikipedia_api.input_value.info'),
        ),
        MessageTextInput(
            name="lang",
            display_name=i18n.t(
                'components.tools.wikipedia_api.lang.display_name'),
            info=i18n.t('components.tools.wikipedia_api.lang.info'),
            value="en"
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.tools.wikipedia_api.k.display_name'),
            info=i18n.t('components.tools.wikipedia_api.k.info'),
            value=4,
            required=True
        ),
        BoolInput(
            name="load_all_available_meta",
            display_name=i18n.t(
                'components.tools.wikipedia_api.load_all_available_meta.display_name'),
            info=i18n.t(
                'components.tools.wikipedia_api.load_all_available_meta.info'),
            value=False,
            advanced=True
        ),
        IntInput(
            name="doc_content_chars_max",
            display_name=i18n.t(
                'components.tools.wikipedia_api.doc_content_chars_max.display_name'),
            info=i18n.t(
                'components.tools.wikipedia_api.doc_content_chars_max.info'),
            value=4000,
            advanced=True
        ),
    ]

    def run_model(self) -> list[Data]:
        try:
            if not self.input_value or not self.input_value.strip():
                warning_message = i18n.t(
                    'components.tools.wikipedia_api.warnings.empty_input')
                self.status = warning_message
                return [Data(data={"error": warning_message})]

            executing_message = i18n.t('components.tools.wikipedia_api.info.searching',
                                       query=self.input_value, lang=self.lang)
            self.status = executing_message

            wrapper = self._build_wrapper()
            docs = wrapper.load(self.input_value)

            if not docs:
                warning_message = i18n.t('components.tools.wikipedia_api.warnings.no_results',
                                         query=self.input_value)
                self.status = warning_message
                return [Data(data={"message": warning_message, "query": self.input_value})]

            data = [Data.from_document(doc) for doc in docs]

            success_message = i18n.t('components.tools.wikipedia_api.success.search_completed',
                                     count=len(data), query=self.input_value)
            self.status = success_message
            return data

        except ImportError as e:
            error_message = i18n.t(
                'components.tools.wikipedia_api.errors.import_error')
            self.status = error_message
            logger.debug(error_message, exc_info=True)
            return [Data(data={"error": error_message, "details": str(e)})]
        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikipedia_api.errors.search_failed', error=str(e))
            self.status = error_message
            logger.debug("Error running Wikipedia API", exc_info=True)
            return [Data(data={"error": error_message, "query": self.input_value})]

    def build_tool(self) -> Tool:
        try:
            wrapper = self._build_wrapper()
            tool = cast("Tool", WikipediaQueryRun(api_wrapper=wrapper))

            success_message = i18n.t('components.tools.wikipedia_api.success.tool_created',
                                     lang=self.lang, results=self.k)
            self.status = success_message
            return tool

        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikipedia_api.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _build_wrapper(self) -> WikipediaAPIWrapper:
        try:
            return WikipediaAPIWrapper(
                top_k_results=self.k,
                lang=self.lang,
                load_all_available_meta=self.load_all_available_meta,
                doc_content_chars_max=self.doc_content_chars_max,
            )
        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikipedia_api.errors.wrapper_creation_failed', error=str(e))
            raise ValueError(error_message) from e
