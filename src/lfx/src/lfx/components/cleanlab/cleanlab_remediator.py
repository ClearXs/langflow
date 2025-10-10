import os
import i18n
from lfx.custom import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import BoolInput, FloatInput, HandleInput, MessageTextInput, Output, PromptInput
from lfx.log.logger import logger
from lfx.schema.message import Message


class CleanlabRemediator(Component):
    """Remediates potentially untrustworthy LLM responses based on trust scores computed by the Cleanlab Evaluator.

    This component takes a response and its associated trust score,
    and applies remediation strategies based on configurable thresholds and settings.

    Inputs:
        - response (MessageTextInput): The original LLM-generated response to be evaluated and possibly remediated.
          The CleanlabEvaluator passes this response through.
        - score (HandleInput): The trust score output from CleanlabEvaluator (expected to be a float between 0 and 1).
        - explanation (MessageTextInput): Optional textual explanation for the trust score, to be included in the
          output.
        - threshold (Input[float]): Minimum trust score required to accept the response. If the score is lower, the
          response is remediated.
        - show_untrustworthy_response (BoolInput): If true, returns the original response with a warning; if false,
          returns fallback text.
        - untrustworthy_warning_text (PromptInput): Text warning to append to responses deemed untrustworthy (when
          showing them).
        - fallback_text (PromptInput): Replacement message returned if the response is untrustworthy and should be
          hidden.

    Outputs:
        - remediated_response (Message): Either:
            • the original response,
            • the original response with appended warning, or
            • the fallback response,
          depending on the trust score and configuration.

    This component is typically used downstream of CleanlabEvaluator or CleanlabRagValidator
    to take appropriate action on low-trust responses and inform users accordingly.
    """

    display_name = i18n.t(
        'components.cleanlab.cleanlab_remediator.display_name')
    description = i18n.t('components.cleanlab.cleanlab_remediator.description')
    icon = "Cleanlab"
    name = "CleanlabRemediator"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="response",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.response.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.response.info'),
            required=True,
        ),
        HandleInput(
            name="score",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.score.display_name'),
            info=i18n.t('components.cleanlab.cleanlab_remediator.score.info'),
            input_types=["number"],
            required=True,
        ),
        MessageTextInput(
            name="explanation",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.explanation.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.explanation.info'),
            required=False,
        ),
        FloatInput(
            name="threshold",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.threshold.display_name'),
            field_type="float",
            value=0.7,
            range_spec=RangeSpec(min=0.0, max=1.0, step=0.05),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.threshold.info'),
            required=True,
            show=True,
        ),
        BoolInput(
            name="show_untrustworthy_response",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.show_untrustworthy_response.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.show_untrustworthy_response.info'),
            value=True,
        ),
        PromptInput(
            name="untrustworthy_warning_text",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.untrustworthy_warning_text.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.untrustworthy_warning_text.info'),
            value=i18n.t(
                'components.cleanlab.cleanlab_remediator.untrustworthy_warning_text.default'),
        ),
        PromptInput(
            name="fallback_text",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.fallback_text.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_remediator.fallback_text.info'),
            value=i18n.t(
                'components.cleanlab.cleanlab_remediator.fallback_text.default'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_remediator.outputs.remediated_response.display_name'),
            name="remediated_response",
            method="remediate_response",
            types=["Message"],
        ),
    ]

    def remediate_response(self) -> Message:
        try:
            if self.score >= self.threshold:
                status_msg = i18n.t('components.cleanlab.cleanlab_remediator.status.accepted',
                                    score=self.score,
                                    threshold=self.threshold)
                self.status = status_msg
                logger.info(i18n.t('components.cleanlab.cleanlab_remediator.logs.response_accepted',
                                   score=self.score,
                                   threshold=self.threshold))

                return Message(
                    text=i18n.t('components.cleanlab.cleanlab_remediator.messages.trusted_response',
                                response=self.response,
                                score=self.score)
                )

            status_msg = i18n.t('components.cleanlab.cleanlab_remediator.status.flagged',
                                score=self.score,
                                threshold=self.threshold)
            self.status = status_msg
            logger.warning(i18n.t('components.cleanlab.cleanlab_remediator.logs.response_flagged',
                                  score=self.score,
                                  threshold=self.threshold))

            if self.show_untrustworthy_response:
                logger.debug(
                    i18n.t('components.cleanlab.cleanlab_remediator.logs.showing_with_warning'))

                parts = [
                    self.response,
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"**{self.untrustworthy_warning_text.strip()}**",
                    i18n.t('components.cleanlab.cleanlab_remediator.messages.trust_score_label',
                           score=self.score),
                ]
                if self.explanation:
                    parts.append(i18n.t('components.cleanlab.cleanlab_remediator.messages.explanation_label',
                                        explanation=self.explanation))
                    logger.debug(
                        i18n.t('components.cleanlab.cleanlab_remediator.logs.explanation_included'))

                return Message(text="\n\n".join(parts))

            logger.debug(
                i18n.t('components.cleanlab.cleanlab_remediator.logs.using_fallback'))
            return Message(text=self.fallback_text)

        except Exception as e:
            error_msg = i18n.t('components.cleanlab.cleanlab_remediator.errors.remediation_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Message(text=self.fallback_text)
