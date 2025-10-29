"""组件元数据提取器

该模块提供不同类型组件的元数据提取功能。
根据组件类型，自动选择合适的Extractor来提取类型特定的信息。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langflow.graph.vertex.base import Vertex
    from langflow.services.metadata_extractors.base import BaseMetadataExtractor


def get_metadata_extractor(vertex: "Vertex") -> "BaseMetadataExtractor":
    """根据组件类型获取对应的MetadataExtractor

    Args:
        vertex: 顶点对象

    Returns:
        对应类型的MetadataExtractor实例
    """
    from langflow.services.metadata_extractors.agent_extractor import AgentMetadataExtractor
    from langflow.services.metadata_extractors.etl_extractor import ETLMetadataExtractor
    from langflow.services.metadata_extractors.generic_extractor import GenericMetadataExtractor
    from langflow.services.metadata_extractors.llm_extractor import LLMMetadataExtractor
    from langflow.services.metadata_extractors.tool_extractor import ToolMetadataExtractor

    component_class = vertex.vertex_type.lower()

    # ETL组件
    if any(x in component_class for x in ["etl", "table", "kafka", "excel", "csv", "cdc"]):
        return ETLMetadataExtractor(vertex)

    # LLM模型组件
    if any(x in component_class for x in ["model", "llm", "openai", "anthropic", "groq", "cohere"]):
        return LLMMetadataExtractor(vertex)

    # Agent组件
    if "agent" in component_class:
        return AgentMetadataExtractor(vertex)

    # Tool组件
    if "tool" in component_class:
        return ToolMetadataExtractor(vertex)

    # 其他组件使用通用提取器
    return GenericMetadataExtractor(vertex)


__all__ = ["get_metadata_extractor"]
