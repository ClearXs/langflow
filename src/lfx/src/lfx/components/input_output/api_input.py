import json
from typing import Any

import httpx
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    DropdownInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
    Output,
    SecretStrInput,
    TableInput,
)
from lfx.schema import Data


class ETLAPIInputComponent(Component):
    display_name = i18n.t("components.input_output.api_input.display_name")
    description = i18n.t("components.input_output.api_input.description")
    icon = "globe"
    name = "ETLAPIInput"

    inputs = [
        MessageTextInput(
            name="api_url",
            display_name=i18n.t("components.input_output.api_input.api_url.display_name"),
            info=i18n.t("components.input_output.api_input.api_url.info"),
            required=True,
            placeholder="https://api.example.com/data",
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t("components.input_output.api_input.method.display_name"),
            info=i18n.t("components.input_output.api_input.method.info"),
            options=["GET", "POST"],
            value="GET",
        ),
        DropdownInput(
            name="auth_type",
            display_name=i18n.t("components.input_output.api_input.auth_type.display_name"),
            info=i18n.t("components.input_output.api_input.auth_type.info"),
            options=["None", "Basic", "Bearer", "API Key"],
            value="None",
            advanced=True,
        ),
        MessageTextInput(
            name="auth_username",
            display_name=i18n.t("components.input_output.api_input.auth_username.display_name"),
            info=i18n.t("components.input_output.api_input.auth_username.info"),
            advanced=True,
        ),
        SecretStrInput(
            name="auth_password",
            display_name=i18n.t("components.input_output.api_input.auth_password.display_name"),
            info=i18n.t("components.input_output.api_input.auth_password.info"),
            advanced=True,
        ),
        SecretStrInput(
            name="bearer_token",
            display_name=i18n.t("components.input_output.api_input.bearer_token.display_name"),
            info=i18n.t("components.input_output.api_input.bearer_token.info"),
            advanced=True,
        ),
        MessageTextInput(
            name="api_key_header",
            display_name=i18n.t("components.input_output.api_input.api_key_header.display_name"),
            info=i18n.t("components.input_output.api_input.api_key_header.info"),
            value="X-API-Key",
            advanced=True,
        ),
        SecretStrInput(
            name="api_key_value",
            display_name=i18n.t("components.input_output.api_input.api_key_value.display_name"),
            info=i18n.t("components.input_output.api_input.api_key_value.info"),
            advanced=True,
        ),
        TableInput(
            name="headers",
            display_name=i18n.t("components.input_output.api_input.headers.display_name"),
            info=i18n.t("components.input_output.api_input.headers.info"),
            table_schema=[
                {"name": "key", "display_name": "Header Name", "type": "str"},
                {"name": "value", "display_name": "Header Value", "type": "str"},
            ],
            value=[],
            advanced=True,
        ),
        MultilineInput(
            name="request_body",
            display_name=i18n.t("components.input_output.api_input.request_body.display_name"),
            info=i18n.t("components.input_output.api_input.request_body.info"),
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.input_output.api_input.timeout.display_name"),
            info=i18n.t("components.input_output.api_input.timeout.info"),
            value=30,
            advanced=True,
        ),
        IntInput(
            name="retry_count",
            display_name=i18n.t("components.input_output.api_input.retry_count.display_name"),
            info=i18n.t("components.input_output.api_input.retry_count.info"),
            value=3,
            advanced=True,
        ),
        MessageTextInput(
            name="data_path",
            display_name=i18n.t("components.input_output.api_input.data_path.display_name"),
            info=i18n.t("components.input_output.api_input.data_path.info"),
            placeholder="$.data or data.items",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.api_input.outputs.data.display_name"),
            method="fetch_data",
        ),
        Output(
            name="response_info",
            display_name=i18n.t("components.input_output.api_input.outputs.response_info.display_name"),
            method="get_response_info",
        ),
    ]

    async def fetch_data(self) -> list[Data]:
        """Fetch data from REST API with authentication and retry logic."""
        try:
            self.status = i18n.t("components.input_output.api_input.status.fetching")

            headers = self._build_headers()
            auth = self._build_auth()

            async with httpx.AsyncClient() as client:
                for attempt in range(self.retry_count):
                    try:
                        if self.method == "GET":
                            response = await client.get(self.api_url, headers=headers, auth=auth, timeout=self.timeout)
                        else:
                            body_data = json.loads(self.request_body) if self.request_body else {}
                            response = await client.post(
                                self.api_url, headers=headers, auth=auth, json=body_data, timeout=self.timeout
                            )

                        response.raise_for_status()
                        break

                    except httpx.HTTPError as e:
                        if attempt == self.retry_count - 1:
                            raise e
                        continue

                # Parse response
                response_data = response.json()

                # Extract data using path if provided
                if self.data_path:
                    response_data = self._extract_data_path(response_data)

                # Convert to Data objects
                result_data = []
                if isinstance(response_data, list):
                    for item in response_data:
                        result_data.append(Data(data=item))
                elif isinstance(response_data, dict):
                    result_data.append(Data(data=response_data))

                self.status = i18n.t("components.input_output.api_input.status.success", records=len(result_data))
                return result_data

        except Exception as e:
            error_msg = i18n.t("components.input_output.api_input.errors.fetch_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _build_headers(self) -> dict:
        """Build request headers with authentication."""
        headers = {}

        # Add custom headers
        if self.headers:
            for header in self.headers:
                headers[header["key"]] = header["value"]

        # Add authentication headers
        if self.auth_type == "Bearer" and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.auth_type == "API Key" and self.api_key_value:
            headers[self.api_key_header] = self.api_key_value

        return headers

    def _build_auth(self):
        """Build authentication for basic auth."""
        if self.auth_type == "Basic" and self.auth_username and self.auth_password:
            return (self.auth_username, self.auth_password)
        return None

    def _extract_data_path(self, data: Any) -> Any:
        """Extract data using JSONPath-like notation."""
        if not self.data_path:
            return data

        path_parts = self.data_path.strip("$.").split(".")
        current = data

        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part, current)
            else:
                break

        return current

    async def get_response_info(self) -> Data:
        """Get API response information."""
        info = {"api_url": self.api_url, "method": self.method, "auth_type": self.auth_type, "timeout": self.timeout}
        return Data(data=info)
