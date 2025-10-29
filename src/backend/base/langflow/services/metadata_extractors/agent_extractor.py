"""Agent组件元数据提取器

专门用于Agent组件的元数据提取。
提取Agent决策过程、工具调用链等信息。
"""

from langflow.services.metadata_extractors.base import BaseMetadataExtractor


class AgentMetadataExtractor(BaseMetadataExtractor):
    """Agent组件元数据提取器

    提取Agent相关的元数据：
    - Agent类型和配置
    - 工具调用链
    - 决策步骤
    """

    async def extract_input_metadata(self) -> dict:
        """提取输入元信息（Agent特定）

        Returns:
            输入元信息字典
        """
        metadata = {}

        # 提取Agent配置
        if self.vertex.params:
            if "tools" in self.vertex.params:
                tools = self.vertex.params["tools"]
                if isinstance(tools, list):
                    metadata["tool_count"] = len(tools)

        return metadata

    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息（Agent特定）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            输出元信息字典
        """
        metadata = {}

        # 统计步骤数
        if results:
            metadata["execution_steps"] = len(results)

        return metadata
