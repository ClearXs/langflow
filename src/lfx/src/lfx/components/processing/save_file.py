import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
import i18n

import orjson
import pandas as pd
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

from lfx.custom import Component
from lfx.io import DropdownInput, HandleInput, StrInput
from lfx.schema import Data, DataFrame, Message
from lfx.services.deps import get_settings_service, get_storage_service
from lfx.template.field.base import Output


class SaveToFileComponent(Component):
    display_name = i18n.t('components.processing.save_file.display_name')
    description = i18n.t('components.processing.save_file.description')
    documentation: str = "https://docs.langflow.org/components-processing#save-file"
    icon = "save"
    name = "SaveToFile"

    # File format options for different types
    DATA_FORMAT_CHOICES = ["csv", "excel", "json", "markdown"]
    MESSAGE_FORMAT_CHOICES = ["txt", "json", "markdown"]

    inputs = [
        HandleInput(
            name="input",
            display_name=i18n.t(
                'components.processing.save_file.input.display_name'),
            info=i18n.t('components.processing.save_file.input.info'),
            dynamic=True,
            input_types=["Data", "DataFrame", "Message"],
            required=True,
        ),
        StrInput(
            name="file_name",
            display_name=i18n.t(
                'components.processing.save_file.file_name.display_name'),
            info=i18n.t('components.processing.save_file.file_name.info'),
            required=True,
        ),
        DropdownInput(
            name="file_format",
            display_name=i18n.t(
                'components.processing.save_file.file_format.display_name'),
            options=list(dict.fromkeys(
                DATA_FORMAT_CHOICES + MESSAGE_FORMAT_CHOICES)),
            info=i18n.t('components.processing.save_file.file_format.info'),
            value="",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.save_file.outputs.file_path.display_name'),
            name="message",
            method="save_to_file"
        )
    ]

    async def save_to_file(self) -> Message:
        """Save the input to a file and upload it, returning a confirmation message."""
        try:
            # Validate inputs
            if not self.file_name:
                error_msg = i18n.t(
                    'components.processing.save_file.errors.empty_file_name')
                self.status = error_msg
                raise ValueError(error_msg)

            if not self._get_input_type():
                error_msg = i18n.t(
                    'components.processing.save_file.errors.input_type_not_set')
                self.status = error_msg
                raise ValueError(error_msg)

            # Validate file format based on input type
            file_format = self.file_format or self._get_default_format()
            allowed_formats = (
                self.MESSAGE_FORMAT_CHOICES if self._get_input_type(
                ) == "Message" else self.DATA_FORMAT_CHOICES
            )
            if file_format not in allowed_formats:
                error_msg = i18n.t('components.processing.save_file.errors.invalid_file_format',
                                   format=file_format, input_type=self._get_input_type(),
                                   allowed=', '.join(allowed_formats))
                self.status = error_msg
                raise ValueError(error_msg)

            # Prepare file path
            self.status = i18n.t(
                'components.processing.save_file.status.preparing_file_path')
            file_path = Path(self.file_name).expanduser()
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path = self._adjust_file_path_with_format(
                file_path, file_format)

            # Save the input to file based on type
            self.status = i18n.t(
                'components.processing.save_file.status.saving_file', format=file_format)

            if self._get_input_type() == "DataFrame":
                confirmation = self._save_dataframe(
                    self.input, file_path, file_format)
            elif self._get_input_type() == "Data":
                confirmation = self._save_data(
                    self.input, file_path, file_format)
            elif self._get_input_type() == "Message":
                confirmation = await self._save_message(self.input, file_path, file_format)
            else:
                error_msg = i18n.t('components.processing.save_file.errors.unsupported_input_type',
                                   input_type=self._get_input_type())
                self.status = error_msg
                raise ValueError(error_msg)

            # Upload the saved file
            self.status = i18n.t(
                'components.processing.save_file.status.uploading_file')
            await self._upload_file(file_path)

            # Return the final file path and confirmation message
            final_path = Path.cwd() / file_path if not file_path.is_absolute() else file_path

            success_msg = i18n.t('components.processing.save_file.success.file_saved_and_uploaded',
                                 confirmation=confirmation, path=str(final_path))
            self.status = success_msg

            return Message(text=success_msg)

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.save_file.errors.save_operation_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise

    def _get_input_type(self) -> str:
        """Determine the input type based on the provided input."""
        try:
            # Use exact type checking (type() is) instead of isinstance() to avoid inheritance issues.
            # Since Message inherits from Data, isinstance(message, Data) would return True for Message objects,
            # causing Message inputs to be incorrectly identified as Data type.
            if type(self.input) is DataFrame:
                return "DataFrame"
            if type(self.input) is Message:
                return "Message"
            if type(self.input) is Data:
                return "Data"
            error_msg = i18n.t('components.processing.save_file.errors.unsupported_input_type_detection',
                               actual_type=type(self.input).__name__)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.save_file.errors.input_type_detection_failed', error=str(e))
            self.log(error_msg, "error")
            raise

    def _get_default_format(self) -> str:
        """Return the default file format based on input type."""
        input_type = self._get_input_type()
        if input_type == "DataFrame":
            return "csv"
        elif input_type == "Data":
            return "json"
        elif input_type == "Message":
            return "json"
        else:
            return "json"  # Fallback

    def _adjust_file_path_with_format(self, path: Path, fmt: str) -> Path:
        """Adjust the file path to include the correct extension."""
        try:
            file_extension = path.suffix.lower().lstrip(".")
            if fmt == "excel":
                return Path(f"{path}.xlsx").expanduser() if file_extension not in ["xlsx", "xls"] else path
            return Path(f"{path}.{fmt}").expanduser() if file_extension != fmt else path
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.save_file.errors.file_path_adjustment_failed', error=str(e))
            self.log(error_msg, "error")
            raise

    async def _upload_file(self, file_path: Path) -> None:
        """Upload the saved file using the upload_user_file service."""
        try:
            from langflow.api.v2.files import upload_user_file
            from langflow.services.database.models.user.crud import get_user_by_id
        except ImportError as e:
            error_msg = i18n.t(
                'components.processing.save_file.errors.langflow_import_failed')
            raise ImportError(error_msg) from e

        if not file_path.exists():
            error_msg = i18n.t(
                'components.processing.save_file.errors.file_not_found', path=str(file_path))
            raise FileNotFoundError(error_msg)

        try:
            with file_path.open("rb") as f:
                try:
                    from langflow.services.database.models.user.crud import get_user_by_id
                    from langflow.services.deps import session_scope
                except ImportError as e:
                    error_msg = i18n.t(
                        'components.processing.save_file.errors.langflow_mcp_import_failed')
                    raise ImportError(error_msg) from e

                async with session_scope() as db:
                    if not self.user_id:
                        error_msg = i18n.t(
                            'components.processing.save_file.errors.user_id_required')
                        raise ValueError(error_msg)

                    current_user = await get_user_by_id(db, self.user_id)

                    await upload_user_file(
                        file=UploadFile(filename=file_path.name,
                                        file=f, size=file_path.stat().st_size),
                        session=db,
                        current_user=current_user,
                        storage_service=get_storage_service(),
                        settings_service=get_settings_service(),
                    )

        except Exception as e:
            error_msg = i18n.t('components.processing.save_file.errors.file_upload_failed',
                               path=str(file_path), error=str(e))
            self.log(error_msg, "error")
            raise

    def _save_dataframe(self, dataframe: DataFrame, path: Path, fmt: str) -> str:
        """Save a DataFrame to the specified file format."""
        try:
            if fmt == "csv":
                dataframe.to_csv(path, index=False)
            elif fmt == "excel":
                dataframe.to_excel(path, index=False, engine="openpyxl")
            elif fmt == "json":
                dataframe.to_json(path, orient="records", indent=2)
            elif fmt == "markdown":
                path.write_text(dataframe.to_markdown(
                    index=False), encoding="utf-8")
            else:
                error_msg = i18n.t(
                    'components.processing.save_file.errors.unsupported_dataframe_format', format=fmt)
                raise ValueError(error_msg)

            return i18n.t('components.processing.save_file.success.dataframe_saved', path=str(path))

        except Exception as e:
            error_msg = i18n.t('components.processing.save_file.errors.dataframe_save_failed',
                               format=fmt, error=str(e))
            self.log(error_msg, "error")
            raise

    def _save_data(self, data: Data, path: Path, fmt: str) -> str:
        """Save a Data object to the specified file format."""
        try:
            if fmt == "csv":
                pd.DataFrame(data.data).to_csv(path, index=False)
            elif fmt == "excel":
                pd.DataFrame(data.data).to_excel(
                    path, index=False, engine="openpyxl")
            elif fmt == "json":
                path.write_text(
                    orjson.dumps(jsonable_encoder(data.data),
                                 option=orjson.OPT_INDENT_2).decode("utf-8"),
                    encoding="utf-8"
                )
            elif fmt == "markdown":
                path.write_text(pd.DataFrame(data.data).to_markdown(
                    index=False), encoding="utf-8")
            else:
                error_msg = i18n.t(
                    'components.processing.save_file.errors.unsupported_data_format', format=fmt)
                raise ValueError(error_msg)

            return i18n.t('components.processing.save_file.success.data_saved', path=str(path))

        except Exception as e:
            error_msg = i18n.t('components.processing.save_file.errors.data_save_failed',
                               format=fmt, error=str(e))
            self.log(error_msg, "error")
            raise

    async def _save_message(self, message: Message, path: Path, fmt: str) -> str:
        """Save a Message to the specified file format, handling async iterators."""
        try:
            content = ""
            if message.text is None:
                content = ""
            elif isinstance(message.text, AsyncIterator):
                async for item in message.text:
                    content += str(item) + " "
                content = content.strip()
            elif isinstance(message.text, Iterator):
                content = " ".join(str(item) for item in message.text)
            else:
                content = str(message.text)

            if fmt == "txt":
                path.write_text(content, encoding="utf-8")
            elif fmt == "json":
                path.write_text(json.dumps(
                    {"message": content}, indent=2), encoding="utf-8")
            elif fmt == "markdown":
                path.write_text(f"**Message:**\n\n{content}", encoding="utf-8")
            else:
                error_msg = i18n.t(
                    'components.processing.save_file.errors.unsupported_message_format', format=fmt)
                raise ValueError(error_msg)

            return i18n.t('components.processing.save_file.success.message_saved', path=str(path))

        except Exception as e:
            error_msg = i18n.t('components.processing.save_file.errors.message_save_failed',
                               format=fmt, error=str(e))
            self.log(error_msg, "error")
            raise
