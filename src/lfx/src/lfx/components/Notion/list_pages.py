import i18n
import json
from typing import Any

import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import MultilineInput, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class NotionListPages(LCToolComponent):
    display_name: str = i18n.t('components.notion.list_pages.display_name')
    description: str = i18n.t('components.notion.list_pages.description')
    documentation: str = "https://docs.langflow.org/integrations/notion/list-pages"
    icon = "NotionDirectoryLoader"

    inputs = [
        SecretStrInput(
            name="notion_secret",
            display_name=i18n.t(
                'components.notion.list_pages.notion_secret.display_name'),
            info=i18n.t('components.notion.list_pages.notion_secret.info'),
            required=True,
        ),
        StrInput(
            name="database_id",
            display_name=i18n.t(
                'components.notion.list_pages.database_id.display_name'),
            info=i18n.t('components.notion.list_pages.database_id.info'),
        ),
        MultilineInput(
            name="query_json",
            display_name=i18n.t(
                'components.notion.list_pages.query_json.display_name'),
            info=i18n.t('components.notion.list_pages.query_json.info'),
        ),
    ]

    class NotionListPagesSchema(BaseModel):
        database_id: str = Field(...,
                                 description="The ID of the Notion database to query.")
        query_json: str | None = Field(
            default="",
            description="A JSON string containing the filters and sorts for querying the database. "
            "Leave empty for no filters or sorts.",
        )

    def run_model(self) -> list[Data]:
        result = self._query_notion_database(self.database_id, self.query_json)

        if isinstance(result, str):
            # An error occurred, return it as a single record
            return [Data(text=result)]

        records = []
        combined_text = f"Pages found: {len(result)}\n\n"

        for page in result:
            page_data = {
                "id": page["id"],
                "url": page["url"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
                "properties": page["properties"],
            }

            text = (
                f"id: {page['id']}\n"
                f"url: {page['url']}\n"
                f"created_time: {page['created_time']}\n"
                f"last_edited_time: {page['last_edited_time']}\n"
                f"properties: {json.dumps(page['properties'], indent=2)}\n\n"
            )

            combined_text += text
            records.append(Data(text=text, **page_data))

        self.status = records
        return records

    def build_tool(self) -> Tool:
        return StructuredTool.from_function(
            name="notion_list_pages",
            description=self.description,
            func=self._query_notion_database,
            args_schema=self.NotionListPagesSchema,
        )

    def _query_notion_database(self, database_id: str, query_json: str | None = None) -> list[dict[str, Any]] | str:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        query_payload = {}
        if query_json and query_json.strip():
            try:
                query_payload = json.loads(query_json)
            except json.JSONDecodeError as e:
                return f"Invalid JSON format for query: {e}"

        try:
            response = requests.post(
                url, headers=headers, json=query_payload, timeout=10)
            response.raise_for_status()
            results = response.json()
            return results["results"]
        except requests.exceptions.RequestException as e:
            return f"Error querying Notion database: {e}"
        except KeyError:
            return "Unexpected response format from Notion API"
        except Exception as e:  # noqa: BLE001
            logger.debug("Error querying Notion database", exc_info=True)
            return f"An unexpected error occurred: {e}"
