import i18n
from cleanlab_tlm import TrustworthyRAG, get_default_evals

from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    MessageTextInput,
    Output,
    SecretStrInput,
)
from lfx.log.logger import logger
from lfx.schema.message import Message


class CleanlabRAGEvaluator(Component):
    """A component that evaluates the quality of RAG (Retrieval-Augmented Generation) outputs using Cleanlab."""

    display_name = i18n.t(
        'components.cleanlab.cleanlab_rag_evaluator.display_name')
    description = i18n.t(
        'components.cleanlab.cleanlab_rag_evaluator.description')
    icon = "Cleanlab"
    name = "CleanlabRAGEvaluator"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.api_key.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.api_key.info'),
            required=True,
        ),
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.model.display_name'),
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
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.model.info'),
            value="gpt-4o-mini",
            required=True,
            advanced=True,
        ),
        DropdownInput(
            name="quality_preset",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.quality_preset.display_name'),
            options=["base", "low", "medium"],
            value="medium",
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.quality_preset.info'),
            required=True,
            advanced=True,
        ),
        MessageTextInput(
            name="context",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.context.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.context.info'),
            required=True,
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.query.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.query.info'),
            required=True,
        ),
        MessageTextInput(
            name="response",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.response.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.response.info'),
            required=True,
        ),
        BoolInput(
            name="run_context_sufficiency",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_context_sufficiency.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_context_sufficiency.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="run_response_groundedness",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_response_groundedness.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_response_groundedness.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="run_response_helpfulness",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_response_helpfulness.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_response_helpfulness.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="run_query_ease",
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_query_ease.display_name'),
            info=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.run_query_ease.info'),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.outputs.response.display_name'),
            name="response_passthrough",
            method="pass_response",
            types=["Message"]
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.outputs.trust_score.display_name'),
            name="trust_score",
            method="get_trust_score",
            types=["number"]
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.outputs.explanation.display_name'),
            name="trust_explanation",
            method="get_trust_explanation",
            types=["Message"]
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.outputs.other_evals.display_name'),
            name="other_scores",
            method="get_other_scores",
            types=["Data"]
        ),
        Output(
            display_name=i18n.t(
                'components.cleanlab.cleanlab_rag_evaluator.outputs.summary.display_name'),
            name="evaluation_summary",
            method="get_evaluation_summary",
            types=["Message"]
        ),
    ]

    def _evaluate_once(self):
        if not hasattr(self, "_cached_result"):
            try:
                self.status = i18n.t(
                    'components.cleanlab.cleanlab_rag_evaluator.status.configuring_evals')
                logger.debug(
                    i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.configuring_evals'))

                default_evals = get_default_evals()
                enabled_names = []

                if self.run_context_sufficiency:
                    enabled_names.append("context_sufficiency")
                if self.run_response_groundedness:
                    enabled_names.append("response_groundedness")
                if self.run_response_helpfulness:
                    enabled_names.append("response_helpfulness")
                if self.run_query_ease:
                    enabled_names.append("query_ease")

                selected_evals = [
                    e for e in default_evals if e.name in enabled_names]

                logger.info(i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.selected_evals',
                                   evals=enabled_names))

                validator = TrustworthyRAG(
                    api_key=self.api_key,
                    quality_preset=self.quality_preset,
                    options={"log": ["explanation"], "model": self.model},
                    evals=selected_evals,
                )

                self.status = i18n.t('components.cleanlab.cleanlab_rag_evaluator.status.running_evals',
                                     evals=[e.name for e in selected_evals])
                logger.info(i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.running_evals',
                                   count=len(selected_evals)))

                self._cached_result = validator.score(
                    query=self.query,
                    context=self.context,
                    response=self.response,
                )

                success_msg = i18n.t(
                    'components.cleanlab.cleanlab_rag_evaluator.success.evaluation_complete')
                self.status = success_msg
                logger.info(success_msg)

            except Exception as e:
                error_msg = i18n.t('components.cleanlab.cleanlab_rag_evaluator.errors.evaluation_failed',
                                   error=str(e))
                self.status = error_msg
                logger.exception(error_msg)
                self._cached_result = {}

        return self._cached_result

    def pass_response(self) -> Message:
        self.status = i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.status.passing_response')
        logger.debug(
            i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.passing_response'))
        return Message(text=self.response)

    def get_trust_score(self) -> float:
        score = self._evaluate_once().get("trustworthiness", {}).get("score", 0.0)
        self.status = i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.status.trust_score', score=score)
        logger.info(i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.logs.trust_score_retrieved', score=score))
        return score

    def get_trust_explanation(self) -> Message:
        explanation = self._evaluate_once().get(
            "trustworthiness", {}).get("log", {}).get("explanation", "")
        self.status = i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.status.explanation_extracted')
        logger.debug(
            i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.explanation_extracted'))
        return Message(text=explanation)

    def get_other_scores(self) -> dict:
        result = self._evaluate_once()

        selected = {
            "context_sufficiency": self.run_context_sufficiency,
            "response_groundedness": self.run_response_groundedness,
            "response_helpfulness": self.run_response_helpfulness,
            "query_ease": self.run_query_ease,
        }

        filtered_scores = {key: result[key]["score"] for key, include in selected.items(
        ) if include and key in result}

        self.status = i18n.t('components.cleanlab.cleanlab_rag_evaluator.status.other_evals_returned',
                             count=len(filtered_scores))
        logger.info(i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.other_evals_retrieved',
                           count=len(filtered_scores)))
        return filtered_scores

    def get_evaluation_summary(self) -> Message:
        result = self._evaluate_once()

        query_text = self.query.strip()
        context_text = self.context.strip()
        response_text = self.response.strip()

        trust = result.get("trustworthiness", {}).get("score", 0.0)
        trust_exp = result.get("trustworthiness", {}).get(
            "log", {}).get("explanation", "")

        selected = {
            "context_sufficiency": self.run_context_sufficiency,
            "response_groundedness": self.run_response_groundedness,
            "response_helpfulness": self.run_response_helpfulness,
            "query_ease": self.run_query_ease,
        }

        other_scores = {key: result[key]["score"] for key, include in selected.items(
        ) if include and key in result}

        metrics = i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.summary.trustworthiness', score=trust)
        if trust_exp:
            metrics += "\n" + i18n.t('components.cleanlab.cleanlab_rag_evaluator.summary.explanation',
                                     explanation=trust_exp)
        if other_scores:
            metrics += "\n" + "\n".join(
                i18n.t('components.cleanlab.cleanlab_rag_evaluator.summary.metric',
                       name=k.replace('_', ' ').title(),
                       score=v)
                for k, v in other_scores.items()
            )

        summary = i18n.t('components.cleanlab.cleanlab_rag_evaluator.summary.full',
                         query=query_text,
                         context=context_text,
                         response=response_text,
                         metrics=metrics)

        self.status = i18n.t(
            'components.cleanlab.cleanlab_rag_evaluator.status.summary_built')
        logger.info(
            i18n.t('components.cleanlab.cleanlab_rag_evaluator.logs.summary_built'))
        return Message(text=summary)
