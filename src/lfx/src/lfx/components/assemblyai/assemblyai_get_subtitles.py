import assemblyai as aai
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, IntInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AssemblyAIGetSubtitles(Component):
    display_name = i18n.t(
        'components.assemblyai.assemblyai_get_subtitles.display_name')
    description = i18n.t(
        'components.assemblyai.assemblyai_get_subtitles.description')
    documentation: str = "https://www.assemblyai.com/docs"
    icon = "AssemblyAI"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.api_key.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.api_key.info'),
            required=True,
        ),
        DataInput(
            name="transcription_result",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.transcription_result.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.transcription_result.info'),
            required=True,
        ),
        DropdownInput(
            name="subtitle_format",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.subtitle_format.display_name'),
            options=["srt", "vtt"],
            value="srt",
            info=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.subtitle_format.info'),
        ),
        IntInput(
            name="chars_per_caption",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.chars_per_caption.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.chars_per_caption.info'),
            value=0,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.outputs.subtitles.display_name'),
            name="subtitles",
            method="get_subtitles"
        ),
    ]

    def get_subtitles(self) -> Data:
        """Get subtitles from AssemblyAI transcription result."""
        try:
            aai.settings.api_key = self.api_key

            # Check if it's an error message from the previous step
            if self.transcription_result.data.get("error"):
                error_msg = self.transcription_result.data["error"]
                logger.warning(i18n.t('components.assemblyai.assemblyai_get_subtitles.warnings.previous_step_error',
                                      error=error_msg))
                self.status = error_msg
                return self.transcription_result

            self.status = i18n.t(
                'components.assemblyai.assemblyai_get_subtitles.status.retrieving_transcript')

            try:
                transcript_id = self.transcription_result.data["id"]
                logger.debug(i18n.t('components.assemblyai.assemblyai_get_subtitles.logs.fetching_transcript',
                                    id=transcript_id))
                transcript = aai.Transcript.get_by_id(transcript_id)
            except KeyError as e:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_get_subtitles.errors.transcript_id_not_found')
                logger.error(error_msg, exc_info=True)
                self.status = error_msg
                return Data(data={"error": error_msg})
            except Exception as e:
                error_msg = i18n.t('components.assemblyai.assemblyai_get_subtitles.errors.get_transcript_failed',
                                   error=str(e))
                logger.error(error_msg, exc_info=True)
                self.status = error_msg
                return Data(data={"error": error_msg})

            if transcript.status == aai.TranscriptStatus.completed:
                self.status = i18n.t('components.assemblyai.assemblyai_get_subtitles.status.exporting_subtitles',
                                     format=self.subtitle_format.upper())

                subtitles = None
                chars_per_caption = self.chars_per_caption if self.chars_per_caption > 0 else None

                try:
                    if self.subtitle_format == "srt":
                        subtitles = transcript.export_subtitles_srt(
                            chars_per_caption)
                        logger.debug(
                            i18n.t('components.assemblyai.assemblyai_get_subtitles.logs.srt_exported'))
                    else:
                        subtitles = transcript.export_subtitles_vtt(
                            chars_per_caption)
                        logger.debug(
                            i18n.t('components.assemblyai.assemblyai_get_subtitles.logs.vtt_exported'))
                except Exception as e:
                    error_msg = i18n.t('components.assemblyai.assemblyai_get_subtitles.errors.export_failed',
                                       format=self.subtitle_format.upper(), error=str(e))
                    logger.error(error_msg, exc_info=True)
                    self.status = error_msg
                    return Data(data={"error": error_msg})

                result = Data(
                    subtitles=subtitles,
                    format=self.subtitle_format,
                    transcript_id=transcript_id,
                    chars_per_caption=chars_per_caption,
                )

                success_msg = i18n.t('components.assemblyai.assemblyai_get_subtitles.success.subtitles_exported',
                                     format=self.subtitle_format.upper())
                logger.info(success_msg)
                self.status = success_msg
                return result

            # Transcript is not completed
            error_msg = transcript.error or i18n.t('components.assemblyai.assemblyai_get_subtitles.errors.transcript_not_completed',
                                                   status=transcript.status)
            logger.error(i18n.t('components.assemblyai.assemblyai_get_subtitles.logs.transcript_error',
                                status=transcript.status, error=error_msg))
            self.status = error_msg
            return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_get_subtitles.errors.get_subtitles_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})
