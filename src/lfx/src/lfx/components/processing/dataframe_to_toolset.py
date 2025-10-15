"""DataFrame to Toolset Component.

This component converts each row of a DataFrame into a callable tool/action within a toolset.
Each row becomes a tool where the action name comes from one column and the content/response
comes from another column.
"""

import os
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import i18n
from langchain.tools import StructuredTool
from pydantic import BaseModel, create_model

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing.constants import Tool
from lfx.io import HandleInput, Output, StrInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message

if TYPE_CHECKING:
    from lfx.field_typing.constants import Tool


class DataFrameToToolsetComponent(LCToolComponent):
    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    """Component that converts DataFrame rows into a toolset with multiple callable actions."""

    display_name = i18n.t("components.processing.dataframe_to_toolset.display_name")
    description = i18n.t("components.processing.dataframe_to_toolset.description")
    icon = "wrench"
    name = "DataFrameToToolset"

    inputs = [
        HandleInput(
            name="dataframe",
            display_name=i18n.t("components.processing.dataframe_to_toolset.dataframe.display_name"),
            input_types=["DataFrame"],
            info=i18n.t("components.processing.dataframe_to_toolset.dataframe.info"),
            required=True,
        ),
        StrInput(
            name="tool_name_column",
            display_name=i18n.t("components.processing.dataframe_to_toolset.tool_name_column.display_name"),
            info=i18n.t("components.processing.dataframe_to_toolset.tool_name_column.info"),
            required=True,
        ),
        StrInput(
            name="tool_output_column",
            display_name=i18n.t("components.processing.dataframe_to_toolset.tool_output_column.display_name"),
            info=i18n.t("components.processing.dataframe_to_toolset.tool_output_column.info"),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.processing.dataframe_to_toolset.outputs.tools.display_name"),
            name="tools",
            method="build_tools",
        ),
        Output(
            display_name=i18n.t("components.processing.dataframe_to_toolset.outputs.message.display_name"),
            name="message",
            method="get_message",
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tools_cache: list[Tool] = []
        self._action_data: dict[str, dict[str, str]] = {}

    def _sanitize_tool_name(self, name: str) -> str:
        """Sanitize tool name to match required format '^[a-zA-Z0-9_-]+$'."""
        # Replace any non-alphanumeric characters (except _ and -) with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name))
        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != "_":
            sanitized = f"tool_{sanitized}"
        return sanitized or "unnamed_tool"

    def _prepare_action_data(self) -> None:
        """Prepare action data from DataFrame."""
        # Check if dataframe exists and is valid
        if not hasattr(self, "dataframe") or self.dataframe is None:
            self._action_data = {}
            return

        if not isinstance(self.dataframe, DataFrame):
            self._action_data = {}
            return

        if not hasattr(self.dataframe, "columns"):
            self._action_data = {}
            return

        # Check if column names are provided
        if not self.tool_name_column or not self.tool_output_column:
            self._action_data = {}
            return

        if self.tool_name_column not in self.dataframe.columns:
            msg = i18n.t(
                "components.processing.dataframe_to_toolset.errors.column_not_found",
                column=self.tool_name_column,
                columns=list(self.dataframe.columns),
            )
            raise ValueError(msg)

        if self.tool_output_column not in self.dataframe.columns:
            msg = i18n.t(
                "components.processing.dataframe_to_toolset.errors.column_not_found",
                column=self.tool_output_column,
                columns=list(self.dataframe.columns),
            )
            raise ValueError(msg)

        # Clear previous data
        self._action_data = {}

        # Process each row to create action mappings
        for _, row in self.dataframe.iterrows():
            action_name = str(row[self.tool_name_column]).strip()
            content = str(row[self.tool_output_column]).strip()

            if action_name and content:
                sanitized_name = self._sanitize_tool_name(action_name)
                self._action_data[sanitized_name] = {
                    "original_name": action_name,
                    "content": content,
                    "sanitized_name": sanitized_name,
                }

    def _create_action_function(self, action_name: str, content: str):
        """Create a function for a specific action that returns the content."""

        def action_function(**kwargs) -> str:
            # You could extend this to use kwargs to modify the content
            # For now, just return the stored content
            self.log(kwargs)  # TODO: Coming soon: implement arguments to modify content
            return content

        action_function.__name__ = f"execute_{action_name}"
        action_function.__doc__ = i18n.t(
            "components.processing.dataframe_to_toolset.action_function_doc", action_name=action_name
        )
        return action_function

    def build_tools(self) -> list[Tool]:
        """Build the toolset from DataFrame data."""
        # Handle case where inputs are not ready
        if not hasattr(self, "dataframe") or self.dataframe is None:
            return []

        self._prepare_action_data()

        if not self._action_data:
            return []

        tools_description_preview_length = 100
        tools_description_content_length = 200

        tools = []

        for sanitized_name, action_info in self._action_data.items():
            original_name = action_info["original_name"]
            content = action_info["content"]

            # Create a simple schema for this tool (no parameters needed)
            # But we could extend this to accept parameters if needed
            tool_schema = create_model(
                f"{sanitized_name}Schema",
                __base__=BaseModel,
                # Add parameters here if you want the tools to accept inputs
                # For now, keeping it simple with no parameters
            )

            # Create the tool function
            tool_function = self._create_action_function(sanitized_name, content)

            # Create description with preview
            content_preview = content[:tools_description_preview_length]
            has_more = len(content) > tools_description_preview_length
            description = i18n.t(
                "components.processing.dataframe_to_toolset.tool_description",
                action_name=original_name,
                content=content_preview,
                ellipsis="..." if has_more else "",
            )

            # Create the StructuredTool
            tool = StructuredTool(
                name=sanitized_name,
                description=description,
                func=tool_function,
                args_schema=tool_schema,
                handle_tool_error=True,
                tags=[sanitized_name],
                metadata={
                    "display_name": original_name,
                    "display_description": i18n.t(
                        "components.processing.dataframe_to_toolset.action_metadata", action_name=original_name
                    ),
                    "original_name": original_name,
                    "content_preview": content[:tools_description_content_length],
                },
            )

            tools.append(tool)

        self._tools_cache = tools
        return tools

    def build_tool(self) -> Tool:
        """Build a single tool (for compatibility with LCToolComponent)."""
        tools = self.build_tools()
        if not tools:
            # Return a placeholder tool when no data is available
            def placeholder_function(**kwargs) -> str:
                self.log(kwargs)  # TODO: Coming soon: implement arguments to modify content
                return i18n.t("components.processing.dataframe_to_toolset.placeholder_message")

            return StructuredTool(
                name="placeholder_tool",
                description=i18n.t("components.processing.dataframe_to_toolset.placeholder_description"),
                func=placeholder_function,
                args_schema=create_model("PlaceholderSchema", __base__=BaseModel),
            )

        # Return the first tool, or create a composite tool
        return tools[0]

    def get_message(self) -> Message:
        """Get a message describing the created toolset."""
        # Handle case where inputs are not ready
        if not hasattr(self, "dataframe") or self.dataframe is None:
            return Message(text=i18n.t("components.processing.dataframe_to_toolset.messages.waiting_input"))

        self._prepare_action_data()

        if not self._action_data:
            return Message(text=i18n.t("components.processing.dataframe_to_toolset.messages.no_tools"))

        tool_count = len(self._action_data)
        tool_names = [info["original_name"] for info in self._action_data.values()]

        message_text = (
            i18n.t("components.processing.dataframe_to_toolset.messages.toolset_created", count=tool_count) + "\n"
        )
        for i, name in enumerate(tool_names, 1):
            message_text += f"{i}. {name}\n"

        return Message(text=message_text)

    def run_model(self) -> list[Data]:
        """Run the model and return tool information as Data objects."""
        # Handle case where inputs are not ready
        if not hasattr(self, "dataframe") or self.dataframe is None:
            return [Data(data={"status": i18n.t("components.processing.dataframe_to_toolset.status.waiting_input")})]

        tools = self.build_tools()

        if not tools:
            return [Data(data={"status": i18n.t("components.processing.dataframe_to_toolset.status.no_tools")})]

        results = []
        for tool in tools:
            tool_data = {
                "tool_name": tool.name,
                "display_name": tool.metadata.get("display_name", tool.name)
                if hasattr(tool, "metadata")
                else tool.name,
                "description": tool.description,
                "original_name": tool.metadata.get("original_name", "") if hasattr(tool, "metadata") else "",
                "content_preview": tool.metadata.get("content_preview", "") if hasattr(tool, "metadata") else "",
            }
            results.append(Data(data=tool_data))

        return results
