import assemblyai as aai
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, FloatInput, IntInput, MultilineInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AssemblyAILeMUR(Component):
    display_name = i18n.t(
        'components.assemblyai.assemblyai_lemur.display_name')
    description = i18n.t('components.assemblyai.assemblyai_lemur.description')
    documentation = "https://www.assemblyai.com/docs/lemur"
    icon = "AssemblyAI"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.api_key.display_name'),
            info=i18n.t('components.assemblyai.assemblyai_lemur.api_key.info'),
            advanced=False,
            required=True,
        ),
        DataInput(
            name="transcription_result",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.transcription_result.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.transcription_result.info'),
            required=True,
        ),
        MultilineInput(
            name="prompt",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.prompt.display_name'),
            info=i18n.t('components.assemblyai.assemblyai_lemur.prompt.info'),
            required=True
        ),
        DropdownInput(
            name="final_model",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.final_model.display_name'),
            options=["claude3_5_sonnet", "claude3_opus",
                     "claude3_haiku", "claude3_sonnet"],
            value="claude3_5_sonnet",
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.final_model.info'),
            advanced=True,
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.temperature.display_name'),
            advanced=True,
            value=0.0,
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.temperature.info'),
        ),
        IntInput(
            name="max_output_size",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.max_output_size.display_name'),
            advanced=True,
            value=2000,
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.max_output_size.info'),
        ),
        DropdownInput(
            name="endpoint",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.endpoint.display_name'),
            options=["task", "summary", "question-answer"],
            value="task",
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.endpoint.info'),
            advanced=True,
        ),
        MultilineInput(
            name="questions",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.questions.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.questions.info'),
            advanced=True,
        ),
        MultilineInput(
            name="transcript_ids",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.transcript_ids.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_lemur.transcript_ids.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.assemblyai.assemblyai_lemur.outputs.lemur_response.display_name'),
            name="lemur_response",
            method="run_lemur"
        ),
    ]

    def run_lemur(self) -> Data:
        """Use the LeMUR task endpoint to input the LLM prompt."""
        try:
            aai.settings.api_key = self.api_key

            # Validate inputs
            if not self.transcription_result and not self.transcript_ids:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_lemur.errors.no_input_provided')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            if self.transcription_result and self.transcription_result.data.get("error"):
                # error message from the previous step
                error_msg = self.transcription_result.data["error"]
                logger.warning(i18n.t('components.assemblyai.assemblyai_lemur.warnings.previous_step_error',
                                      error=error_msg))
                self.status = error_msg
                return self.transcription_result

            if self.endpoint == "task" and not self.prompt:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_lemur.errors.no_prompt_for_task')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            if self.endpoint == "question-answer" and not self.questions:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_lemur.errors.no_questions_for_qa')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Check for valid transcripts
            transcript_ids = None
            if self.transcription_result and "id" in self.transcription_result.data:
                transcript_ids = [self.transcription_result.data["id"]]
                logger.debug(i18n.t('components.assemblyai.assemblyai_lemur.logs.transcript_id_from_result',
                                    id=transcript_ids[0]))
            elif self.transcript_ids:
                transcript_ids = self.transcript_ids.split(",") or []
                transcript_ids = [t.strip() for t in transcript_ids]
                logger.debug(i18n.t('components.assemblyai.assemblyai_lemur.logs.transcript_ids_provided',
                                    count=len(transcript_ids)))

            if not transcript_ids:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_lemur.errors.no_valid_transcript_ids')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Get TranscriptGroup and check if there is any error
            self.status = i18n.t(
                'components.assemblyai.assemblyai_lemur.status.waiting_for_transcripts')

            transcript_group = aai.TranscriptGroup(
                transcript_ids=transcript_ids)
            transcript_group, failures = transcript_group.wait_for_completion(
                return_failures=True)

            if failures:
                error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.transcription_failed',
                                   error=str(failures[0]))
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            for t in transcript_group.transcripts:
                if t.status == aai.TranscriptStatus.error:
                    logger.error(i18n.t('components.assemblyai.assemblyai_lemur.logs.transcript_error',
                                        id=t.id, error=t.error))
                    self.status = t.error
                    return Data(data={"error": t.error})

            # Perform LeMUR action
            self.status = i18n.t('components.assemblyai.assemblyai_lemur.status.performing_lemur_action',
                                 endpoint=self.endpoint)

            try:
                response = self.perform_lemur_action(
                    transcript_group, self.endpoint)

                success_msg = i18n.t('components.assemblyai.assemblyai_lemur.success.lemur_completed',
                                     endpoint=self.endpoint)
                logger.info(success_msg)
                self.status = success_msg

                result = Data(data=response)
                return result

            except Exception as e:
                logger.debug(i18n.t(
                    'components.assemblyai.assemblyai_lemur.logs.lemur_error'), exc_info=True)
                error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.lemur_action_failed',
                                   error=str(e))
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.run_lemur_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})

    def perform_lemur_action(self, transcript_group: aai.TranscriptGroup, endpoint: str) -> dict:
        """Perform the specified LeMUR action."""
        try:
            logger.info(i18n.t('components.assemblyai.assemblyai_lemur.logs.performing_action',
                               endpoint=endpoint))

            if endpoint == "task":
                result = transcript_group.lemur.task(
                    prompt=self.prompt,
                    final_model=self.get_final_model(self.final_model),
                    temperature=self.temperature,
                    max_output_size=self.max_output_size,
                )
                logger.debug(
                    i18n.t('components.assemblyai.assemblyai_lemur.logs.task_completed'))

            elif endpoint == "summary":
                result = transcript_group.lemur.summarize(
                    final_model=self.get_final_model(self.final_model),
                    temperature=self.temperature,
                    max_output_size=self.max_output_size,
                )
                logger.debug(
                    i18n.t('components.assemblyai.assemblyai_lemur.logs.summary_completed'))

            elif endpoint == "question-answer":
                questions = self.questions.split(",")
                questions = [aai.LemurQuestion(
                    question=q.strip()) for q in questions]
                logger.debug(i18n.t('components.assemblyai.assemblyai_lemur.logs.processing_questions',
                                    count=len(questions)))

                result = transcript_group.lemur.question(
                    questions=questions,
                    final_model=self.get_final_model(self.final_model),
                    temperature=self.temperature,
                    max_output_size=self.max_output_size,
                )
                logger.debug(
                    i18n.t('components.assemblyai.assemblyai_lemur.logs.qa_completed'))

            else:
                error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.unsupported_endpoint',
                                   endpoint=endpoint)
                raise ValueError(error_msg)

            return result.dict()

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.action_execution_failed',
                               endpoint=endpoint, error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    def get_final_model(self, model_name: str) -> aai.LemurModel:
        """Get the LeMUR model based on model name."""
        try:
            model_map = {
                "claude3_5_sonnet": aai.LemurModel.claude3_5_sonnet,
                "claude3_opus": aai.LemurModel.claude3_opus,
                "claude3_haiku": aai.LemurModel.claude3_haiku,
                "claude3_sonnet": aai.LemurModel.claude3_sonnet,
            }

            if model_name not in model_map:
                error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.unsupported_model',
                                   model=model_name)
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.assemblyai.assemblyai_lemur.logs.model_selected',
                                model=model_name))
            return model_map[model_name]

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_lemur.errors.model_selection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
