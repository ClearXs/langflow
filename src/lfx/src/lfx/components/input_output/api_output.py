import httpx
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, MessageTextInput, Output, TableInput
from lfx.schema import Data


class ETLAPIOutputComponent(Component):
    display_name = i18n.t("components.input_output.api_output.display_name")
    description = i18n.t("components.input_output.api_output.description")
    icon = "send"
    name = "ETLAPIOutput"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.api_output.data_input.display_name"),
            info=i18n.t("components.input_output.api_output.data_input.info"),
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="api_url",
            display_name=i18n.t("components.input_output.api_output.api_url.display_name"),
            info=i18n.t("components.input_output.api_output.api_url.info"),
            required=True,
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t("components.input_output.api_output.method.display_name"),
            info=i18n.t("components.input_output.api_output.method.info"),
            options=["POST", "PUT", "PATCH"],
            value="POST",
        ),
        TableInput(
            name="headers",
            display_name=i18n.t("components.input_output.api_output.headers.display_name"),
            info=i18n.t("components.input_output.api_output.headers.info"),
            table_schema=[
                {"name": "key", "display_name": "Header", "type": "str"},
                {"name": "value", "display_name": "Value", "type": "str"},
            ],
            value=[],
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.api_output.batch_size.display_name"),
            info=i18n.t("components.input_output.api_output.batch_size.info"),
            value=100,
            advanced=True,
        ),
        BoolInput(
            name="send_as_batch",
            display_name=i18n.t("components.input_output.api_output.send_as_batch.display_name"),
            info=i18n.t("components.input_output.api_output.send_as_batch.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.input_output.api_output.timeout.display_name"),
            info=i18n.t("components.input_output.api_output.timeout.info"),
            value=30,
            advanced=True,
        ),
    ]

    outputs = [Output(name="result", display_name="Send Result", method="send_to_api")]

    async def send_to_api(self) -> Data:
        try:
            self.status = i18n.t("components.input_output.api_output.status.sending")
            if not self.data_input:
                raise ValueError(i18n.t("components.input_output.api_output.errors.no_data"))
            headers = {h["key"]: h["value"] for h in self.headers} if self.headers else {}
            headers.setdefault("Content-Type", "application/json")
            data_list = [d.data if hasattr(d, "data") else d for d in self.data_input]
            success_count = 0
            error_count = 0
            async with httpx.AsyncClient() as client:
                if self.send_as_batch:
                    for i in range(0, len(data_list), self.batch_size):
                        batch = data_list[i : i + self.batch_size]
                        response = await client.request(
                            self.method, self.api_url, json=batch, headers=headers, timeout=self.timeout
                        )
                        if response.status_code in [200, 201, 204]:
                            success_count += len(batch)
                        else:
                            error_count += len(batch)
                else:
                    for item in data_list:
                        response = await client.request(
                            self.method, self.api_url, json=item, headers=headers, timeout=self.timeout
                        )
                        if response.status_code in [200, 201, 204]:
                            success_count += 1
                        else:
                            error_count += 1
            result_info = {
                "api_url": self.api_url,
                "success_count": success_count,
                "error_count": error_count,
                "method": self.method,
            }
            self.status = i18n.t(
                "components.input_output.api_output.status.success", success=success_count, errors=error_count
            )
            return Data(data=result_info)
        except Exception as e:
            error_msg = i18n.t("components.input_output.api_output.errors.send_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
