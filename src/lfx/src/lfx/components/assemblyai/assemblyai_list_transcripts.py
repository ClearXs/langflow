import os
import assemblyai as aai
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AssemblyAIListTranscripts(Component):
    display_name = i18n.t(
        'components.assemblyai.assemblyai_list_transcripts.display_name')
    description = i18n.t(
        'components.assemblyai.assemblyai_list_transcripts.description')
    documentation = "https://www.assemblyai.com/docs"
    icon = "AssemblyAI"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.api_key.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.api_key.info'),
            required=True,
        ),
        IntInput(
            name="limit",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.limit.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.limit.info'),
            value=20,
        ),
        DropdownInput(
            name="status_filter",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.status_filter.display_name'),
            options=["all", "queued", "processing", "completed", "error"],
            value="all",
            info=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.status_filter.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="created_on",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.created_on.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.created_on.info'),
            advanced=True,
        ),
        BoolInput(
            name="throttled_only",
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.throttled_only.display_name'),
            info=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.throttled_only.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.outputs.transcript_list.display_name'),
            name="transcript_list",
            method="list_transcripts"
        ),
    ]

    def list_transcripts(self) -> list[Data]:
        """List transcripts from AssemblyAI with optional filters."""
        try:
            aai.settings.api_key = self.api_key

            # Build parameters
            self.status = i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.status.building_parameters')

            params = aai.ListTranscriptParameters()

            if self.limit:
                params.limit = self.limit
                logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.limit_set',
                                    limit=self.limit))

            if self.status_filter != "all":
                params.status = self.status_filter
                logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.status_filter_set',
                                    status=self.status_filter))

            if self.created_on and self.created_on.text:
                params.created_on = self.created_on.text
                logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.created_on_set',
                                    date=self.created_on.text))

            if self.throttled_only:
                params.throttled_only = True
                logger.debug(i18n.t(
                    'components.assemblyai.assemblyai_list_transcripts.logs.throttled_only_enabled'))

            transcriber = aai.Transcriber()

            def convert_page_to_data_list(page):
                """Convert a page of transcripts to Data objects."""
                return [Data(**t.dict()) for t in page.transcripts]

            if self.limit == 0:
                # Paginate over all pages
                self.status = i18n.t(
                    'components.assemblyai.assemblyai_list_transcripts.status.fetching_all_transcripts')
                logger.info(i18n.t(
                    'components.assemblyai.assemblyai_list_transcripts.logs.fetching_all_pages'))

                params.limit = 100
                page = transcriber.list_transcripts(params)
                transcripts = convert_page_to_data_list(page)

                page_count = 1
                logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.page_fetched',
                                    page=page_count, count=len(page.transcripts)))

                while page.page_details.before_id_of_prev_url is not None:
                    params.before_id = page.page_details.before_id_of_prev_url
                    page = transcriber.list_transcripts(params)
                    transcripts.extend(convert_page_to_data_list(page))
                    page_count += 1
                    logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.page_fetched',
                                        page=page_count, count=len(page.transcripts)))

                logger.info(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.all_pages_fetched',
                                   pages=page_count, total=len(transcripts)))
            else:
                # Just one page
                self.status = i18n.t('components.assemblyai.assemblyai_list_transcripts.status.fetching_transcripts',
                                     limit=self.limit)
                logger.info(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.fetching_single_page',
                                   limit=self.limit))

                page = transcriber.list_transcripts(params)
                transcripts = convert_page_to_data_list(page)

                logger.debug(i18n.t('components.assemblyai.assemblyai_list_transcripts.logs.single_page_fetched',
                                    count=len(transcripts)))

            success_msg = i18n.t('components.assemblyai.assemblyai_list_transcripts.success.transcripts_retrieved',
                                 count=len(transcripts))
            logger.info(success_msg)
            self.status = transcripts

            return transcripts

        except Exception as e:
            logger.debug(i18n.t(
                'components.assemblyai.assemblyai_list_transcripts.logs.list_error'), exc_info=True)
            error_msg = i18n.t('components.assemblyai.assemblyai_list_transcripts.errors.list_failed',
                               error=str(e))
            logger.error(error_msg)
            error_data = Data(data={"error": error_msg})
            self.status = [error_data]
            return [error_data]
