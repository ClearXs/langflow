import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.data import Data


class JigsawStackTextTranslateComponent(Component):
    display_name = i18n.t('components.jigsawstack.text_translate.display_name')
    description = i18n.t('components.jigsawstack.text_translate.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/translate"
    icon = "JigsawStack"
    name = "JigsawStackTextTranslate"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    
    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.text_translate.api_key.display_name'),
            info=i18n.t('components.jigsawstack.text_translate.api_key.info'),
            required=True,
        ),
        StrInput(
            name="target_language",
            display_name=i18n.t(
                'components.jigsawstack.text_translate.target_language.display_name'),
            info=i18n.t(
                'components.jigsawstack.text_translate.target_language.info'),
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="text",
            display_name=i18n.t(
                'components.jigsawstack.text_translate.text.display_name'),
            info=i18n.t('components.jigsawstack.text_translate.text.info'),
            required=True,
            is_list=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.text_translate.outputs.translation_results.display_name'),
            name="translation_results",
            method="translation"
        ),
    ]

    def translation(self) -> Data:
        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            jigsawstack_import_error = (
                "JigsawStack package not found. Please install it using: pip install jigsawstack>=0.2.7"
            )
            raise ImportError(jigsawstack_import_error) from e

        try:
            client = JigsawStack(api_key=self.api_key)

            # build request object
            params = {}
            if self.target_language:
                params["target_language"] = self.target_language

            if self.text:
                if isinstance(self.text, list):
                    params["text"] = self.text
                else:
                    params["text"] = [self.text]

            # Call web scraping
            response = client.translate.text(params)

            if not response.get("success", False):
                failed_response_error = "JigsawStack API returned unsuccessful response"
                raise ValueError(failed_response_error)

            return Data(data=response)

        except JigsawStackError as e:
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
