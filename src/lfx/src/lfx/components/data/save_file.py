import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import i18n
import orjson
import pandas as pd
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

from lfx.custom import Component
from lfx.inputs import SortableListInput
from lfx.io import DropdownInput, HandleInput, SecretStrInput, StrInput
from lfx.schema import Data, DataFrame, Message
from lfx.services.deps import get_settings_service, get_storage_service, session_scope
from lfx.template.field.base import Output


class SaveToFileComponent(Component):
    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    display_name = i18n.t("components.data.save_file.display_name")
    description = i18n.t("components.data.save_file.description")
    documentation: str = "https://docs.langflow.org/components-processing#save-file"
    icon = "file-text"
    name = "SaveToFile"

    # File format options for different storage types
    LOCAL_DATA_FORMAT_CHOICES = ["csv", "excel", "json", "markdown"]
    LOCAL_MESSAGE_FORMAT_CHOICES = ["txt", "json", "markdown"]
    AWS_FORMAT_CHOICES = [
        "txt",
        "json",
        "csv",
        "xml",
        "html",
        "md",
        "yaml",
        "log",
        "tsv",
        "jsonl",
        "parquet",
        "xlsx",
        "zip",
    ]
    GDRIVE_FORMAT_CHOICES = ["txt", "json", "csv", "xlsx", "slides", "docs", "jpg", "mp3"]

    inputs = [
        # Storage location selection
        SortableListInput(
            name="storage_location",
            display_name=i18n.t("components.data.save_file.storage_location.display_name"),
            placeholder=i18n.t("components.data.save_file.storage_location.placeholder"),
            info=i18n.t("components.data.save_file.storage_location.info"),
            options=[
                {"name": i18n.t("components.data.save_file.storage_location.options.local"), "icon": "hard-drive"},
                {"name": i18n.t("components.data.save_file.storage_location.options.aws"), "icon": "Amazon"},
                {"name": i18n.t("components.data.save_file.storage_location.options.google_drive"), "icon": "google"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        # Common inputs
        HandleInput(
            name="input",
            display_name=i18n.t("components.data.save_file.input.display_name"),
            info=i18n.t("components.data.save_file.input.info"),
            dynamic=True,
            input_types=["Data", "DataFrame", "Message"],
            required=True,
        ),
        StrInput(
            name="file_name",
            display_name=i18n.t("components.data.save_file.file_name.display_name"),
            info=i18n.t("components.data.save_file.file_name.info"),
            required=True,
            show=False,
            tool_mode=True,
        ),
        # Format inputs (dynamic based on storage location)
        DropdownInput(
            name="local_format",
            display_name=i18n.t("components.data.save_file.local_format.display_name"),
            options=list(dict.fromkeys(LOCAL_DATA_FORMAT_CHOICES + LOCAL_MESSAGE_FORMAT_CHOICES)),
            info=i18n.t("components.data.save_file.local_format.info"),
            value="json",
            show=False,
        ),
        DropdownInput(
            name="aws_format",
            display_name=i18n.t("components.data.save_file.aws_format.display_name"),
            options=AWS_FORMAT_CHOICES,
            info=i18n.t("components.data.save_file.aws_format.info"),
            value="txt",
            show=False,
        ),
        DropdownInput(
            name="gdrive_format",
            display_name=i18n.t("components.data.save_file.gdrive_format.display_name"),
            options=GDRIVE_FORMAT_CHOICES,
            info=i18n.t("components.data.save_file.gdrive_format.info"),
            value="txt",
            show=False,
        ),
        # AWS S3 specific inputs
        SecretStrInput(
            name="aws_access_key_id",
            display_name=i18n.t("components.data.save_file.aws_access_key_id.display_name"),
            info=i18n.t("components.data.save_file.aws_access_key_id.info"),
            show=False,
            advanced=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name=i18n.t("components.data.save_file.aws_secret_access_key.display_name"),
            info=i18n.t("components.data.save_file.aws_secret_access_key.info"),
            show=False,
            advanced=True,
        ),
        StrInput(
            name="bucket_name",
            display_name=i18n.t("components.data.save_file.bucket_name.display_name"),
            info=i18n.t("components.data.save_file.bucket_name.info"),
            show=False,
            advanced=True,
        ),
        StrInput(
            name="aws_region",
            display_name=i18n.t("components.data.save_file.aws_region.display_name"),
            info=i18n.t("components.data.save_file.aws_region.info"),
            show=False,
            advanced=True,
        ),
        StrInput(
            name="s3_prefix",
            display_name=i18n.t("components.data.save_file.s3_prefix.display_name"),
            info=i18n.t("components.data.save_file.s3_prefix.info"),
            show=False,
            advanced=True,
        ),
        # Google Drive specific inputs
        SecretStrInput(
            name="service_account_key",
            display_name=i18n.t("components.data.save_file.service_account_key.display_name"),
            info=i18n.t("components.data.save_file.service_account_key.info"),
            show=False,
            advanced=True,
        ),
        StrInput(
            name="folder_id",
            display_name=i18n.t("components.data.save_file.folder_id.display_name"),
            info=i18n.t("components.data.save_file.folder_id.info"),
            show=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.data.save_file.outputs.message.display_name"),
            name="message",
            method="save_to_file",
        )
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update build configuration to show/hide fields based on storage location selection."""
        if field_name != "storage_location":
            return build_config

        # Extract selected storage location
        selected = [location["name"] for location in field_value] if isinstance(field_value, list) else []

        # Hide all dynamic fields first
        dynamic_fields = [
            "file_name",
            "local_format",
            "aws_format",
            "gdrive_format",
            "aws_access_key_id",
            "aws_secret_access_key",
            "bucket_name",
            "aws_region",
            "s3_prefix",
            "service_account_key",
            "folder_id",
        ]

        for f_name in dynamic_fields:
            if f_name in build_config:
                build_config[f_name]["show"] = False

        # Show fields based on selected storage location
        if len(selected) == 1:
            location = selected[0]

            # Show file_name when any storage location is selected
            if "file_name" in build_config:
                build_config["file_name"]["show"] = True

            # Get localized location names
            local_name = i18n.t("components.data.save_file.storage_location.options.local")
            aws_name = i18n.t("components.data.save_file.storage_location.options.aws")
            gdrive_name = i18n.t("components.data.save_file.storage_location.options.google_drive")

            if location == local_name:
                if "local_format" in build_config:
                    build_config["local_format"]["show"] = True

            elif location == aws_name:
                aws_fields = [
                    "aws_format",
                    "aws_access_key_id",
                    "aws_secret_access_key",
                    "bucket_name",
                    "aws_region",
                    "s3_prefix",
                ]
                for f_name in aws_fields:
                    if f_name in build_config:
                        build_config[f_name]["show"] = True

            elif location == gdrive_name:
                gdrive_fields = ["gdrive_format", "service_account_key", "folder_id"]
                for f_name in gdrive_fields:
                    if f_name in build_config:
                        build_config[f_name]["show"] = True

        return build_config

    async def save_to_file(self) -> Message:
        """Save the input to a file and upload it, returning a confirmation message."""
        # Validate inputs
        if not self.file_name:
            msg = i18n.t("components.data.save_file.errors.file_name_required")
            raise ValueError(msg)
        if not self._get_input_type():
            msg = i18n.t("components.data.save_file.errors.input_type_not_set")
            raise ValueError(msg)

        # Get selected storage location
        storage_location = self._get_selected_storage_location()
        if not storage_location:
            msg = i18n.t("components.data.save_file.errors.storage_location_required")
            raise ValueError(msg)

        # Get localized location names for comparison
        local_name = i18n.t("components.data.save_file.storage_location.options.local")
        aws_name = i18n.t("components.data.save_file.storage_location.options.aws")
        gdrive_name = i18n.t("components.data.save_file.storage_location.options.google_drive")

        # Route to appropriate save method based on storage location
        if storage_location == local_name:
            return await self._save_to_local()
        if storage_location == aws_name:
            return await self._save_to_aws()
        if storage_location == gdrive_name:
            return await self._save_to_google_drive()
        msg = i18n.t("components.data.save_file.errors.unsupported_storage_location", location=storage_location)
        raise ValueError(msg)

    def _get_input_type(self) -> str:
        """Determine the input type based on the provided input."""
        if type(self.input) is DataFrame:
            return "DataFrame"
        if type(self.input) is Message:
            return "Message"
        if type(self.input) is Data:
            return "Data"
        msg = i18n.t("components.data.save_file.errors.unsupported_input_type", type=str(type(self.input)))
        raise ValueError(msg)

    def _get_default_format(self) -> str:
        """Return the default file format based on input type."""
        if self._get_input_type() == "DataFrame":
            return "csv"
        if self._get_input_type() == "Data":
            return "json"
        if self._get_input_type() == "Message":
            return "json"
        return "json"

    def _adjust_file_path_with_format(self, path: Path, fmt: str) -> Path:
        """Adjust the file path to include the correct extension."""
        file_extension = path.suffix.lower().lstrip(".")
        if fmt == "excel":
            return Path(f"{path}.xlsx").expanduser() if file_extension not in ["xlsx", "xls"] else path
        return Path(f"{path}.{fmt}").expanduser() if file_extension != fmt else path

    async def _upload_file(self, file_path: Path) -> None:
        """Upload the saved file using the upload_user_file service."""
        from langflow.api.v2.files import upload_user_file
        from langflow.services.database.models.user.crud import get_user_by_id

        if not file_path.exists():
            msg = i18n.t("components.data.save_file.errors.file_not_found", path=str(file_path))
            raise FileNotFoundError(msg)

        with file_path.open("rb") as f:
            async with session_scope() as db:
                if not self.user_id:
                    msg = i18n.t("components.data.save_file.errors.user_id_required")
                    raise ValueError(msg)
                current_user = await get_user_by_id(db, self.user_id)

                await upload_user_file(
                    file=UploadFile(filename=file_path.name, file=f, size=file_path.stat().st_size),
                    session=db,
                    current_user=current_user,
                    storage_service=get_storage_service(),
                    settings_service=get_settings_service(),
                )

    def _save_dataframe(self, dataframe: DataFrame, path: Path, fmt: str) -> str:
        """Save a DataFrame to the specified file format."""
        if fmt == "csv":
            dataframe.to_csv(path, index=False)
        elif fmt == "excel":
            dataframe.to_excel(path, index=False, engine="openpyxl")
        elif fmt == "json":
            dataframe.to_json(path, orient="records", indent=2)
        elif fmt == "markdown":
            path.write_text(dataframe.to_markdown(index=False), encoding="utf-8")
        else:
            msg = i18n.t("components.data.save_file.errors.unsupported_dataframe_format", format=fmt)
            raise ValueError(msg)
        return i18n.t("components.data.save_file.success.dataframe_saved", path=str(path))

    def _save_data(self, data: Data, path: Path, fmt: str) -> str:
        """Save a Data object to the specified file format."""
        if fmt == "csv":
            pd.DataFrame(data.data).to_csv(path, index=False)
        elif fmt == "excel":
            pd.DataFrame(data.data).to_excel(path, index=False, engine="openpyxl")
        elif fmt == "json":
            path.write_text(
                orjson.dumps(jsonable_encoder(data.data), option=orjson.OPT_INDENT_2).decode("utf-8"), encoding="utf-8"
            )
        elif fmt == "markdown":
            path.write_text(pd.DataFrame(data.data).to_markdown(index=False), encoding="utf-8")
        else:
            msg = i18n.t("components.data.save_file.errors.unsupported_data_format", format=fmt)
            raise ValueError(msg)
        return i18n.t("components.data.save_file.success.data_saved", path=str(path))

    async def _save_message(self, message: Message, path: Path, fmt: str) -> str:
        """Save a Message to the specified file format, handling async iterators."""
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
            path.write_text(json.dumps({"message": content}, indent=2), encoding="utf-8")
        elif fmt == "markdown":
            path.write_text(f"**Message:**\n\n{content}", encoding="utf-8")
        else:
            msg = i18n.t("components.data.save_file.errors.unsupported_message_format", format=fmt)
            raise ValueError(msg)
        return i18n.t("components.data.save_file.success.message_saved", path=str(path))

    def _get_selected_storage_location(self) -> str:
        """Get the selected storage location from the SortableListInput."""
        if hasattr(self, "storage_location") and self.storage_location:
            if isinstance(self.storage_location, list) and len(self.storage_location) > 0:
                return self.storage_location[0].get("name", "")
            if isinstance(self.storage_location, dict):
                return self.storage_location.get("name", "")
        return ""

    def _get_file_format_for_location(self, location: str) -> str:
        """Get the appropriate file format based on storage location."""
        local_name = i18n.t("components.data.save_file.storage_location.options.local")
        aws_name = i18n.t("components.data.save_file.storage_location.options.aws")
        gdrive_name = i18n.t("components.data.save_file.storage_location.options.google_drive")

        if location == local_name:
            return getattr(self, "local_format", None) or self._get_default_format()
        if location == aws_name:
            return getattr(self, "aws_format", "txt")
        if location == gdrive_name:
            return getattr(self, "gdrive_format", "txt")
        return self._get_default_format()

    async def _save_to_local(self) -> Message:
        """Save file to local storage (original functionality)."""
        local_name = i18n.t("components.data.save_file.storage_location.options.local")
        file_format = self._get_file_format_for_location(local_name)

        # Validate file format based on input type
        allowed_formats = (
            self.LOCAL_MESSAGE_FORMAT_CHOICES if self._get_input_type() == "Message" else self.LOCAL_DATA_FORMAT_CHOICES
        )
        if file_format not in allowed_formats:
            msg = i18n.t(
                "components.data.save_file.errors.invalid_file_format",
                format=file_format,
                type=self._get_input_type(),
                allowed=str(allowed_formats),
            )
            raise ValueError(msg)

        # Prepare file path
        file_path = Path(self.file_name).expanduser()
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = self._adjust_file_path_with_format(file_path, file_format)

        # Save the input to file based on type
        if self._get_input_type() == "DataFrame":
            confirmation = self._save_dataframe(self.input, file_path, file_format)
        elif self._get_input_type() == "Data":
            confirmation = self._save_data(self.input, file_path, file_format)
        elif self._get_input_type() == "Message":
            confirmation = await self._save_message(self.input, file_path, file_format)
        else:
            msg = i18n.t("components.data.save_file.errors.unsupported_input_type", type=self._get_input_type())
            raise ValueError(msg)

        # Upload the saved file
        await self._upload_file(file_path)

        # Return the final file path and confirmation message
        final_path = Path.cwd() / file_path if not file_path.is_absolute() else file_path
        return Message(text=f"{confirmation} at {final_path}")

    async def _save_to_aws(self) -> Message:
        """Save file to AWS S3 using S3 functionality."""
        # Validate AWS credentials
        if not getattr(self, "aws_access_key_id", None):
            msg = i18n.t("components.data.save_file.errors.aws_access_key_required")
            raise ValueError(msg)
        if not getattr(self, "aws_secret_access_key", None):
            msg = i18n.t("components.data.save_file.errors.aws_secret_key_required")
            raise ValueError(msg)
        if not getattr(self, "bucket_name", None):
            msg = i18n.t("components.data.save_file.errors.bucket_name_required")
            raise ValueError(msg)

        # Use S3 upload functionality
        try:
            import boto3
        except ImportError as e:
            msg = i18n.t("components.data.save_file.errors.boto3_not_installed")
            raise ImportError(msg) from e

        # Create S3 client
        client_config = {
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
        }

        if hasattr(self, "aws_region") and self.aws_region:
            client_config["region_name"] = self.aws_region

        s3_client = boto3.client("s3", **client_config)

        # Extract content
        content = self._extract_content_for_upload()
        aws_name = i18n.t("components.data.save_file.storage_location.options.aws")
        file_format = self._get_file_format_for_location(aws_name)

        # Generate file path
        file_path = f"{self.file_name}.{file_format}"
        if hasattr(self, "s3_prefix") and self.s3_prefix:
            file_path = f"{self.s3_prefix.rstrip('/')}/{file_path}"

        # Create temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{file_format}", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Upload to S3
            s3_client.upload_file(temp_file_path, self.bucket_name, file_path)
            s3_url = f"s3://{self.bucket_name}/{file_path}"
            return Message(text=i18n.t("components.data.save_file.success.uploaded_to_s3", url=s3_url))
        finally:
            # Clean up temp file
            if Path(temp_file_path).exists():
                Path(temp_file_path).unlink()

    async def _save_to_google_drive(self) -> Message:
        """Save file to Google Drive using Google Drive functionality."""
        # Validate Google Drive credentials
        if not getattr(self, "service_account_key", None):
            msg = i18n.t("components.data.save_file.errors.service_account_key_required")
            raise ValueError(msg)
        if not getattr(self, "folder_id", None):
            msg = i18n.t("components.data.save_file.errors.folder_id_required")
            raise ValueError(msg)

        # Use Google Drive upload functionality
        try:
            import json
            import tempfile

            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError as e:
            msg = i18n.t("components.data.save_file.errors.google_api_not_installed")
            raise ImportError(msg) from e

        # Parse credentials
        try:
            credentials_dict = json.loads(self.service_account_key)
        except json.JSONDecodeError as e:
            msg = i18n.t("components.data.save_file.errors.invalid_service_account_json", error=str(e))
            raise ValueError(msg) from e

        # Create Google Drive service
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        drive_service = build("drive", "v3", credentials=credentials)

        # Extract content and format
        content = self._extract_content_for_upload()
        gdrive_name = i18n.t("components.data.save_file.storage_location.options.google_drive")
        file_format = self._get_file_format_for_location(gdrive_name)

        # Handle special Google Drive formats
        if file_format in ["slides", "docs"]:
            return await self._save_to_google_apps(drive_service, content, file_format)

        # Create temporary file
        file_path = f"{self.file_name}.{file_format}"
        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{file_format}", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Upload to Google Drive
            file_metadata = {"name": file_path, "parents": [self.folder_id]}
            media = MediaFileUpload(temp_file_path, resumable=True)

            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

            file_id = uploaded_file.get("id")
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            return Message(text=i18n.t("components.data.save_file.success.uploaded_to_drive", url=file_url))
        finally:
            # Clean up temp file
            if Path(temp_file_path).exists():
                Path(temp_file_path).unlink()

    async def _save_to_google_apps(self, drive_service, content: str, app_type: str) -> Message:
        """Save content to Google Apps (Slides or Docs)."""
        import time

        if app_type == "slides":
            from googleapiclient.discovery import build

            slides_service = build("slides", "v1", credentials=drive_service._http.credentials)

            file_metadata = {
                "name": self.file_name,
                "mimeType": "application/vnd.google-apps.presentation",
                "parents": [self.folder_id],
            }

            created_file = drive_service.files().create(body=file_metadata, fields="id").execute()
            presentation_id = created_file["id"]

            time.sleep(2)  # Wait for file to be available  # noqa: ASYNC251

            presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
            slide_id = presentation["slides"][0]["objectId"]

            # Add content to slide
            requests = [
                {
                    "createShape": {
                        "objectId": "TextBox_01",
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "height": {"magnitude": 3000000, "unit": "EMU"},
                                "width": {"magnitude": 6000000, "unit": "EMU"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": 1000000,
                                "translateY": 1000000,
                                "unit": "EMU",
                            },
                        },
                    }
                },
                {"insertText": {"objectId": "TextBox_01", "insertionIndex": 0, "text": content}},
            ]

            slides_service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
            file_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

        elif app_type == "docs":
            from googleapiclient.discovery import build

            docs_service = build("docs", "v1", credentials=drive_service._http.credentials)

            file_metadata = {
                "name": self.file_name,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [self.folder_id],
            }

            created_file = drive_service.files().create(body=file_metadata, fields="id").execute()
            document_id = created_file["id"]

            time.sleep(2)  # Wait for file to be available  # noqa: ASYNC251

            # Add content to document
            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
            docs_service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            file_url = f"https://docs.google.com/document/d/{document_id}/edit"

        return Message(
            text=i18n.t(
                "components.data.save_file.success.created_in_google_apps", app_type=app_type.title(), url=file_url
            )
        )

    def _extract_content_for_upload(self) -> str:
        """Extract content from input for upload to cloud services."""
        if self._get_input_type() == "DataFrame":
            return self.input.to_csv(index=False)
        if self._get_input_type() == "Data":
            if hasattr(self.input, "data") and self.input.data:
                if isinstance(self.input.data, dict):
                    import json

                    return json.dumps(self.input.data, indent=2, ensure_ascii=False)
                return str(self.input.data)
            return str(self.input)
        if self._get_input_type() == "Message":
            return str(self.input.text) if self.input.text else str(self.input)
        return str(self.input)
