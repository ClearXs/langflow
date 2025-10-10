import os
import i18n
from langchain_core.tools import tool
from metaphor_python import Metaphor

from lfx.custom.custom_component.component import Component
from lfx.field_typing import Tool
from lfx.io import BoolInput, IntInput, Output, SecretStrInput
from lfx.log.logger import logger


class ExaSearchToolkit(Component):
    display_name = "Exa Search"
    description = i18n.t('components.exa.exa_search.description')
    documentation = "https://python.langchain.com/docs/integrations/tools/metaphor_search"
    beta = True
    name = "ExaSearch"
    icon = "ExaSearch"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="metaphor_api_key",
            display_name=i18n.t(
                'components.exa.exa_search.metaphor_api_key.display_name'),
            password=True,
            info=i18n.t('components.exa.exa_search.metaphor_api_key.info'),
        ),
        BoolInput(
            name="use_autoprompt",
            display_name=i18n.t(
                'components.exa.exa_search.use_autoprompt.display_name'),
            value=True,
            info=i18n.t('components.exa.exa_search.use_autoprompt.info'),
        ),
        IntInput(
            name="search_num_results",
            display_name=i18n.t(
                'components.exa.exa_search.search_num_results.display_name'),
            value=5,
            info=i18n.t('components.exa.exa_search.search_num_results.info'),
        ),
        IntInput(
            name="similar_num_results",
            display_name=i18n.t(
                'components.exa.exa_search.similar_num_results.display_name'),
            value=5,
            info=i18n.t('components.exa.exa_search.similar_num_results.info'),
        ),
    ]

    outputs = [
        Output(
            name="tools",
            display_name=i18n.t(
                'components.exa.exa_search.outputs.tools.display_name'),
            method="build_toolkit"
        ),
    ]

    def build_toolkit(self) -> Tool:
        """Build Exa Search toolkit with search, content retrieval, and similarity tools.

        Returns:
            list[Tool]: List of Exa Search tools.

        Raises:
            ValueError: If API key is invalid or client creation fails.
        """
        try:
            logger.info(
                i18n.t('components.exa.exa_search.logs.building_toolkit'))

            if not self.metaphor_api_key:
                error_msg = i18n.t(
                    'components.exa.exa_search.errors.api_key_required')
                logger.error(error_msg)
                raise ValueError(error_msg)

            client = Metaphor(api_key=self.metaphor_api_key)
            logger.info(
                i18n.t('components.exa.exa_search.logs.client_created'))

        except Exception as e:
            error_msg = i18n.t('components.exa.exa_search.errors.client_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        @tool
        def search(query: str):
            """Call search engine with a query.

            Args:
                query: The search query string.

            Returns:
                Search results from Exa.
            """
            try:
                logger.info(i18n.t('components.exa.exa_search.logs.searching',
                                   query=query[:100] + ("..." if len(query) > 100 else "")))

                results = client.search(
                    query,
                    use_autoprompt=self.use_autoprompt,
                    num_results=self.search_num_results
                )

                logger.info(i18n.t('components.exa.exa_search.logs.search_completed',
                                   count=self.search_num_results))
                return results

            except Exception as e:
                error_msg = i18n.t('components.exa.exa_search.errors.search_failed',
                                   error=str(e))
                logger.error(error_msg)
                raise

        @tool
        def get_contents(ids: list[str]):
            """Get contents of a webpage.

            The ids passed in should be a list of ids as fetched from `search`.

            Args:
                ids: List of content IDs from search results.

            Returns:
                Content of the specified webpages.
            """
            try:
                logger.info(i18n.t('components.exa.exa_search.logs.getting_contents',
                                   count=len(ids)))

                contents = client.get_contents(ids)

                logger.info(i18n.t('components.exa.exa_search.logs.contents_retrieved',
                                   count=len(ids)))
                return contents

            except Exception as e:
                error_msg = i18n.t('components.exa.exa_search.errors.get_contents_failed',
                                   error=str(e))
                logger.error(error_msg)
                raise

        @tool
        def find_similar(url: str):
            """Get search results similar to a given URL.

            The url passed in should be a URL returned from `search`.

            Args:
                url: The URL to find similar results for.

            Returns:
                Similar search results.
            """
            try:
                logger.info(i18n.t('components.exa.exa_search.logs.finding_similar',
                                   url=url))

                results = client.find_similar(
                    url, num_results=self.similar_num_results)

                logger.info(i18n.t('components.exa.exa_search.logs.similar_found',
                                   count=self.similar_num_results))
                return results

            except Exception as e:
                error_msg = i18n.t('components.exa.exa_search.errors.find_similar_failed',
                                   error=str(e))
                logger.error(error_msg)
                raise

        logger.info(i18n.t('components.exa.exa_search.logs.toolkit_built'))
        return [search, get_contents, find_similar]
