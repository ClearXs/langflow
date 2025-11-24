"""通用元数据提取器

用于没有特定Extractor的组件类型，提供基础的元数据提取功能。
"""

from lfx.log.logger import logger

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
        """提取输出元信息（通用）- 复用 ETL 提取器的通用逻辑

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            基础的输出元信息，包含：
            - data_metrics: 数据统计信息（row_count, field_count, data_size）
            - result_count: 结果数量
            - artifact_count: artifact数量
        """
        metadata = {}

        # 统计输出数量
        if results:
            metadata["result_count"] = len(results)

        if artifacts:
            metadata["artifact_count"] = len(artifacts)

        # 复用 ETL 提取器的通用数据分析逻辑
        if results:
            try:
                logger.info(
                    f"[METADATA_DEBUG] GenericMetadataExtractor delegating to ETL extractor for component: {self.vertex.vertex_type}"
                )
                from langflow.services.metadata_extractors.etl_extractor import ETLMetadataExtractor

                # 使用 ETL 提取器的通用分析方法
                etl_extractor = ETLMetadataExtractor(self.vertex)
                output_data = await etl_extractor._analyze_output_data(results)

                logger.info(f"[METADATA_DEBUG] GenericMetadataExtractor got output_data: {output_data}")

                if output_data:
                    # 为前端提供 data_metrics
                    metadata["data_metrics"] = {
                        "row_count": output_data.get("row_count", 0),
                        "field_count": output_data.get("field_count", 0),
                        "data_size": output_data.get("data_size", 0),
                    }
                    logger.info(
                        f"[METADATA_DEBUG] GenericMetadataExtractor created data_metrics: {metadata['data_metrics']}"
                    )
            except Exception as e:
                logger.error(f"[METADATA_DEBUG] Failed to extract universal data metrics: {e}")
                import traceback

                logger.error(f"[METADATA_DEBUG] Traceback: {traceback.format_exc()}")

        return metadata
