import os
import i18n
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, FileInput, Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackFileUploadComponent(Component):
    display_name = "File Upload"
    description = i18n.t('components.jigsawstack.file_upload.description')
    documentation = "https://jigsawstack.com/docs/api-reference/store/file/add"
    icon = "JigsawStack"
    name = "JigsawStackFileUpload"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.file_upload.api_key.display_name'),
            info=i18n.t('components.jigsawstack.file_upload.api_key.info'),
            required=True,
        ),
        FileInput(
            name="file",
            display_name=i18n.t(
                'components.jigsawstack.file_upload.file.display_name'),
            info=i18n.t('components.jigsawstack.file_upload.file.info'),
            required=True,
            file_types=["pdf", "png", "jpg", "jpeg",
                        "mp4", "mp3", "txt", "docx", "xlsx"],
        ),
        StrInput(
            name="key",
            display_name=i18n.t(
                'components.jigsawstack.file_upload.key.display_name'),
            info=i18n.t('components.jigsawstack.file_upload.key.info'),
            required=False,
            tool_mode=True,
        ),
        BoolInput(
            name="overwrite",
            display_name=i18n.t(
                'components.jigsawstack.file_upload.overwrite.display_name'),
            info=i18n.t('components.jigsawstack.file_upload.overwrite.info'),
            required=False,
            value=True,
        ),
        BoolInput(
            name="temp_public_url",
            display_name=i18n.t(
                'components.jigsawstack.file_upload.temp_public_url.display_name'),
            info=i18n.t(
                'components.jigsawstack.file_upload.temp_public_url.info'),
            required=False,
            value=False,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.file_upload.outputs.file_upload_result.display_name'),
            name="file_upload_result",
            method="upload_file"
        ),
    ]

    def upload_file(self) -> Data:
        """Upload file to JigsawStack storage.

        Returns:
            Data: Upload result including key and URL.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If file path is invalid.
        """
        logger.info(i18n.t('components.jigsawstack.file_upload.logs.starting_upload',
                           file=self.file))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.file_upload.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.debug(
                i18n.t('components.jigsawstack.file_upload.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            file_path = Path(self.file)

            if not file_path.exists():
                error_msg = i18n.t('components.jigsawstack.file_upload.errors.file_not_found',
                                   path=str(file_path))
                logger.error(error_msg)
                raise ValueError(error_msg)

            if not file_path.is_file():
                error_msg = i18n.t('components.jigsawstack.file_upload.errors.not_a_file',
                                   path=str(file_path))
                logger.error(error_msg)
                raise ValueError(error_msg)

            file_size = file_path.stat().st_size
            logger.debug(i18n.t('components.jigsawstack.file_upload.logs.reading_file',
                                path=str(file_path),
                                size=file_size))

            with Path.open(file_path, "rb") as f:
                file_content = f.read()

            logger.debug(i18n.t('components.jigsawstack.file_upload.logs.file_read',
                                size=len(file_content)))

            # Build upload parameters
            params = {}

            if self.key:
                params["key"] = self.key
                logger.debug(i18n.t('components.jigsawstack.file_upload.logs.using_key',
                                    key=self.key))
            else:
                logger.debug(
                    i18n.t('components.jigsawstack.file_upload.logs.auto_generate_key'))

            if self.overwrite is not None:
                params["overwrite"] = self.overwrite
                logger.debug(i18n.t('components.jigsawstack.file_upload.logs.overwrite_setting',
                                    overwrite=self.overwrite))

            if self.temp_public_url is not None:
                params["temp_public_url"] = self.temp_public_url
                logger.debug(i18n.t('components.jigsawstack.file_upload.logs.temp_url_setting',
                                    temp_url=self.temp_public_url))

            logger.info(i18n.t('components.jigsawstack.file_upload.logs.uploading_file',
                               name=file_path.name,
                               size=file_size))

            response = client.store.upload(file_content, params)

            logger.info(i18n.t('components.jigsawstack.file_upload.logs.upload_complete',
                               key=response.get('key', 'N/A')))

            status_msg = i18n.t('components.jigsawstack.file_upload.logs.upload_success',
                                name=file_path.name)
            self.status = status_msg

            return Data(data=response)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.file_upload.errors.jigsawstack_error',
                               error=str(e))
            logger.error(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            error_data = {"error": error_msg, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except OSError as e:
            error_msg = i18n.t('components.jigsawstack.file_upload.errors.file_read_error',
                               error=str(e))
            logger.error(error_msg)
            error_data = {"error": error_msg, "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.file_upload.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
