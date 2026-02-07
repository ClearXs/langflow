"""Langflow Agents Module.

This module contains AI agents for various tasks:
- new_chat: SurfSense deep agent with configurable tools for knowledge base search,
  podcast generation, web scraping, and more
- podcaster: Podcast generation agent using LangGraph
"""

# New Chat Agent exports
from .new_chat import (
    BUILTIN_TOOLS,
    SURFSENSE_CITATION_INSTRUCTIONS,
    SURFSENSE_SYSTEM_PROMPT,
    SurfSenseContextSchema,
    ToolDefinition,
    build_surfsense_system_prompt,
    build_tools,
    create_chat_litellm_from_config,
    create_display_image_tool,
    create_generate_podcast_tool,
    create_link_preview_tool,
    create_scrape_webpage_tool,
    create_search_knowledge_base_tool,
    create_surfsense_deep_agent,
    format_documents_for_context,
    get_all_tool_names,
    get_default_enabled_tools,
    get_tool_by_name,
    load_llm_config_from_yaml,
    search_knowledge_base_async,
)

# Podcaster Agent exports
from .podcaster import graph as podcaster_graph

__all__ = [
    # New Chat Agent - Core
    "create_surfsense_deep_agent",
    "SurfSenseContextSchema",
    # New Chat Agent - System Prompts
    "SURFSENSE_SYSTEM_PROMPT",
    "SURFSENSE_CITATION_INSTRUCTIONS",
    "build_surfsense_system_prompt",
    # New Chat Agent - LLM Config
    "create_chat_litellm_from_config",
    "load_llm_config_from_yaml",
    # New Chat Agent - Tools Registry
    "BUILTIN_TOOLS",
    "ToolDefinition",
    "build_tools",
    "get_all_tool_names",
    "get_default_enabled_tools",
    "get_tool_by_name",
    # New Chat Agent - Tool Factories
    "create_search_knowledge_base_tool",
    "create_generate_podcast_tool",
    "create_link_preview_tool",
    "create_display_image_tool",
    "create_scrape_webpage_tool",
    # New Chat Agent - Knowledge Base Utilities
    "search_knowledge_base_async",
    "format_documents_for_context",
    # Podcaster Agent
    "podcaster_graph",
]
