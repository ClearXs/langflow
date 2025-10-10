import os
import i18n
from typing import Any

import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import DropdownInput, SecretStrInput, StrInput
from lfx.schema.data import Data


class NotionSearch(LCToolComponent):
    display_name: str = i18n.t('components.notion.search.display_name')
    description: str = i18n.t('components.notion.search.description')
    documentation: str = "https://docs.langflow.org/integrations/notion/search"
    icon = "NotionDirectoryLoader"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="notion_secret",
            display_name=i18n.t(
                'components.notion.search.notion_secret.display_name'),
            info=i18n.t('components.notion.search.notion_secret.info'),
            required=True,
        ),
        StrInput(
            name="query",
            display_name=i18n.t('components.notion.search.query.display_name'),
            info=i18n.t('components.notion.search.query.info'),
        ),
        DropdownInput(
            name="filter_value",
            display_name=i18n.t(
                'components.notion.search.filter_value.display_name'),
            info=i18n.t('components.notion.search.filter_value.info'),
            options=["page", "database"],
            value="page",
        ),
        DropdownInput(
            name="sort_direction",
            display_name=i18n.t(
                'components.notion.search.sort_direction.display_name'),
            info=i18n.t('components.notion.search.sort_direction.info'),
            options=["ascending", "descending"],
            value="descending",
        ),
    ]

    class NotionSearchSchema(BaseModel):
        query: str = Field(..., description="The search query text.")
        filter_value: str = Field(
            default="page", description="Filter type: 'page' or 'database'.")
        sort_direction: str = Field(
            default="descending", description="Sort direction: 'ascending' or 'descending'.")

    def run_model(self) -> list[Data]:
        results = self._search_notion(
            self.query, self.filter_value, self.sort_direction)
        records = []
        combined_text = f"Results found: {len(results)}\n\n"

        for result in results:
            result_data = {
                "id": result["id"],
                "type": result["object"],
                "last_edited_time": result["last_edited_time"],
            }

            if result["object"] == "page":
                result_data["title_or_url"] = result["url"]
                text = f"id: {result['id']}\ntitle_or_url: {result['url']}\n"
            elif result["object"] == "database":
                if "title" in result and isinstance(result["title"], list) and len(result["title"]) > 0:
                    result_data["title_or_url"] = result["title"][0]["plain_text"]
                    text = f"id: {result['id']}\ntitle_or_url: {result['title'][0]['plain_text']}\n"
                else:
                    result_data["title_or_url"] = "N/A"
                    text = f"id: {result['id']}\ntitle_or_url: N/A\n"

            text += f"type: {result['object']}\nlast_edited_time: {result['last_edited_time']}\n\n"
            combined_text += text
            records.append(Data(text=text, data=result_data))

        self.status = records
        return records

    def build_tool(self) -> Tool:
        return StructuredTool.from_function(
            name="notion_search",
            description="Search Notion pages and databases. "
            "Input should include the search query and optionally filter type and sort direction.",
            func=self._search_notion,
            args_schema=self.NotionSearchSchema,
        )

    def _search_notion(
        self, query: str, filter_value: str = "page", sort_direction: str = "descending"
    ) -> list[dict[str, Any]]:
        url = "https://api.notion.com/v1/search"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        data = {
            "query": query,
            "filter": {"value": filter_value, "property": "object"},
            "sort": {"direction": sort_direction, "timestamp": "last_edited_time"},
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()

        results = response.json()
        return results["results"]
