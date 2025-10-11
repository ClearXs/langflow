import os
import i18n
from langchain_community.chat_models.baidu_qianfan_endpoint import QianfanChatEndpoint

from lfx.base.models.model import LCModelComponent
from lfx.field_typing.constants import LanguageModel
from lfx.io import DropdownInput, FloatInput, MessageTextInput, SecretStrInput
from lfx.log.logger import logger


class QianfanChatEndpointComponent(LCModelComponent):
    display_name: str = i18n.t(
        'components.baidu.baidu_qianfan_chat.display_name')
    description: str = i18n.t(
        'components.baidu.baidu_qianfan_chat.description')
    documentation: str = "https://python.langchain.com/docs/integrations/chat/baidu_qianfan_endpoint"
    icon = "BaiduQianfan"
    name = "BaiduQianfanChatModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.model.display_name'),
            options=[
                "EB-turbo-AppBuilder",
                "Llama-2-70b-chat",
                "ERNIE-Bot-turbo-AI",
                "ERNIE-Lite-8K-0308",
                "ERNIE-Speed",
                "Qianfan-Chinese-Llama-2-13B",
                "ERNIE-3.5-8K",
                "BLOOMZ-7B",
                "Qianfan-Chinese-Llama-2-7B",
                "XuanYuan-70B-Chat-4bit",
                "AquilaChat-7B",
                "ERNIE-Bot-4",
                "Llama-2-13b-chat",
                "ChatGLM2-6B-32K",
                "ERNIE-Bot",
                "ERNIE-Speed-128k",
                "ERNIE-4.0-8K",
                "Qianfan-BLOOMZ-7B-compressed",
                "ERNIE Speed",
                "Llama-2-7b-chat",
                "Mixtral-8x7B-Instruct",
                "ERNIE 3.5",
                "ERNIE Speed-AppBuilder",
                "ERNIE-Speed-8K",
                "Yi-34B-Chat",
            ],
            info=i18n.t('components.baidu.baidu_qianfan_chat.model.info'),
            value="ERNIE-4.0-8K",
        ),
        SecretStrInput(
            name="qianfan_ak",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.qianfan_ak.display_name'),
            info=i18n.t('components.baidu.baidu_qianfan_chat.qianfan_ak.info'),
        ),
        SecretStrInput(
            name="qianfan_sk",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.qianfan_sk.display_name'),
            info=i18n.t('components.baidu.baidu_qianfan_chat.qianfan_sk.info'),
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.top_p.display_name'),
            info=i18n.t('components.baidu.baidu_qianfan_chat.top_p.info'),
            value=0.8,
            advanced=True,
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.temperature.display_name'),
            info=i18n.t(
                'components.baidu.baidu_qianfan_chat.temperature.info'),
            value=0.95,
        ),
        FloatInput(
            name="penalty_score",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.penalty_score.display_name'),
            info=i18n.t(
                'components.baidu.baidu_qianfan_chat.penalty_score.info'),
            value=1.0,
            advanced=True,
        ),
        MessageTextInput(
            name="endpoint",
            display_name=i18n.t(
                'components.baidu.baidu_qianfan_chat.endpoint.display_name'),
            info=i18n.t('components.baidu.baidu_qianfan_chat.endpoint.info')
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build Baidu Qianfan chat model."""
        try:
            self.status = i18n.t('components.baidu.baidu_qianfan_chat.status.initializing',
                                 model=self.model)

            logger.debug(i18n.t('components.baidu.baidu_qianfan_chat.logs.building_model',
                                model=self.model,
                                temperature=self.temperature,
                                top_p=self.top_p,
                                penalty_score=self.penalty_score,
                                has_endpoint=bool(self.endpoint)))

            kwargs = {
                "model": self.model,
                "qianfan_ak": self.qianfan_ak or None,
                "qianfan_sk": self.qianfan_sk or None,
                "top_p": self.top_p,
                "temperature": self.temperature,
                "penalty_score": self.penalty_score,
            }

            if self.endpoint:  # Only add endpoint if it has a value
                kwargs["endpoint"] = self.endpoint
                logger.debug(i18n.t('components.baidu.baidu_qianfan_chat.logs.custom_endpoint_set',
                                    endpoint=self.endpoint))

            output = QianfanChatEndpoint(**kwargs)

            success_msg = i18n.t('components.baidu.baidu_qianfan_chat.success.model_initialized',
                                 model=self.model)
            logger.info(success_msg)
            self.status = success_msg

            return output

        except Exception as e:
            error_msg = i18n.t('components.baidu.baidu_qianfan_chat.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
