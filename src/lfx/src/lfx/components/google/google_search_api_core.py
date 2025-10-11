import os
import i18n
from langchain_google_community import GoogleSearchAPIWrapper

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MultilineInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame


class GoogleSearchAPICore(Component):
    display_name = "Google Search API"
    description = i18n.t(
        'components.google.google_search_api_core.description')
    icon = "Google"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="google_api_key",
            display_name=i18n.t(
                'components.google.google_search_api_core.google_api_key.display_name'),
            required=True,
        ),
        SecretStrInput(
            name="google_cse_id",
            display_name=i18n.t(
                'components.google.google_search_api_core.google_cse_id.display_name'),
            required=True,
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.google.google_search_api_core.input_value.display_name'),
            tool_mode=True,
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.google.google_search_api_core.k.display_name'),
            value=4,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_search_api_core.outputs.results.display_name'),
            name="results",
            type_=DataFrame,
            method="search_google",
        ),
    ]

    def search_google(self) -> DataFrame:
        """Search Google using the provided query.

        Returns:
            DataFrame: Search results or error information.
        """
        logger.info(i18n.t('components.google.google_search_api_core.logs.searching',
                           query=self.input_value[:100] + ("..." if len(self.input_value) > 100 else "")))

        if not self.google_api_key:
            error_msg = i18n.t(
                'components.google.google_search_api_core.errors.invalid_api_key')
            logger.error(error_msg)
            return DataFrame([{"error": error_msg}])

        if not self.google_cse_id:
            error_msg = i18n.t(
                'components.google.google_search_api_core.errors.invalid_cse_id')
            logger.error(error_msg)
            return DataFrame([{"error": error_msg}])

        logger.debug(i18n.t('components.google.google_search_api_core.logs.creating_wrapper',
                            k=self.k))

        try:
            wrapper = GoogleSearchAPIWrapper(
                google_api_key=self.google_api_key,
                google_cse_id=self.google_cse_id,
                k=self.k
            )

            logger.debug(
                i18n.t('components.google.google_search_api_core.logs.executing_search'))
            results = wrapper.results(
                query=self.input_value, num_results=self.k)

            logger.info(i18n.t('components.google.google_search_api_core.logs.search_completed',
                               count=len(results)))

            df = DataFrame(results)
            self.status = i18n.t('components.google.google_search_api_core.logs.status_success',
                                 count=len(results))
            return df

        except (ValueError, KeyError) as e:
            error_msg = i18n.t('components.google.google_search_api_core.errors.invalid_configuration',
                               error=str(e))
            logger.error(error_msg)
            return DataFrame([{"error": error_msg}])

        except ConnectionError as e:
            error_msg = i18n.t('components.google.google_search_api_core.errors.connection_error',
                               error=str(e))
            logger.error(error_msg)
            return DataFrame([{"error": error_msg}])

        except RuntimeError as e:
            error_msg = i18n.t('components.google.google_search_api_core.errors.search_error',
                               error=str(e))
            logger.exception(error_msg)
            return DataFrame([{"error": error_msg}])

        except Exception as e:
            error_msg = i18n.t('components.google.google_search_api_core.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            return DataFrame([{"error": error_msg}])

    def build(self):
        logger.debug(
            i18n.t('components.google.google_search_api_core.logs.building'))
        return self.search_google
