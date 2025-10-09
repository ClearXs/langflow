import i18n
import time
from multiprocessing import Queue, get_context
from queue import Empty

from lfx.base.data import BaseFileComponent
from lfx.base.data.docling_utils import _serialize_pydantic_model, docling_worker
from lfx.inputs import BoolInput, DropdownInput, HandleInput, StrInput
from lfx.log.logger import logger
from lfx.schema import Data


class DoclingInlineComponent(BaseFileComponent):
    display_name = "Docling"
    description = i18n.t('components.docling.docling_inline.description')
    documentation = "https://docling-project.github.io/docling/"
    trace_type = "tool"
    icon = "Docling"
    name = "DoclingInline"

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
        DropdownInput(
            name="pipeline",
            display_name=i18n.t(
                'components.docling.docling_inline.pipeline.display_name'),
            info=i18n.t('components.docling.docling_inline.pipeline.info'),
            options=["standard", "vlm"],
            value="standard",
        ),
        DropdownInput(
            name="ocr_engine",
            display_name=i18n.t(
                'components.docling.docling_inline.ocr_engine.display_name'),
            info=i18n.t('components.docling.docling_inline.ocr_engine.info'),
            options=["None", "easyocr", "tesserocr", "rapidocr", "ocrmac"],
            value="None",
        ),
        BoolInput(
            name="do_picture_classification",
            display_name=i18n.t(
                'components.docling.docling_inline.do_picture_classification.display_name'),
            info=i18n.t(
                'components.docling.docling_inline.do_picture_classification.info'),
            value=False,
        ),
        HandleInput(
            name="pic_desc_llm",
            display_name=i18n.t(
                'components.docling.docling_inline.pic_desc_llm.display_name'),
            info=i18n.t('components.docling.docling_inline.pic_desc_llm.info'),
            input_types=["LanguageModel"],
            required=False,
        ),
        StrInput(
            name="pic_desc_prompt",
            display_name=i18n.t(
                'components.docling.docling_inline.pic_desc_prompt.display_name'),
            value="Describe the image in three sentences. Be concise and accurate.",
            info=i18n.t(
                'components.docling.docling_inline.pic_desc_prompt.info'),
            advanced=True,
        ),
        # TODO: expose more Docling options
    ]

    outputs = [
        *BaseFileComponent.get_base_outputs(),
    ]

    def _wait_for_result_with_process_monitoring(self, queue: Queue, proc, timeout: int = 300):
        """Wait for result from queue while monitoring process health.

        Handles cases where process crashes without sending result.

        Args:
            queue: The queue to receive results from.
            proc: The worker process to monitor.
            timeout: Maximum time to wait in seconds.

        Returns:
            The result from the worker process.

        Raises:
            RuntimeError: If the worker process crashes.
            TimeoutError: If the timeout is reached.
        """
        start_time = time.time()
        logger.debug(i18n.t('components.docling.docling_inline.logs.monitoring_process',
                            timeout=timeout))

        while time.time() - start_time < timeout:
            # Check if process is still alive
            if not proc.is_alive():
                # Process died, try to get any result it might have sent
                try:
                    result = queue.get_nowait()
                except Empty:
                    # Process died without sending result
                    error_msg = i18n.t('components.docling.docling_inline.errors.process_crashed',
                                       exit_code=proc.exitcode)
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from None
                else:
                    logger.info(
                        i18n.t('components.docling.docling_inline.logs.process_completed'))
                    self.log(
                        i18n.t('components.docling.docling_inline.logs.process_completed'))
                    return result

            # Poll the queue instead of blocking
            try:
                result = queue.get(timeout=1)
            except Empty:
                # No result yet, continue monitoring
                continue
            else:
                logger.info(
                    i18n.t('components.docling.docling_inline.logs.result_received'))
                self.log(
                    i18n.t('components.docling.docling_inline.logs.result_received'))
                return result

        # Overall timeout reached
        error_msg = i18n.t('components.docling.docling_inline.errors.process_timeout',
                           timeout=timeout)
        logger.error(error_msg)
        raise TimeoutError(error_msg)

    def _terminate_process_gracefully(self, proc, timeout_terminate: int = 10, timeout_kill: int = 5):
        """Terminate process gracefully with escalating signals.

        First tries SIGTERM, then SIGKILL if needed.

        Args:
            proc: The process to terminate.
            timeout_terminate: Time to wait after SIGTERM.
            timeout_kill: Time to wait after SIGKILL.
        """
        if not proc.is_alive():
            return

        logger.info(
            i18n.t('components.docling.docling_inline.logs.terminating_sigterm'))
        self.log(i18n.t('components.docling.docling_inline.logs.terminating_sigterm'))
        proc.terminate()  # Send SIGTERM
        proc.join(timeout=timeout_terminate)

        if proc.is_alive():
            logger.warning(
                i18n.t('components.docling.docling_inline.logs.terminating_sigkill'))
            self.log(
                i18n.t('components.docling.docling_inline.logs.terminating_sigkill'))
            proc.kill()  # Send SIGKILL
            proc.join(timeout=timeout_kill)

            if proc.is_alive():
                warning_msg = i18n.t(
                    'components.docling.docling_inline.logs.process_still_alive')
                logger.warning(warning_msg)
                self.log(warning_msg)

    def process_files(self, file_list: list[BaseFileComponent.BaseFile]) -> list[BaseFileComponent.BaseFile]:
        """Process files using Docling.

        Args:
            file_list: List of files to process.

        Returns:
            list[BaseFileComponent.BaseFile]: List of processed files with document data.

        Raises:
            ImportError: If Docling or required dependencies are not installed.
            RuntimeError: If processing fails.
        """
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
            logger.debug(
                i18n.t('components.docling.docling_inline.logs.docling_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.docling.docling_inline.errors.docling_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        file_paths = [file.path for file in file_list if file.path]

        if not file_paths:
            logger.info(
                i18n.t('components.docling.docling_inline.logs.no_files'))
            self.log(i18n.t('components.docling.docling_inline.logs.no_files'))
            return file_list

        logger.info(i18n.t('components.docling.docling_inline.logs.processing_files',
                           count=len(file_paths)))

        pic_desc_config: dict | None = None
        if self.pic_desc_llm is not None:
            pic_desc_config = _serialize_pydantic_model(self.pic_desc_llm)
            logger.debug(
                i18n.t('components.docling.docling_inline.logs.pic_desc_enabled'))

        ctx = get_context("spawn")
        queue: Queue = ctx.Queue()

        logger.debug(i18n.t('components.docling.docling_inline.logs.creating_worker',
                            pipeline=self.pipeline,
                            ocr_engine=self.ocr_engine))

        proc = ctx.Process(
            target=docling_worker,
            kwargs={
                "file_paths": file_paths,
                "queue": queue,
                "pipeline": self.pipeline,
                "ocr_engine": self.ocr_engine,
                "do_picture_classification": self.do_picture_classification,
                "pic_desc_config": pic_desc_config,
                "pic_desc_prompt": self.pic_desc_prompt,
            },
        )

        result = None
        proc.start()
        logger.info(
            i18n.t('components.docling.docling_inline.logs.worker_started'))

        try:
            result = self._wait_for_result_with_process_monitoring(
                queue, proc, timeout=300)
        except KeyboardInterrupt:
            logger.info(
                i18n.t('components.docling.docling_inline.logs.cancelled_by_user'))
            self.log(
                i18n.t('components.docling.docling_inline.logs.cancelled_by_user'))
            result = []
        except Exception as e:
            error_msg = i18n.t('components.docling.docling_inline.errors.processing_error',
                               error=str(e))
            logger.exception(error_msg)
            self.log(error_msg)
            raise
        finally:
            # Improved cleanup with graceful termination
            try:
                self._terminate_process_gracefully(proc)
            finally:
                # Always close and cleanup queue resources
                try:
                    queue.close()
                    queue.join_thread()
                except Exception as e:  # noqa: BLE001
                    # Ignore cleanup errors, but log them
                    warning_msg = i18n.t('components.docling.docling_inline.logs.cleanup_warning',
                                         error=str(e))
                    logger.warning(warning_msg)
                    self.log(warning_msg)

        # Enhanced error checking with dependency-specific handling
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"]

            # Handle dependency errors specifically
            if result.get("error_type") == "dependency_error":
                dependency_name = result.get(
                    "dependency_name", "Unknown dependency")
                install_command = result.get(
                    "install_command", "Please check documentation")

                # Create a user-friendly error message
                user_message = i18n.t('components.docling.docling_inline.errors.missing_ocr_dependency',
                                      dependency=dependency_name,
                                      install_command=install_command)
                logger.error(user_message)
                raise ImportError(user_message)

            # Handle other specific errors
            if error_msg.startswith("Docling is not installed"):
                logger.error(error_msg)
                raise ImportError(error_msg)

            # Handle graceful shutdown
            if "Worker interrupted by SIGINT" in error_msg or "shutdown" in result:
                logger.info(
                    i18n.t('components.docling.docling_inline.logs.cancelled_by_user'))
                self.log(
                    i18n.t('components.docling.docling_inline.logs.cancelled_by_user'))
                result = []
            else:
                logger.error(i18n.t('components.docling.docling_inline.errors.runtime_error',
                                    error=error_msg))
                raise RuntimeError(error_msg)

        logger.info(i18n.t('components.docling.docling_inline.logs.processing_completed',
                           count=len(result)))

        processed_data = [Data(
            data={"doc": r["document"], "file_path": r["file_path"]}) if r else None for r in result]
        return self.rollup_data(file_list, processed_data)
