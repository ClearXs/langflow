import os
import i18n
from typing import cast

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.inputs.inputs import MessageTextInput
from lfx.io import BoolInput, FileInput, FloatInput, IntInput, StrInput


class ChatVertexAIComponent(LCModelComponent):
    display_name = i18n.t('components.vertexai.vertexai.display_name')
    description = i18n.t('components.vertexai.vertexai.description')
    icon = "VertexAI"
    name = "VertexAiModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        FileInput(
            name="credentials",
            display_name=i18n.t(
                'components.vertexai.vertexai.credentials.display_name'),
            info=i18n.t('components.vertexai.vertexai.credentials.info'),
            file_types=["json"],
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.vertexai.vertexai.model_name.display_name'),
            value="gemini-1.5-pro"
        ),
        StrInput(
            name="project",
            display_name=i18n.t(
                'components.vertexai.vertexai.project.display_name'),
            info=i18n.t('components.vertexai.vertexai.project.info'),
            advanced=True
        ),
        StrInput(
            name="location",
            display_name=i18n.t(
                'components.vertexai.vertexai.location.display_name'),
            value="us-central1",
            advanced=True
        ),
        IntInput(
            name="max_output_tokens",
            display_name=i18n.t(
                'components.vertexai.vertexai.max_output_tokens.display_name'),
            advanced=True
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.vertexai.vertexai.max_retries.display_name'),
            value=1,
            advanced=True
        ),
        FloatInput(
            name="temperature",
            value=0.0,
            display_name=i18n.t(
                'components.vertexai.vertexai.temperature.display_name')
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t(
                'components.vertexai.vertexai.top_k.display_name'),
            advanced=True
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.vertexai.vertexai.top_p.display_name'),
            value=0.95,
            advanced=True
        ),
        BoolInput(
            name="verbose",
            display_name=i18n.t(
                'components.vertexai.vertexai.verbose.display_name'),
            value=False,
            advanced=True
        ),
    ]

    def build_model(self) -> LanguageModel:
        try:
            from langchain_google_vertexai import ChatVertexAI
        except ImportError as e:
            msg = "Please install the langchain-google-vertexai package to use the VertexAIEmbeddings component."
            raise ImportError(msg) from e
        location = self.location or None
        if self.credentials:
            from google.cloud import aiplatform
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                self.credentials)
            project = self.project or credentials.project_id
            # ChatVertexAI sometimes skip manual credentials initialization
            aiplatform.init(
                project=project,
                location=location,
                credentials=credentials,
            )
        else:
            project = self.project or None
            credentials = None

        return cast(
            "LanguageModel",
            ChatVertexAI(
                credentials=credentials,
                location=location,
                project=project,
                max_output_tokens=self.max_output_tokens or None,
                max_retries=self.max_retries,
                model_name=self.model_name,
                temperature=self.temperature,
                top_k=self.top_k or None,
                top_p=self.top_p,
                verbose=self.verbose,
            ),
        )
