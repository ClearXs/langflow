import os
import i18n
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import Embeddings
from lfx.io import BoolInput, FileInput, FloatInput, IntInput, MessageTextInput, Output


class VertexAIEmbeddingsComponent(LCModelComponent):
    display_name = i18n.t(
        'components.vertexai.vertexai_embeddings.display_name')
    description = i18n.t('components.vertexai.vertexai_embeddings.description')
    icon = "VertexAI"
    name = "VertexAIEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        FileInput(
            name="credentials",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.credentials.display_name'),
            info=i18n.t(
                'components.vertexai.vertexai_embeddings.credentials.info'),
            value="",
            file_types=["json"],
            required=True,
        ),
        MessageTextInput(
            name="location",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.location.display_name'),
            value="us-central1",
            advanced=True
        ),
        MessageTextInput(
            name="project",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.project.display_name'),
            info=i18n.t(
                'components.vertexai.vertexai_embeddings.project.info'),
            advanced=True
        ),
        IntInput(
            name="max_output_tokens",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.max_output_tokens.display_name'),
            advanced=True
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.max_retries.display_name'),
            value=1,
            advanced=True
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.model_name.display_name'),
            value="textembedding-gecko",
            required=True
        ),
        IntInput(
            name="n",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.n.display_name'),
            value=1,
            advanced=True
        ),
        IntInput(
            name="request_parallelism",
            value=5,
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.request_parallelism.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="stop_sequences",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.stop_sequences.display_name'),
            advanced=True,
            is_list=True
        ),
        BoolInput(
            name="streaming",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.streaming.display_name'),
            value=False,
            advanced=True
        ),
        FloatInput(
            name="temperature",
            value=0.0,
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.temperature.display_name')
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.top_k.display_name'),
            advanced=True
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.top_p.display_name'),
            value=0.95,
            advanced=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.vertexai.vertexai_embeddings.outputs.embeddings'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        try:
            from langchain_google_vertexai import VertexAIEmbeddings
        except ImportError as e:
            msg = "Please install the langchain-google-vertexai package to use the VertexAIEmbeddings component."
            raise ImportError(msg) from e

        from google.oauth2 import service_account

        if self.credentials:
            gcloud_credentials = service_account.Credentials.from_service_account_file(
                self.credentials)
        else:
            # will fallback to environment variable or inferred from gcloud CLI
            gcloud_credentials = None
        return VertexAIEmbeddings(
            credentials=gcloud_credentials,
            location=self.location,
            max_output_tokens=self.max_output_tokens or None,
            max_retries=self.max_retries,
            model_name=self.model_name,
            n=self.n,
            project=self.project,
            request_parallelism=self.request_parallelism,
            stop=self.stop_sequences or None,
            streaming=self.streaming,
            temperature=self.temperature,
            top_k=self.top_k or None,
            top_p=self.top_p,
        )
