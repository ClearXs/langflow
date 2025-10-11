import os
import i18n
import tempfile

from lfx.custom.custom_component.component import Component
from lfx.io import Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackFileReadComponent(Component):
    display_name = "File Read"
    description = i18n.t('components.jigsawstack.file_read.description')
    documentation = "https://jigsawstack.com/docs/api-reference/store/file/get"
    icon = "JigsawStack"
    name = "JigsawStackFileRead"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.file_read.api_key.display_name'),
            info=i18n.t('components.jigsawstack.file_read.api_key.info'),
            required=True,
        ),
        StrInput(
            name="key",
            display_name=i18n.t(
                'components.jigsawstack.file_read.key.display_name'),
            info=i18n.t('components.jigsawstack.file_read.key.info'),
            required=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.file_read.outputs.file_path.display_name'),
            name="file_path",
            method="read_and_save_file"
        ),
    ]

    def read_and_save_file(self) -> Data:
        """Read file from JigsawStack and save to temp file, return file path.

        Returns:
            Data: File information including path, extension, size, etc.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If key is empty or invalid.
        """
        logger.info(i18n.t('components.jigsawstack.file_read.logs.starting_read',
                           key=self.key))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.file_read.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.key or self.key.strip() == "":
                error_msg = i18n.t(
                    'components.jigsawstack.file_read.errors.empty_key')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(
                i18n.t('components.jigsawstack.file_read.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Download file content
            logger.info(i18n.t('components.jigsawstack.file_read.logs.downloading_file',
                               key=self.key))
            response = client.store.get(self.key)

            # Determine file extension
            logger.debug(
                i18n.t('components.jigsawstack.file_read.logs.detecting_extension'))
            file_extension = self._detect_file_extension(response)

            logger.debug(i18n.t('components.jigsawstack.file_read.logs.extension_detected',
                                extension=file_extension))

            # Create temporary file
            logger.debug(
                i18n.t('components.jigsawstack.file_read.logs.creating_temp_file'))
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=file_extension, prefix=f"jigsawstack_{self.key}_"
            ) as temp_file:
                if isinstance(response, bytes):
                    temp_file.write(response)
                    content_size = len(response)
                    logger.debug(i18n.t('components.jigsawstack.file_read.logs.wrote_binary',
                                        size=content_size))
                else:
                    # Handle string content
                    encoded_content = response.encode("utf-8")
                    temp_file.write(encoded_content)
                    content_size = len(encoded_content)
                    logger.debug(i18n.t('components.jigsawstack.file_read.logs.wrote_text',
                                        size=content_size))

                temp_path = temp_file.name

            logger.info(i18n.t('components.jigsawstack.file_read.logs.file_saved',
                               path=temp_path,
                               size=content_size,
                               extension=file_extension))

            status_msg = i18n.t('components.jigsawstack.file_read.logs.read_complete',
                                key=self.key)
            self.status = status_msg

            return Data(
                data={
                    "file_path": temp_path,
                    "key": self.key,
                    "file_extension": file_extension,
                    "size": content_size,
                    "success": True,
                }
            )

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.file_read.errors.jigsawstack_error',
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

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.file_read.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)

    def _detect_file_extension(self, content) -> str:
        """Detect file extension based on content headers.

        Args:
            content: File content (bytes or string).

        Returns:
            str: Detected file extension with leading dot.
        """
        if isinstance(content, bytes):
            logger.debug(
                i18n.t('components.jigsawstack.file_read.logs.analyzing_binary'))

            # Check magic numbers for common file types
            if content.startswith(b"\xff\xd8\xff"):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='JPEG'))
                return ".jpg"
            if content.startswith(b"\x89PNG\r\n\x1a\n"):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='PNG'))
                return ".png"
            if content.startswith((b"GIF87a", b"GIF89a")):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='GIF'))
                return ".gif"
            if content.startswith(b"%PDF"):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='PDF'))
                return ".pdf"
            if content.startswith(b"PK\x03\x04"):  # ZIP/DOCX/XLSX
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='ZIP/Office'))
                return ".zip"
            if content.startswith(b"\x00\x00\x01\x00"):  # ICO
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='ICO'))
                return ".ico"
            if content.startswith(b"RIFF") and b"WEBP" in content[:12]:
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='WebP'))
                return ".webp"
            if content.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='MP3'))
                return ".mp3"
            if content.startswith((b"ftypmp4", b"\x00\x00\x00\x20ftypmp4")):
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='MP4'))
                return ".mp4"

            # Try to decode as text
            try:
                content.decode("utf-8")
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='Text'))
                return ".txt"
            except UnicodeDecodeError:
                logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                    type='Binary'))
                return ".bin"  # Binary file
        else:
            # String content
            logger.debug(i18n.t('components.jigsawstack.file_read.logs.detected_type',
                                type='Text'))
            return ".txt"
