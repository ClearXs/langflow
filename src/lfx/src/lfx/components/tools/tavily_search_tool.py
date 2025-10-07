from enum import Enum
import i18n

import httpx
from langchain.tools import StructuredTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import BoolInput, DropdownInput, IntInput, MessageTextInput, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data

# Add at the top with other constants
MAX_CHUNKS_PER_SOURCE = 3


class TavilySearchDepth(Enum):
    BASIC = "basic"
    ADVANCED = "advanced"


class TavilySearchTopic(Enum):
    GENERAL = "general"
    NEWS = "news"


class TavilySearchTimeRange(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class TavilySearchSchema(BaseModel):
    query: str = Field(...,
                       description="The search query you want to execute with Tavily.")
    search_depth: TavilySearchDepth = Field(
        TavilySearchDepth.BASIC, description="The depth of the search.")
    topic: TavilySearchTopic = Field(
        TavilySearchTopic.GENERAL, description="The category of the search.")
    max_results: int = Field(
        5, description="The maximum number of search results to return.")
    include_images: bool = Field(
        default=False, description="Include a list of query-related images in the response.")
    include_answer: bool = Field(
        default=False, description="Include a short answer to original query.")
    chunks_per_source: int = Field(
        default=MAX_CHUNKS_PER_SOURCE,
        description=(
            "The number of content chunks to retrieve from each source (max 500 chars each). Only for advanced search."
        ),
        ge=1,
        le=MAX_CHUNKS_PER_SOURCE,
    )
    include_domains: list[str] = Field(
        default=[],
        description="A list of domains to specifically include in the search results.",
    )
    exclude_domains: list[str] = Field(
        default=[],
        description="A list of domains to specifically exclude from the search results.",
    )
    include_raw_content: bool = Field(
        default=False,
        description="Include the cleaned and parsed HTML content of each search result.",
    )
    days: int = Field(
        default=7,
        description="Number of days back from the current date to include. Only available if topic is news.",
        ge=1,
    )
    time_range: TavilySearchTimeRange | None = Field(
        default=None,
        description="The time range back from the current date to filter results.",
    )


class TavilySearchToolComponent(LCToolComponent):
    display_name = i18n.t('components.tools.tavily_search_tool.display_name')
    description = i18n.t('components.tools.tavily_search_tool.description')
    icon = "TavilyIcon"
    name = "TavilyAISearch"
    documentation = "https://docs.tavily.com/"
    legacy = True
    replacement = ["tavily.TavilySearchComponent"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.api_key.display_name'),
            required=True,
            info=i18n.t('components.tools.tavily_search_tool.api_key.info'),
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.query.display_name'),
            info=i18n.t('components.tools.tavily_search_tool.query.info'),
        ),
        DropdownInput(
            name="search_depth",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.search_depth.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.search_depth.info'),
            options=list(TavilySearchDepth),
            value=TavilySearchDepth.ADVANCED,
            advanced=True,
        ),
        IntInput(
            name="chunks_per_source",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.chunks_per_source.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.chunks_per_source.info'),
            value=MAX_CHUNKS_PER_SOURCE,
            advanced=True,
        ),
        DropdownInput(
            name="topic",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.topic.display_name'),
            info=i18n.t('components.tools.tavily_search_tool.topic.info'),
            options=list(TavilySearchTopic),
            value=TavilySearchTopic.GENERAL,
            advanced=True,
        ),
        IntInput(
            name="days",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.days.display_name'),
            info=i18n.t('components.tools.tavily_search_tool.days.info'),
            value=7,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.max_results.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.max_results.info'),
            value=5,
            advanced=True,
        ),
        BoolInput(
            name="include_answer",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.include_answer.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.include_answer.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="time_range",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.time_range.display_name'),
            info=i18n.t('components.tools.tavily_search_tool.time_range.info'),
            options=list(TavilySearchTimeRange),
            value=None,
            advanced=True,
        ),
        BoolInput(
            name="include_images",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.include_images.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.include_images.info'),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="include_domains",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.include_domains.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.include_domains.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="exclude_domains",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.exclude_domains.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.exclude_domains.info'),
            advanced=True,
        ),
        BoolInput(
            name="include_raw_content",
            display_name=i18n.t(
                'components.tools.tavily_search_tool.include_raw_content.display_name'),
            info=i18n.t(
                'components.tools.tavily_search_tool.include_raw_content.info'),
            value=False,
            advanced=True,
        ),
    ]

    def run_model(self) -> list[Data]:
        # Convert string values to enum instances with validation
        try:
            search_depth_enum = (
                self.search_depth
                if isinstance(self.search_depth, TavilySearchDepth)
                else TavilySearchDepth(str(self.search_depth).lower())
            )
        except ValueError as e:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.invalid_search_depth', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message})]

        try:
            topic_enum = (
                self.topic if isinstance(self.topic, TavilySearchTopic) else TavilySearchTopic(
                    str(self.topic).lower())
            )
        except ValueError as e:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.invalid_topic', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message})]

        try:
            time_range_enum = (
                self.time_range
                if isinstance(self.time_range, TavilySearchTimeRange)
                else TavilySearchTimeRange(str(self.time_range).lower())
                if self.time_range
                else None
            )
        except ValueError as e:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.invalid_time_range', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message})]

        # Initialize domain variables as None
        include_domains = None
        exclude_domains = None

        # Only process domains if they're provided
        if self.include_domains:
            include_domains = [
                domain.strip() for domain in self.include_domains.split(",") if domain.strip()]

        if self.exclude_domains:
            exclude_domains = [
                domain.strip() for domain in self.exclude_domains.split(",") if domain.strip()]

        return self._tavily_search(
            self.query,
            search_depth=search_depth_enum,
            topic=topic_enum,
            max_results=self.max_results,
            include_images=self.include_images,
            include_answer=self.include_answer,
            chunks_per_source=self.chunks_per_source,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_raw_content=self.include_raw_content,
            days=self.days,
            time_range=time_range_enum,
        )

    def build_tool(self) -> Tool:
        tool_description = i18n.t(
            'components.tools.tavily_search_tool.tool_description')

        tool = StructuredTool.from_function(
            name="tavily_search",
            description=tool_description,
            func=self._tavily_search,
            args_schema=TavilySearchSchema,
        )

        success_message = i18n.t(
            'components.tools.tavily_search_tool.success.tool_created')
        self.status = success_message
        return tool

    def _tavily_search(
        self,
        query: str,
        *,
        search_depth: TavilySearchDepth = TavilySearchDepth.BASIC,
        topic: TavilySearchTopic = TavilySearchTopic.GENERAL,
        max_results: int = 5,
        include_images: bool = False,
        include_answer: bool = False,
        chunks_per_source: int = MAX_CHUNKS_PER_SOURCE,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_raw_content: bool = False,
        days: int = 7,
        time_range: TavilySearchTimeRange | None = None,
    ) -> list[Data]:
        # Validate input parameters
        if not query or not query.strip():
            warning_message = i18n.t(
                'components.tools.tavily_search_tool.warnings.empty_query')
            return [Data(data={"error": warning_message})]

        # Validate enum values
        if not isinstance(search_depth, TavilySearchDepth):
            error_message = i18n.t('components.tools.tavily_search_tool.errors.invalid_search_depth_type',
                                   value=search_depth)
            raise TypeError(error_message)
        if not isinstance(topic, TavilySearchTopic):
            error_message = i18n.t('components.tools.tavily_search_tool.errors.invalid_topic_type',
                                   value=topic)
            raise TypeError(error_message)

        # Validate chunks_per_source range
        if not 1 <= chunks_per_source <= MAX_CHUNKS_PER_SOURCE:
            error_message = i18n.t('components.tools.tavily_search_tool.errors.invalid_chunks_per_source',
                                   min=1, max=MAX_CHUNKS_PER_SOURCE, value=chunks_per_source)
            raise ValueError(error_message)

        # Validate days is positive
        if days < 1:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.invalid_days', value=days)
            raise ValueError(error_message)

        try:
            executing_message = i18n.t('components.tools.tavily_search_tool.info.executing_search',
                                       query=query, depth=search_depth.value, topic=topic.value)
            self.status = executing_message

            url = "https://api.tavily.com/search"
            headers = {
                "content-type": "application/json",
                "accept": "application/json",
            }
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth.value,
                "topic": topic.value,
                "max_results": max_results,
                "include_images": include_images,
                "include_answer": include_answer,
                "chunks_per_source": chunks_per_source if search_depth == TavilySearchDepth.ADVANCED else None,
                "include_domains": include_domains if include_domains else None,
                "exclude_domains": exclude_domains if exclude_domains else None,
                "include_raw_content": include_raw_content,
                "days": days if topic == TavilySearchTopic.NEWS else None,
                "time_range": time_range.value if time_range else None,
            }

            with httpx.Client(timeout=90.0) as client:
                response = client.post(url, json=payload, headers=headers)

            response.raise_for_status()
            search_results = response.json()

            if not search_results.get("results"):
                warning_message = i18n.t(
                    'components.tools.tavily_search_tool.warnings.no_results', query=query)
                return [Data(data={"message": warning_message, "query": query})]

            data_results = [
                Data(
                    data={
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "content": result.get("content"),
                        "score": result.get("score"),
                        "raw_content": result.get("raw_content") if include_raw_content else None,
                    }
                )
                for result in search_results.get("results", [])
            ]

            if include_answer and search_results.get("answer"):
                data_results.insert(
                    0, Data(data={"answer": search_results["answer"]}))

            if include_images and search_results.get("images"):
                data_results.append(
                    Data(data={"images": search_results["images"]}))

            success_message = i18n.t('components.tools.tavily_search_tool.success.search_completed',
                                     count=len(data_results), query=query)
            self.status = success_message

        except httpx.TimeoutException as e:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.timeout')
            logger.error(f"Timeout error: {e}")
            self.status = error_message
            raise ToolException(error_message) from e
        except httpx.HTTPStatusError as e:
            error_message = i18n.t('components.tools.tavily_search_tool.errors.http_error',
                                   status=e.response.status_code, text=e.response.text)
            logger.debug(error_message)
            self.status = error_message
            raise ToolException(error_message) from e
        except Exception as e:
            error_message = i18n.t(
                'components.tools.tavily_search_tool.errors.unexpected_error', error=str(e))
            logger.debug("Error running Tavily Search", exc_info=True)
            self.status = error_message
            raise ToolException(error_message) from e
        return data_results
