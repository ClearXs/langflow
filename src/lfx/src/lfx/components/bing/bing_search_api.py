from typing import cast

import i18n
from langchain_community.tools.bing_search import BingSearchResults
from langchain_community.utilities import BingSearchAPIWrapper

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import IntInput, MessageTextInput, MultilineInput, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.template.field.base import Output


class BingSearchAPIComponent(LCToolComponent):
    display_name = i18n.t('components.bing.bing_search_api.display_name')
    description = i18n.t('components.bing.bing_search_api.description')
    name = "BingSearchAPI"
    icon = "Bing"

    inputs = [
        SecretStrInput(
            name="bing_subscription_key",
            display_name=i18n.t(
                'components.bing.bing_search_api.bing_subscription_key.display_name'),
            info=i18n.t(
                'components.bing.bing_search_api.bing_subscription_key.info'),
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.bing.bing_search_api.input_value.display_name'),
            info=i18n.t('components.bing.bing_search_api.input_value.info'),
        ),
        MessageTextInput(
            name="bing_search_url",
            display_name=i18n.t(
                'components.bing.bing_search_api.bing_search_url.display_name'),
            info=i18n.t(
                'components.bing.bing_search_api.bing_search_url.info'),
            advanced=True,
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.bing.bing_search_api.k.display_name'),
            info=i18n.t('components.bing.bing_search_api.k.info'),
            value=4,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.bing.bing_search_api.outputs.dataframe.display_name'),
            name="dataframe",
            method="fetch_content_dataframe"
        ),
        Output(
            display_name=i18n.t(
                'components.bing.bing_search_api.outputs.tool.display_name'),
            name="tool",
            method="build_tool"
        ),
    ]

    def run_model(self) -> DataFrame:
        return self.fetch_content_dataframe()

    def fetch_content(self) -> list[Data]:
        """Fetch search results from Bing Search API."""
        try:
            self.status = i18n.t('components.bing.bing_search_api.status.searching',
                                 query=self.input_value)

            logger.debug(i18n.t('components.bing.bing_search_api.logs.initializing_wrapper',
                                has_custom_url=bool(self.bing_search_url),
                                num_results=self.k))

            if self.bing_search_url:
                wrapper = BingSearchAPIWrapper(
                    bing_search_url=self.bing_search_url,
                    bing_subscription_key=self.bing_subscription_key
                )
                logger.debug(i18n.t('components.bing.bing_search_api.logs.custom_url_set',
                                    url=self.bing_search_url))
            else:
                wrapper = BingSearchAPIWrapper(
                    bing_subscription_key=self.bing_subscription_key)
                logger.debug(
                    i18n.t('components.bing.bing_search_api.logs.default_url_used'))

            logger.info(i18n.t('components.bing.bing_search_api.logs.executing_search',
                               query=self.input_value,
                               num_results=self.k))

            results = wrapper.results(
                query=self.input_value, num_results=self.k)
            data = [Data(data=result, text=result["snippet"])
                    for result in results]

            success_msg = i18n.t('components.bing.bing_search_api.success.results_found',
                                 count=len(data))
            logger.info(success_msg)
            self.status = data

            return data

        except Exception as e:
            error_msg = i18n.t('components.bing.bing_search_api.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def fetch_content_dataframe(self) -> DataFrame:
        """Fetch search results and return as DataFrame."""
        try:
            self.status = i18n.t(
                'components.bing.bing_search_api.status.converting_to_dataframe')

            data = self.fetch_content()
            df = DataFrame(data)

            logger.debug(i18n.t('components.bing.bing_search_api.logs.dataframe_created',
                                rows=len(data)))

            return df

        except Exception as e:
            error_msg = i18n.t('components.bing.bing_search_api.errors.dataframe_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def build_tool(self) -> Tool:
        """Build Bing Search tool."""
        try:
            self.status = i18n.t(
                'components.bing.bing_search_api.status.building_tool')

            logger.debug(i18n.t('components.bing.bing_search_api.logs.building_tool',
                                has_custom_url=bool(self.bing_search_url),
                                num_results=self.k))

            if self.bing_search_url:
                wrapper = BingSearchAPIWrapper(
                    bing_search_url=self.bing_search_url,
                    bing_subscription_key=self.bing_subscription_key
                )
            else:
                wrapper = BingSearchAPIWrapper(
                    bing_subscription_key=self.bing_subscription_key)

            tool = cast("Tool", BingSearchResults(
                api_wrapper=wrapper, num_results=self.k))

            success_msg = i18n.t(
                'components.bing.bing_search_api.success.tool_built')
            logger.info(success_msg)
            self.status = success_msg

            return tool

        except Exception as e:
            error_msg = i18n.t('components.bing.bing_search_api.errors.tool_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
