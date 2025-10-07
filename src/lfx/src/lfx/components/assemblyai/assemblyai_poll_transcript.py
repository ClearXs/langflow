import assemblyai as aai
import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import DataInput, FloatInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AssemblyAITranscriptionJobPoller(Component):
    display_name = i18n.t(
        'components.assemblyai.assemblyai_poll_transcript.display_name')
    description = i18n.t(
        'components.assemblyai.assemblyai_poll_transcript.description')
    documentation = "https://www.assemblyai.com/docs"
    icon = "AssemblyAI"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.api_key.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.api_key.info'),
            required=True,
        ),
        DataInput(
            name="transcript_id",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.transcript_id.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.transcript_id.info'),
            required=True,
        ),
        FloatInput(
            name="polling_interval",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.polling_interval.display_name'),
            value=3.0,
            info=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.polling_interval.info'),
            advanced=True,
            range_spec=RangeSpec(min=3, max=30),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.assemblyai.assemblyai_poll_transcript.outputs.transcription_result.display_name'),
            name="transcription_result",
            method="poll_transcription_job"
        ),
    ]

    def poll_transcription_job(self) -> Data:
        """Polls the transcription status until completion and returns the Data."""
        try:
            aai.settings.api_key = self.api_key
            aai.settings.polling_interval = self.polling_interval

            logger.debug(i18n.t('components.assemblyai.assemblyai_poll_transcript.logs.polling_interval_set',
                                interval=self.polling_interval))

            # Check if it's an error message from the previous step
            if self.transcript_id.data.get("error"):
                error_msg = self.transcript_id.data["error"]
                logger.warning(i18n.t('components.assemblyai.assemblyai_poll_transcript.warnings.previous_step_error',
                                      error=error_msg))
                self.status = error_msg
                return self.transcript_id

            # Get transcript ID
            if "transcript_id" not in self.transcript_id.data:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_poll_transcript.errors.transcript_id_not_found')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            transcript_id = self.transcript_id.data["transcript_id"]

            self.status = i18n.t('components.assemblyai.assemblyai_poll_transcript.status.polling_transcript',
                                 id=transcript_id)
            logger.info(i18n.t('components.assemblyai.assemblyai_poll_transcript.logs.polling_started',
                               id=transcript_id))

            try:
                transcript = aai.Transcript.get_by_id(transcript_id)
            except Exception as e:
                error_msg = i18n.t('components.assemblyai.assemblyai_poll_transcript.errors.get_transcript_failed',
                                   error=str(e))
                logger.error(error_msg, exc_info=True)
                self.status = error_msg
                return Data(data={"error": error_msg})

            if transcript.status == aai.TranscriptStatus.completed:
                logger.info(i18n.t('components.assemblyai.assemblyai_poll_transcript.logs.transcript_completed',
                                   id=transcript_id))

                self.status = i18n.t(
                    'components.assemblyai.assemblyai_poll_transcript.status.processing_result')

                try:
                    json_response = transcript.json_response
                    text = json_response.pop("text", None)
                    utterances = json_response.pop("utterances", None)
                    tid = json_response.pop("id", None)

                    # Build sorted data with text and utterances first
                    sorted_data = {
                        "text": text,
                        "utterances": utterances,
                        "id": tid
                    }
                    sorted_data.update(json_response)

                    data = Data(data=sorted_data)

                    success_msg = i18n.t('components.assemblyai.assemblyai_poll_transcript.success.transcription_completed',
                                         id=transcript_id,
                                         length=len(text) if text else 0)
                    logger.info(success_msg)
                    self.status = data

                    return data

                except Exception as e:
                    error_msg = i18n.t('components.assemblyai.assemblyai_poll_transcript.errors.process_result_failed',
                                       error=str(e))
                    logger.exception(error_msg)
                    self.status = error_msg
                    return Data(data={"error": error_msg})

            # Transcript is not completed
            error_msg = transcript.error or i18n.t('components.assemblyai.assemblyai_poll_transcript.errors.transcript_not_completed',
                                                   status=transcript.status)
            logger.error(i18n.t('components.assemblyai.assemblyai_poll_transcript.logs.transcript_error',
                                id=transcript_id,
                                status=transcript.status,
                                error=error_msg))
            self.status = error_msg
            return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_poll_transcript.errors.poll_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})
