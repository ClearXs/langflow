import os
import i18n
from cleanlab_tlm import TLM

from lfx.custom import Component
from lfx.io import (
    DropdownInput,
    MessageTextInput,
    Output,
    SecretStrInput,
)
from lfx.schema.message import Message


class CleanlabEvaluator(Component):
    """A component that evaluates the trustworthiness of LLM responses using Cleanlab."""

    display_name = i18n.t(
        'components.cleanlab.cleanlab_evaluator.display_name')
    description = i18n.t('components.cleanlab.cleanlab_evaluator.description')
    icon = "Cleanlab"
    name = "CleanlabEvaluator"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.system_prompt.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_evaluator.system_prompt.info'),
            value="",
        ),
        MessageTextInput(
            name="prompt",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.prompt.display_name'),
            info=i18n.t('components.cleanlab.cleanlab_evaluator.prompt.info'),
            required=True,
        ),
        MessageTextInput(
            name="response",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.response.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_evaluator.response.info'),
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.api_key.display_name'),
            info=i18n.t('components.cleanlab.cleanlab_evaluator.api_key.info'),
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.model.display_name'),
            options=[
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4.1-nano",
                "o4-mini",
                "o3",
                "gpt-4.5-preview",
                "gpt-4o-mini",
                "gpt-4o",
                "o3-mini",
                "o1",
                "o1-mini",
                "gpt-4",
                "gpt-3.5-turbo-16k",
                "claude-3.7-sonnet",
                "claude-3.5-sonnet-v2",
                "claude-3.5-sonnet",
                "claude-3.5-haiku",
                "claude-3-haiku",
                "nova-micro",
                "nova-lite",
                "nova-pro",
            ],
            info=i18n.t('components.cleanlab.cleanlab_evaluator.model.info'),
            value="gpt-4o-mini",
            required=True,
            advanced=True,
        ),
        DropdownInput(
            name="quality_preset",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.quality_preset.display_name'),
            options=["base", "low", "medium", "high", "best"],
            value="medium",
            info=i18n.t(
                'components.cleanlab.cleanlab_evaluator.quality_preset.info'),
            required=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.outputs.response.display_name'),
            name="response_passthrough",
            method="pass_response",
            types=["Message"],
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.outputs.score.display_name'),
            name="score",
            method="get_score",
            types=["number"],
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_evaluator.outputs.explanation.display_name'),
            name="explanation",
            method="get_explanation",
            types=["Message"],
        ),
    ]

    def _evaluate_once(self):
        if not hasattr(self, "_cached_result"):
            full_prompt = f"{self.system_prompt}\n\n{self.prompt}" if self.system_prompt else self.prompt
            tlm = TLM(
                api_key=self.api_key,
                options={"log": ["explanation"], "model": self.model},
                quality_preset=self.quality_preset,
            )
            self._cached_result = tlm.get_trustworthiness_score(
                full_prompt, self.response)
        return self._cached_result

    def get_score(self) -> float:
        result = self._evaluate_once()
        score = result.get("trustworthiness_score", 0.0)
        self.status = i18n.t(
            'components.cleanlab.cleanlab_evaluator.status.score', score=score)
        return score

    def get_explanation(self) -> Message:
        result = self._evaluate_once()
        explanation = result.get("log", {}).get("explanation", i18n.t(
            'components.cleanlab.cleanlab_evaluator.errors.no_explanation'))
        return Message(text=explanation)

    def pass_response(self) -> Message:
        self.status = i18n.t(
            'components.cleanlab.cleanlab_evaluator.status.passing_response')
        return Message(text=self.response)
