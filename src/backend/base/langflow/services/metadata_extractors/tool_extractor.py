"""Tool组件元数据提取器

专门用于Tool组件的元数据提取。
提取工具调用参数、API响应等信息。
"""

from langflow.services.metadata_extractors.base import BaseMetadataExtractor


class ToolMetadataExtractor(BaseMetadataExtractor):
    """Tool组件元数据提取器

    提取Tool相关的元数据：
    - 工具参数
    - API调用信息
    - 响应结果
    """

    async def extract_input_metadata(self) -> dict:
        """提取输入元信息（Tool特定）

        Returns:
            输入元信息字典
        """
        metadata = {}

        # 统计参数数量
        if self.vertex.params:
            metadata["param_count"] = len(self.vertex.params)

        return metadata

    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息（Tool特定）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            输出元信息字典
        """
        metadata = {}

        # 统计输出数量
        if results:
            metadata["result_count"] = len(results)

        return metadata
