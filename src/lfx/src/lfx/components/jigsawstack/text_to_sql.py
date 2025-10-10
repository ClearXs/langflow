import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output, QueryInput, SecretStrInput, StrInput
from lfx.schema.data import Data


class JigsawStackTextToSQLComponent(Component):
    display_name = i18n.t('components.jigsawstack.text_to_sql.display_name')
    description = i18n.t('components.jigsawstack.text_to_sql.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/text-to-sql"
    icon = "JigsawStack"
    name = "JigsawStackTextToSQL"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.text_to_sql.api_key.display_name'),
            info=i18n.t('components.jigsawstack.text_to_sql.api_key.info'),
            required=True,
        ),
        QueryInput(
            name="prompt",
            display_name=i18n.t(
                'components.jigsawstack.text_to_sql.prompt.display_name'),
            info=i18n.t('components.jigsawstack.text_to_sql.prompt.info'),
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="sql_schema",
            display_name=i18n.t(
                'components.jigsawstack.text_to_sql.sql_schema.display_name'),
            info=i18n.t('components.jigsawstack.text_to_sql.sql_schema.info'),
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="file_store_key",
            display_name=i18n.t(
                'components.jigsawstack.text_to_sql.file_store_key.display_name'),
            info=i18n.t(
                'components.jigsawstack.text_to_sql.file_store_key.info'),
            required=False,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.text_to_sql.outputs.sql_query.display_name'),
            name="sql_query",
            method="generate_sql"
        ),
    ]

    def generate_sql(self) -> Data:
        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            jigsawstack_import_error = (
                "JigsawStack package not found. Please install it using: pip install jigsawstack>=0.2.7"
            )
            raise ImportError(jigsawstack_import_error) from e

        try:
            schema_error = "Either 'sql_schema' or 'file_store_key' must be provided"
            if not self.sql_schema and not self.file_store_key:
                raise ValueError(schema_error)

            # build request object
            params = {"prompt": self.prompt}

            if self.sql_schema:
                params["sql_schema"] = self.sql_schema
            if self.file_store_key:
                params["file_store_key"] = self.file_store_key

            client = JigsawStack(api_key=self.api_key)
            response = client.text_to_sql(params)

            api_error_msg = "JigsawStack API returned unsuccessful response"
            if not response.get("success", False):
                raise ValueError(api_error_msg)

            return Data(data=response)

        except ValueError:
            raise
        except JigsawStackError as e:
            error_data = {"error": str(e), "success": False}
            self.status = f"Error: {e!s}"
            return Data(data=error_data)
