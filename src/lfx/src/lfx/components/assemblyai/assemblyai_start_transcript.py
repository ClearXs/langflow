from pathlib import Path

import assemblyai as aai
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, FileInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AssemblyAITranscriptionJobCreator(Component):
    display_name = i18n.t(
        'components.assemblyai.assemblyai_start_transcript.display_name')
    description = i18n.t(
        'components.assemblyai.assemblyai_start_transcript.description')
    documentation = "https://www.assemblyai.com/docs"
    icon = "AssemblyAI"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.api_key.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.api_key.info'),
            required=True,
        ),
        FileInput(
            name="audio_file",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.audio_file.display_name'),
            file_types=[
                "3ga",
                "8svx",
                "aac",
                "ac3",
                "aif",
                "aiff",
                "alac",
                "amr",
                "ape",
                "au",
                "dss",
                "flac",
                "flv",
                "m4a",
                "m4b",
                "m4p",
                "m4r",
                "mp3",
                "mpga",
                "ogg",
                "oga",
                "mogg",
                "opus",
                "qcp",
                "tta",
                "voc",
                "wav",
                "wma",
                "wv",
                "webm",
                "mts",
                "m2ts",
                "ts",
                "mov",
                "mp2",
                "mp4",
                "m4p",
                "m4v",
                "mxf",
            ],
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.audio_file.info'),
            required=True,
        ),
        MessageTextInput(
            name="audio_file_url",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.audio_file_url.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.audio_file_url.info'),
            advanced=True,
        ),
        DropdownInput(
            name="speech_model",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speech_model.display_name'),
            options=[
                "best",
                "nano",
            ],
            value="best",
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speech_model.info'),
            advanced=True,
        ),
        BoolInput(
            name="language_detection",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.language_detection.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.language_detection.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="language_code",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.language_code.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.language_code.info'),
            advanced=True,
        ),
        BoolInput(
            name="speaker_labels",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speaker_labels.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speaker_labels.info'),
        ),
        MessageTextInput(
            name="speakers_expected",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speakers_expected.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.speakers_expected.info'),
            advanced=True,
        ),
        BoolInput(
            name="punctuate",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.punctuate.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.punctuate.info'),
            advanced=True,
            value=True,
        ),
        BoolInput(
            name="format_text",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.format_text.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.format_text.info'),
            advanced=True,
            value=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.assemblyai.assemblyai_start_transcript.outputs.transcript_id.display_name'),
            name="transcript_id",
            method="create_transcription_job"
        ),
    ]

    def create_transcription_job(self) -> Data:
        """Create a transcription job for an audio file using AssemblyAI."""
        try:
            aai.settings.api_key = self.api_key

            # Convert speakers_expected to int if it's not empty
            speakers_expected = None
            if self.speakers_expected and self.speakers_expected.strip():
                try:
                    speakers_expected = int(self.speakers_expected)
                    logger.debug(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.speakers_expected_set',
                                        count=speakers_expected))
                except ValueError:
                    error_msg = i18n.t(
                        'components.assemblyai.assemblyai_start_transcript.errors.invalid_speakers_count')
                    logger.error(error_msg)
                    self.status = error_msg
                    return Data(data={"error": error_msg})

            language_code = self.language_code or None
            if language_code:
                logger.debug(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.language_code_set',
                                    code=language_code))

            # Build configuration
            self.status = i18n.t(
                'components.assemblyai.assemblyai_start_transcript.status.building_config')

            config = aai.TranscriptionConfig(
                speech_model=self.speech_model,
                language_detection=self.language_detection,
                language_code=language_code,
                speaker_labels=self.speaker_labels,
                speakers_expected=speakers_expected,
                punctuate=self.punctuate,
                format_text=self.format_text,
            )

            logger.debug(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.config_built',
                                model=self.speech_model,
                                language_detection=self.language_detection,
                                speaker_labels=self.speaker_labels))

            # Determine audio source
            audio = None
            if self.audio_file:
                if self.audio_file_url:
                    logger.warning(i18n.t(
                        'components.assemblyai.assemblyai_start_transcript.warnings.url_ignored'))

                # Check if the file exists
                if not Path(self.audio_file).exists():
                    error_msg = i18n.t(
                        'components.assemblyai.assemblyai_start_transcript.errors.file_not_found')
                    logger.error(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.file_not_found',
                                        path=self.audio_file))
                    self.status = error_msg
                    return Data(data={"error": error_msg})

                audio = self.audio_file
                logger.info(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.using_audio_file',
                                   path=self.audio_file))

            elif self.audio_file_url:
                audio = self.audio_file_url
                logger.info(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.using_audio_url',
                                   url=self.audio_file_url))
            else:
                error_msg = i18n.t(
                    'components.assemblyai.assemblyai_start_transcript.errors.no_audio_source')
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Submit transcription job
            self.status = i18n.t(
                'components.assemblyai.assemblyai_start_transcript.status.submitting_job')

            try:
                transcript = aai.Transcriber().submit(audio, config=config)
                logger.info(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.job_submitted',
                                   id=transcript.id))
            except Exception as e:
                logger.debug(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.submission_error'),
                             exc_info=True)
                error_msg = i18n.t('components.assemblyai.assemblyai_start_transcript.errors.submission_failed',
                                   error=str(e))
                logger.error(error_msg)
                self.status = error_msg
                return Data(data={"error": error_msg})

            if transcript.error:
                error_msg = transcript.error
                logger.error(i18n.t('components.assemblyai.assemblyai_start_transcript.logs.transcript_error',
                                    error=error_msg))
                self.status = error_msg
                return Data(data={"error": error_msg})

            result = Data(data={"transcript_id": transcript.id})
            success_msg = i18n.t('components.assemblyai.assemblyai_start_transcript.success.job_created',
                                 id=transcript.id)
            logger.info(success_msg)
            self.status = result

            return result

        except Exception as e:
            error_msg = i18n.t('components.assemblyai.assemblyai_start_transcript.errors.create_job_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})
