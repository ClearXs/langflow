import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.data import Data


class JigsawStackVOCRComponent(Component):
    display_name = i18n.t('components.jigsawstack.vocr.display_name')
    description = i18n.t('components.jigsawstack.vocr.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/vocr"
    icon = "JigsawStack"
    name = "JigsawStackVOCR"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.vocr.api_key.display_name'),
            info=i18n.t('components.jigsawstack.vocr.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="prompts",
            display_name=i18n.t(
                'components.jigsawstack.vocr.prompts.display_name'),
            info=i18n.t('components.jigsawstack.vocr.prompts.info'),
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="url",
            display_name=i18n.t(
                'components.jigsawstack.vocr.url.display_name'),
            info=i18n.t('components.jigsawstack.vocr.url.info'),
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="file_store_key",
            display_name=i18n.t(
                'components.jigsawstack.vocr.file_store_key.display_name'),
            info=i18n.t('components.jigsawstack.vocr.file_store_key.info'),
            required=False,
            tool_mode=True,
        ),
        IntInput(
            name="page_range_start",
            display_name=i18n.t(
                'components.jigsawstack.vocr.page_range_start.display_name'),
            info=i18n.t('components.jigsawstack.vocr.page_range_start.info'),
            required=False,
        ),
        IntInput(
            name="page_range_end",
            display_name=i18n.t(
                'components.jigsawstack.vocr.page_range_end.display_name'),
            info=i18n.t('components.jigsawstack.vocr.page_range_end.info'),
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.vocr.outputs.vocr_results.display_name'),
            name="vocr_results",
            method="vocr"
        ),
    ]

    def vocr(self) -> Data:
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
            if self.prompts:
                if isinstance(self.prompts, list):
                    params["prompt"] = self.prompts
                elif isinstance(self.prompts, str):
                    if "," in self.prompts:
                        # Split by comma and strip whitespace
                        params["prompt"] = [p.strip()
                                            for p in self.prompts.split(",")]
                    else:
                        params["prompt"] = [self.prompts.strip()]
                else:
                    invalid_prompt_error = "Prompt must be a list of strings or a single string"
                    raise ValueError(invalid_prompt_error)
            if self.url:
                params["url"] = self.url
            if self.file_store_key:
                params["file_store_key"] = self.file_store_key

            if self.page_range_start and self.page_range_end:
                params["page_range"] = [
                    self.page_range_start, self.page_range_end]

            # Call VOCR
            response = client.vision.vocr(params)

            if not response.get("success", False):
                failed_response_error = "JigsawStack API returned unsuccessful response"
                raise ValueError(failed_response_error)

            return Data(data=response)

        except JigsawStackError as e:
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
