import i18n
from langchain_core.tools import Tool

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.inputs.inputs import IntInput, MultilineInput, SecretStrInput
from lfx.schema.data import Data


class GoogleSearchAPIComponent(LCToolComponent):
    display_name = i18n.t('components.tools.google_search_api.display_name')
    description = i18n.t('components.tools.google_search_api.description')
    name = "GoogleSearchAPI"
    icon = "Google"
    legacy = True

    inputs = [
        SecretStrInput(
            name="google_api_key",
            display_name=i18n.t(
                'components.tools.google_search_api.google_api_key.display_name'),
            info=i18n.t(
                'components.tools.google_search_api.google_api_key.info'),
            required=True
        ),
        SecretStrInput(
            name="google_cse_id",
            display_name=i18n.t(
                'components.tools.google_search_api.google_cse_id.display_name'),
            info=i18n.t(
                'components.tools.google_search_api.google_cse_id.info'),
            required=True
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.tools.google_search_api.input_value.display_name'),
            info=i18n.t('components.tools.google_search_api.input_value.info'),
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.tools.google_search_api.k.display_name'),
            info=i18n.t('components.tools.google_search_api.k.info'),
            value=4,
            required=True
        ),
    ]

    def run_model(self) -> Data | list[Data]:
        try:
            if not self.input_value or not self.input_value.strip():
                warning_message = i18n.t(
                    'components.tools.google_search_api.warnings.empty_query')
                self.status = warning_message
                return [Data(data={"error": warning_message, "results": []})]

            wrapper = self._build_wrapper()

            executing_message = i18n.t('components.tools.google_search_api.info.searching',
                                       query=self.input_value, count=self.k)
            self.status = executing_message

            results = wrapper.results(
                query=self.input_value, num_results=self.k)

            if not results:
                warning_message = i18n.t('components.tools.google_search_api.warnings.no_results',
                                         query=self.input_value)
                self.status = warning_message
                return [Data(data={"query": self.input_value, "results": [], "message": warning_message})]

            data = [Data(data=result, text=result.get("snippet", ""))
                    for result in results]

            success_message = i18n.t('components.tools.google_search_api.success.search_completed',
                                     count=len(results), query=self.input_value)
            self.status = success_message

            return data

        except ImportError as e:
            error_message = i18n.t(
                'components.tools.google_search_api.errors.import_error')
            self.status = error_message
            return [Data(data={"error": error_message, "details": str(e)})]
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_search_api.errors.search_failed', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message, "query": self.input_value})]

    def build_tool(self) -> Tool:
        try:
            wrapper = self._build_wrapper()
            return Tool(
                name="google_search",
                description=i18n.t(
                    'components.tools.google_search_api.tool_description'),
                func=wrapper.run,
            )
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_search_api.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _build_wrapper(self):
        try:
            from langchain_google_community import GoogleSearchAPIWrapper
        except ImportError as e:
            error_message = i18n.t(
                'components.tools.google_search_api.errors.langchain_google_missing')
            raise ImportError(error_message) from e

        try:
            return GoogleSearchAPIWrapper(
                google_api_key=self.google_api_key,
                google_cse_id=self.google_cse_id,
                k=self.k
            )
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_search_api.errors.wrapper_creation_failed', error=str(e))
            raise ValueError(error_message) from e
