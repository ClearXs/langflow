import base64
import os
import i18n
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from docling_core.types.doc import DoclingDocument
from pydantic import ValidationError

from lfx.base.data import BaseFileComponent
from lfx.inputs import IntInput, NestedDictInput, StrInput
from lfx.inputs.inputs import FloatInput
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.utils.util import transform_localhost_url


class DoclingRemoteComponent(BaseFileComponent):
    display_name = "Docling Serve"
    description = i18n.t('components.docling.docling_remote.description')
    documentation = "https://docling-project.github.io/docling/"
    trace_type = "tool"
    icon = "Docling"
    name = "DoclingRemote"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    MAX_500_RETRIES = 5

    # https://docling-project.github.io/docling/usage/supported_formats/
    VALID_EXTENSIONS = [
        "adoc",
        "asciidoc",
        "asc",
        "bmp",
        "csv",
        "dotx",
        "dotm",
        "docm",
        "docx",
        "htm",
        "html",
        "jpeg",
        "json",
        "md",
        "pdf",
        "png",
        "potx",
        "ppsx",
        "pptm",
        "potm",
        "ppsm",
        "pptx",
        "tiff",
        "txt",
        "xls",
        "xlsx",
        "xhtml",
        "xml",
        "webp",
    ]

    inputs = [
        *BaseFileComponent.get_base_inputs(),
        StrInput(
            name="api_url",
            display_name=i18n.t(
                'components.docling.docling_remote.api_url.display_name'),
            info=i18n.t('components.docling.docling_remote.api_url.info'),
            required=True,
        ),
        IntInput(
            name="max_concurrency",
            display_name=i18n.t(
                'components.docling.docling_remote.max_concurrency.display_name'),
            info=i18n.t(
                'components.docling.docling_remote.max_concurrency.info'),
            advanced=True,
            value=2,
        ),
        FloatInput(
            name="max_poll_timeout",
            display_name=i18n.t(
                'components.docling.docling_remote.max_poll_timeout.display_name'),
            info=i18n.t(
                'components.docling.docling_remote.max_poll_timeout.info'),
            advanced=True,
            value=3600,
        ),
        NestedDictInput(
            name="api_headers",
            display_name=i18n.t(
                'components.docling.docling_remote.api_headers.display_name'),
            advanced=True,
            required=False,
            info=i18n.t('components.docling.docling_remote.api_headers.info'),
        ),
        NestedDictInput(
            name="docling_serve_opts",
            display_name=i18n.t(
                'components.docling.docling_remote.docling_serve_opts.display_name'),
            advanced=True,
            required=False,
            info=i18n.t(
                'components.docling.docling_remote.docling_serve_opts.info'),
        ),
    ]

    outputs = [
        *BaseFileComponent.get_base_outputs(),
    ]

    def process_files(self, file_list: list[BaseFileComponent.BaseFile]) -> list[BaseFileComponent.BaseFile]:
        # Transform localhost URLs to container-accessible hosts when running in a container
        transformed_url = transform_localhost_url(self.api_url)
        base_url = f"{transformed_url}/v1"

        def _convert_document(client: httpx.Client, file_path: Path, options: dict[str, Any]) -> Data | None:
            """Convert a single document using Docling Serve API.

            Args:
                client: HTTP client instance.
                file_path: Path to the file to convert.
                options: Conversion options.

            Returns:
                Data | None: Processed document data or None if failed.

            Raises:
                RuntimeError: If processing times out or fails.
            """
            logger.info(i18n.t('components.docling.docling_remote.logs.converting_document',
                               filename=file_path.name))

            encoded_doc = base64.b64encode(file_path.read_bytes()).decode()
            payload = {
                "options": options,
                "sources": [{"kind": "file", "base64_string": encoded_doc, "filename": file_path.name}],
            }

            try:
                logger.debug(
                    i18n.t('components.docling.docling_remote.logs.sending_conversion_request'))
                response = client.post(
                    f"{base_url}/convert/source/async", json=payload)
                response.raise_for_status()
                task = response.json()
                task_id = task['task_id']
                logger.info(i18n.t('components.docling.docling_remote.logs.task_created',
                                   task_id=task_id))
            except Exception as e:
                error_msg = i18n.t('components.docling.docling_remote.errors.conversion_request_failed',
                                   error=str(e))
                logger.error(error_msg)
                self.log(error_msg)
                raise

            http_failures = 0
            retry_status_start = 500
            retry_status_end = 600
            start_wait_time = time.monotonic()
            poll_count = 0

            while task["task_status"] not in ("success", "failure"):
                # Check if processing exceeds the maximum poll timeout
                processing_time = time.monotonic() - start_wait_time
                if processing_time >= self.max_poll_timeout:
                    error_msg = i18n.t('components.docling.docling_remote.errors.processing_timeout',
                                       processing_time=processing_time,
                                       max_poll_timeout=self.max_poll_timeout)
                    logger.error(error_msg)
                    self.log(error_msg)
                    raise RuntimeError(error_msg)

                # Call for a new status update
                time.sleep(2)
                poll_count += 1

                logger.debug(i18n.t('components.docling.docling_remote.logs.polling_status',
                                    poll_count=poll_count,
                                    task_id=task_id))

                response = client.get(
                    f"{base_url}/status/poll/{task['task_id']}")

                # Check if the status call gets into 5xx errors and retry
                if retry_status_start <= response.status_code < retry_status_end:
                    http_failures += 1
                    logger.warning(i18n.t('components.docling.docling_remote.logs.http_error',
                                          status_code=response.status_code,
                                          failures=http_failures,
                                          max_retries=self.MAX_500_RETRIES))

                    if http_failures > self.MAX_500_RETRIES:
                        error_msg = i18n.t('components.docling.docling_remote.errors.too_many_http_errors',
                                           status_code=response.status_code,
                                           max_retries=self.MAX_500_RETRIES)
                        logger.error(error_msg)
                        self.log(error_msg)
                        return None
                    continue

                # Update task status
                task = response.json()
                logger.debug(i18n.t('components.docling.docling_remote.logs.task_status',
                                    status=task["task_status"]))

            if task["task_status"] == "failure":
                error_msg = i18n.t('components.docling.docling_remote.errors.task_failed',
                                   task_id=task_id)
                logger.error(error_msg)
                self.log(error_msg)
                return None

            logger.info(i18n.t('components.docling.docling_remote.logs.task_completed',
                               task_id=task_id,
                               processing_time=time.monotonic() - start_wait_time))

            try:
                result_resp = client.get(
                    f"{base_url}/result/{task['task_id']}")
                result_resp.raise_for_status()
                result = result_resp.json()
            except Exception as e:
                error_msg = i18n.t('components.docling.docling_remote.errors.result_retrieval_failed',
                                   error=str(e))
                logger.error(error_msg)
                self.log(error_msg)
                raise

            if "json_content" not in result["document"] or result["document"]["json_content"] is None:
                warning_msg = i18n.t(
                    'components.docling.docling_remote.logs.no_json_content')
                logger.warning(warning_msg)
                self.log(warning_msg)
                return None

            try:
                doc = DoclingDocument.model_validate(
                    result["document"]["json_content"])
                logger.info(i18n.t('components.docling.docling_remote.logs.document_validated',
                                   filename=file_path.name))
                return Data(data={"doc": doc, "file_path": str(file_path)})
            except ValidationError as e:
                error_msg = i18n.t('components.docling.docling_remote.errors.validation_failed',
                                   error=str(e))
                logger.error(error_msg)
                self.log(error_msg)
                return None

        docling_options = {
            "to_formats": ["json"],
            "image_export_mode": "placeholder",
            **(self.docling_serve_opts or {}),
        }

        logger.debug(i18n.t('components.docling.docling_remote.logs.docling_options',
                            options=str(docling_options)))

        processed_data: list[Data | None] = []
        logger.info(i18n.t('components.docling.docling_remote.logs.starting_processing',
                           count=len(file_list),
                           concurrency=self.max_concurrency))

        with (
            httpx.Client(headers=self.api_headers) as client,
            ThreadPoolExecutor(max_workers=self.max_concurrency) as executor,
        ):
            futures: list[tuple[int, Future]] = []
            for i, file in enumerate(file_list):
                if file.path is None:
                    logger.warning(i18n.t('components.docling.docling_remote.logs.skipping_no_path',
                                          index=i))
                    processed_data.append(None)
                    continue

                logger.debug(i18n.t('components.docling.docling_remote.logs.submitting_file',
                                    index=i,
                                    filename=file.path.name))
                futures.append(
                    (i, executor.submit(_convert_document, client, file.path, docling_options)))

            logger.info(i18n.t('components.docling.docling_remote.logs.waiting_for_results',
                               count=len(futures)))

            for _index, future in futures:
                try:
                    result_data = future.result()
                    processed_data.append(result_data)
                    if result_data:
                        logger.debug(
                            i18n.t('components.docling.docling_remote.logs.file_processed_successfully'))
                except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError) as exc:
                    error_msg = i18n.t('components.docling.docling_remote.errors.processing_failed',
                                       error=str(exc))
                    logger.exception(error_msg)
                    self.log(error_msg)
                    raise

        success_count = sum(1 for d in processed_data if d is not None)
        logger.info(i18n.t('components.docling.docling_remote.logs.processing_completed',
                           success=success_count,
                           total=len(file_list)))

        return self.rollup_data(file_list, processed_data)
