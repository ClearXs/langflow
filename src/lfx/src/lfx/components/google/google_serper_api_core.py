import i18n
from langchain_community.utilities.google_serper import GoogleSerperAPIWrapper

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MultilineInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message


class GoogleSerperAPICore(Component):
    display_name = "Google Serper API"
    description = i18n.t(
        'components.google.google_serper_api_core.description')
    icon = "Serper"

    inputs = [
        SecretStrInput(
            name="serper_api_key",
            display_name=i18n.t(
                'components.google.google_serper_api_core.serper_api_key.display_name'),
            required=True,
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.google.google_serper_api_core.input_value.display_name'),
            tool_mode=True,
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.google.google_serper_api_core.k.display_name'),
            value=4,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_serper_api_core.outputs.results.display_name'),
            name="results",
            type_=DataFrame,
            method="search_serper",
        ),
    ]

    def search_serper(self) -> DataFrame:
        """Search using Serper API and return results as DataFrame.

        Returns:
            DataFrame: Search results or error information.
        """
        logger.info(i18n.t('components.google.google_serper_api_core.logs.searching',
                           query=self.input_value[:100] + ("..." if len(self.input_value) > 100 else "")))

        try:
            logger.debug(i18n.t('components.google.google_serper_api_core.logs.building_wrapper',
                                k=self.k))
            wrapper = self._build_wrapper()

            logger.debug(
                i18n.t('components.google.google_serper_api_core.logs.executing_search'))
            results = wrapper.results(query=self.input_value)
            list_results = results.get("organic", [])

            logger.info(i18n.t('components.google.google_serper_api_core.logs.results_retrieved',
                               count=len(list_results)))

            # Convert results to DataFrame using list comprehension
            df_data = [
                {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                }
                for result in list_results
            ]

            logger.debug(i18n.t('components.google.google_serper_api_core.logs.dataframe_created',
                                rows=len(df_data)))

            df = DataFrame(df_data)
            self.status = i18n.t('components.google.google_serper_api_core.logs.status_success',
                                 count=len(df_data))
            return df

        except ValueError as e:
            error_message = i18n.t('components.google.google_serper_api_core.errors.value_error',
                                   error=str(e))
            logger.error(error_message)
            self.status = error_message
            return DataFrame([{"error": error_message}])

        except KeyError as e:
            error_message = i18n.t('components.google.google_serper_api_core.errors.key_error',
                                   error=str(e))
            logger.error(error_message)
            self.status = error_message
            return DataFrame([{"error": error_message}])

        except ConnectionError as e:
            error_message = i18n.t('components.google.google_serper_api_core.errors.connection_error',
                                   error=str(e))
            logger.error(error_message)
            self.status = error_message
            return DataFrame([{"error": error_message}])

        except Exception as e:
            error_message = i18n.t('components.google.google_serper_api_core.errors.unexpected_error',
                                   error=str(e))
            logger.exception(error_message)
            self.status = error_message
            return DataFrame([{"error": error_message}])

    def text_search_serper(self) -> Message:
        """Search and return results as text Message.

        Returns:
            Message: Search results formatted as text.
        """
        logger.info(
            i18n.t('components.google.google_serper_api_core.logs.text_search'))

        search_results = self.search_serper()

        if not search_results.empty:
            text_result = search_results.to_string(index=False)
            logger.debug(i18n.t('components.google.google_serper_api_core.logs.text_result_generated',
                                length=len(text_result)))
        else:
            text_result = i18n.t(
                'components.google.google_serper_api_core.logs.no_results')
            logger.warning(text_result)

        return Message(text=text_result)

    def _build_wrapper(self):
        """Build GoogleSerperAPIWrapper instance.

        Returns:
            GoogleSerperAPIWrapper: Configured wrapper instance.
        """
        logger.debug(
            i18n.t('components.google.google_serper_api_core.logs.creating_wrapper'))
        return GoogleSerperAPIWrapper(serper_api_key=self.serper_api_key, k=self.k)

    def build(self):
        """Build the component.

        Returns:
            Callable: The search_serper method.
        """
        logger.debug(
            i18n.t('components.google.google_serper_api_core.logs.building'))
        return self.search_serper
