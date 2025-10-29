"""ETL组件元数据提取器

专门用于ETL组件（table_input, kafka_input, data_cleaning等）的元数据提取。
提取数据行数、schema、转换详情等ETL特定信息。
"""

from loguru import logger

from langflow.services.metadata_extractors.base import BaseMetadataExtractor


class ETLMetadataExtractor(BaseMetadataExtractor):
    """ETL组件元数据提取器

    提取ETL相关的元数据：
    - 数据行数、字段数
    - 数据schema
    - 转换详情（字段变化、行数变化）
    - 数据采样
    """

    async def extract_input_metadata(self) -> dict:
        """提取输入元信息（ETL特定）

        Returns:
            输入元信息字典，包含：
            - input_data: 输入数据统计信息（如果有上游组件）
            - source_info: 数据源信息（数据库、文件、Kafka topic等）
        """
        metadata = {}

        # 提取数据源信息（从组件参数中）
        source_info = self._extract_source_info()
        if source_info:
            metadata["source_info"] = source_info

        return metadata

    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息（ETL特定）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            输出元信息字典，包含：
            - output_data: 输出数据统计信息
            - transformation: 转换详情（如果是transformation组件）
        """
        metadata = {}

        # 分析输出数据
        if results:
            output_data = await self._analyze_output_data(results)
            if output_data:
                metadata["output_data"] = output_data

        # 如果是transformation组件，计算转换指标
        if self._is_transformation_component():
            transformation = self._calculate_transformation_metrics(results)
            if transformation:
                metadata["transformation"] = transformation

        return metadata

    def _extract_source_info(self) -> dict | None:
        """从组件参数中提取数据源信息

        Returns:
            数据源信息字典，例如：
            {
                "type": "database|file|kafka|api",
                "connection": "MySQL Production",
                "table": "orders",
                "query": "SELECT * FROM orders WHERE...",
            }
        """
        if not self.vertex.params:
            return None

        source_info = {}

        # 数据库输入组件
        if any(x in self.vertex.vertex_type.lower() for x in ["tableinput", "sqlinput"]):
            if "datasource_selector" in self.vertex.params:
                source_info["type"] = "database"
                ds = self.vertex.params["datasource_selector"]
                source_info["connection"] = getattr(ds, "value", str(ds)) if hasattr(ds, "value") else str(ds)

            if "sql_query" in self.vertex.params:
                query = self.vertex.params["sql_query"]
                source_info["query"] = getattr(query, "value", str(query)) if hasattr(query, "value") else str(query)

        # Kafka输入组件
        elif "kafka" in self.vertex.vertex_type.lower():
            source_info["type"] = "kafka"
            if "topic" in self.vertex.params:
                topic = self.vertex.params["topic"]
                source_info["topic"] = getattr(topic, "value", str(topic)) if hasattr(topic, "value") else str(topic)
            if "bootstrap_servers" in self.vertex.params:
                servers = self.vertex.params["bootstrap_servers"]
                source_info["bootstrap_servers"] = getattr(servers, "value", str(servers)) if hasattr(servers, "value") else str(servers)

        # 文件输入组件（Excel, CSV等）
        elif any(x in self.vertex.vertex_type.lower() for x in ["excel", "csv"]):
            source_info["type"] = "file"
            if "file_path" in self.vertex.params:
                path = self.vertex.params["file_path"]
                source_info["file_path"] = getattr(path, "value", str(path)) if hasattr(path, "value") else str(path)

        return source_info if source_info else None

    async def _analyze_output_data(self, results: dict) -> dict | None:
        """分析输出数据，提取统计信息

        Args:
            results: 组件执行结果

        Returns:
            数据统计信息字典，例如：
            {
                "row_count": 15423,
                "field_count": 12,
                "byte_size": 2456789,
                "schema": {...},
                "sample": [...]
            }
        """
        try:
            # 从results中提取Data对象
            data_list = self._extract_data_from_results(results)
            if not data_list:
                return None

            row_count = len(data_list)
            schema = self._extract_schema(data_list)
            field_count = len(schema.get("fields", [])) if schema else 0

            # 智能采样策略
            sample = None
            if row_count <= 100:
                # 小数据集：不存储sample（可以从results中获取）
                pass
            elif row_count <= 1000:
                # 中等数据集：采样50行
                sample = self._sample_data(data_list, 50)
            else:
                # 大数据集：采样100行
                sample = self._sample_data(data_list, 100)

            return {
                "row_count": row_count,
                "field_count": field_count,
                "schema": schema,
                "sample": sample,
            }

        except Exception as e:
            logger.warning(f"Failed to analyze output data: {e}")
            return None

    def _extract_data_from_results(self, results: dict) -> list | None:
        """从results字典中提取Data对象列表

        Args:
            results: 组件执行结果

        Returns:
            Data对象列表
        """
        # 尝试从常见的key中提取数据
        for key in ["results", "data", "output", "Data"]:
            if key in results:
                data = results[key]
                # 如果是Data对象，转换为列表
                if not isinstance(data, list):
                    data = [data] if data is not None else []
                return data

        return None

    def _extract_schema(self, data_list: list) -> dict | None:
        """从Data列表中提取schema

        Args:
            data_list: Data对象列表

        Returns:
            Schema字典，例如：
            {
                "fields": [
                    {"name": "field1", "type": "string"},
                    {"name": "field2", "type": "integer"},
                ]
            }
        """
        if not data_list:
            return None

        try:
            # 从第一个Data对象中提取字段
            first_data = data_list[0]

            # 处理Data对象
            if hasattr(first_data, "data") and isinstance(first_data.data, dict):
                fields = []
                for field_name, field_value in first_data.data.items():
                    fields.append({
                        "name": field_name,
                        "type": type(field_value).__name__ if field_value is not None else "unknown"
                    })
                return {"fields": fields}

            # 处理字典
            if isinstance(first_data, dict):
                fields = []
                for field_name, field_value in first_data.items():
                    fields.append({
                        "name": field_name,
                        "type": type(field_value).__name__ if field_value is not None else "unknown"
                    })
                return {"fields": fields}

        except Exception as e:
            logger.warning(f"Failed to extract schema: {e}")

        return None

    def _sample_data(self, data_list: list, sample_size: int) -> list:
        """对数据进行采样

        Args:
            data_list: 数据列表
            sample_size: 采样数量

        Returns:
            采样后的数据列表
        """
        if len(data_list) <= sample_size:
            return data_list[:sample_size]

        # 分层采样：在数据集的不同位置采样
        step = len(data_list) / sample_size
        indices = [int(i * step) for i in range(sample_size)]
        sampled = []

        for idx in indices:
            if idx < len(data_list):
                item = data_list[idx]
                # 提取数据的简化版本
                if hasattr(item, "data"):
                    sampled.append(item.data)
                elif isinstance(item, dict):
                    sampled.append(item)
                else:
                    sampled.append(str(item))

        return sampled

    def _is_transformation_component(self) -> bool:
        """判断是否是transformation组件

        Returns:
            是否是transformation组件
        """
        component_class = self.vertex.vertex_type.lower()
        return any(x in component_class for x in [
            "cleaning", "mapping", "pivot", "split", "merge",
            "filter", "transform", "manipulation"
        ])

    def _calculate_transformation_metrics(self, results: dict) -> dict | None:
        """计算转换指标

        Args:
            results: 组件执行结果

        Returns:
            转换指标字典，例如：
            {
                "type": "filter_and_aggregate",
                "rows_added": 100,
                "fields_added": ["new_field1"],
                "fields_removed": ["old_field1"],
            }
        """
        # TODO: 实现更复杂的转换指标计算
        # 需要对比输入和输出的schema和行数
        return {
            "type": "transformation",
            "note": "Detailed transformation metrics not yet implemented"
        }
