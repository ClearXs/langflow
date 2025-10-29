"""通用元数据提取器

用于没有特定Extractor的组件类型，提供基础的元数据提取功能。
"""

from langflow.services.metadata_extractors.base import BaseMetadataExtractor


class GenericMetadataExtractor(BaseMetadataExtractor):
    """通用元数据提取器

    提供基础的元数据提取，适用于所有组件类型。
    """

    async def extract_input_metadata(self) -> dict:
        """提取输入元信息（通用）

        Returns:
            基础的输入元信息
        """
        metadata = {}

        # 提取基础信息
        if hasattr(self.vertex, "params") and self.vertex.params:
            metadata["param_count"] = len(self.vertex.params)

        return metadata

    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息（通用）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            基础的输出元信息
        """
        metadata = {}

        # 统计输出数量
        if results:
            metadata["result_count"] = len(results)

        if artifacts:
            metadata["artifact_count"] = len(artifacts)

        return metadata
