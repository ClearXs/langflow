"""ETL组件元数据提取器

专门用于ETL组件（table_input, kafka_input, data_cleaning等）的元数据提取。
提取数据行数、schema、转换详情等ETL特定信息。
"""

import json

from lfx.log.logger import logger

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
            - data_metrics: 数据统计信息（直接用于前端显示）
            - output_data: 完整的输出数据分析（包含schema和sample）
            - transformation: 转换详情（如果是transformation组件）
        """
        metadata = {}

        # 分析输出数据
        if results:
            output_data = await self._analyze_output_data(results)
            if output_data:
                # 为前端提供 data_metrics（包含 row_count, field_count, data_size）
                metadata["data_metrics"] = {
                    "row_count": output_data.get("row_count", 0),
                    "field_count": output_data.get("field_count", 0),
                    "data_size": output_data.get("data_size", 0),
                }
                # 保留完整的 output_data（包含 schema 和 sample）
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
                source_info["bootstrap_servers"] = (
                    getattr(servers, "value", str(servers)) if hasattr(servers, "value") else str(servers)
                )

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
        logger.info(f"[METADATA_DEBUG] Starting _analyze_output_data for component: {self.vertex.vertex_type}")
        logger.info(f"[METADATA_DEBUG] Results keys: {list(results.keys()) if results else 'None'}")
        logger.info(f"[METADATA_DEBUG] Results structure: {type(results)}")

        if results:
            for key, value in results.items():
                logger.info(f"[METADATA_DEBUG] Result '{key}': {type(value)} - {str(value)[:200]}...")

        try:
            # 从results中提取Data对象
            data_list = self._extract_data_from_results(results)
            logger.info(f"[METADATA_DEBUG] Extracted data_list: {len(data_list) if data_list else 'None'} items")

            if not data_list:
                logger.warning(
                    f"[METADATA_DEBUG] No data extracted from results for component: {self.vertex.vertex_type}"
                )
                return None

            row_count = len(data_list)
            schema = self._extract_schema(data_list)
            field_count = len(schema.get("fields", [])) if schema else 0

            # 估算数据大小（字节）
            data_size = self._estimate_data_size(data_list)

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
                "data_size": data_size,
                "schema": schema,
                "sample": sample,
            }

        except Exception as e:
            logger.warning(f"Failed to analyze output data: {e}")
            return None

    def _extract_data_from_results(self, results: dict) -> list | None:
        """通用数据提取：从任何组件输出中提取数据对象

        遍历所有输出，过滤掉纯元数据输出，提取实际数据对象。
        支持 Data、DataFrame、list、dict 等各种类型。

        Args:
            results: 组件执行结果字典

        Returns:
            Data对象列表，如果没有找到数据则返回None
        """
        logger.info("[METADATA_DEBUG] Starting _extract_data_from_results")
        all_data = []

        if not results:
            logger.warning("[METADATA_DEBUG] Results is None or empty")
            return None

        logger.info(f"[METADATA_DEBUG] Processing {len(results)} output items")

        for output_name, output_data in results.items():
            logger.info(f"[METADATA_DEBUG] Processing output: '{output_name}' = {type(output_data)}")

            # 跳过纯元数据输出
            if self._is_metadata_output(output_name):
                logger.info(f"[METADATA_DEBUG] Skipping metadata output: '{output_name}'")
                continue

            # 从各种输出类型中提取数据
            extracted_data = self._extract_from_output(output_data)
            logger.info(
                f"[METADATA_DEBUG] Extracted {len(extracted_data) if extracted_data else 0} data items from '{output_name}'"
            )

            if extracted_data:
                all_data.extend(extracted_data)

        logger.info(f"[METADATA_DEBUG] Total data extracted: {len(all_data)} items")
        return all_data if all_data else None

    def _is_metadata_output(self, output_name: str) -> bool:
        """判断输出是否为纯元数据（不包含实际数据）

        Args:
            output_name: 输出的名称

        Returns:
            True 表示该输出是纯元数据，应该跳过
        """
        metadata_outputs = {
            "row_count",
            "field_count",
            "fields_schema",
            "schema_info",
            "sample_data",
            "consumer_info",
            "connection_info",
            "metadata",
            "status",
            "error",
            "warning",
            "total_statements",
            "successful_statements",
            "failed_statements",
            "total_rows_affected",
        }
        return output_name.lower() in metadata_outputs

    def _extract_from_output(self, output_data) -> list:
        """从各种输出类型中提取数据对象

        支持的类型：
        - Data 对象（有 .data 属性）
        - list（Data对象列表、dict列表等）
        - DataFrame（有 .to_dict() 方法）
        - dict（原始字典）
        - 其他类型（string、number等）

        Args:
            output_data: 组件的输出数据

        Returns:
            Data对象列表
        """
        from langflow.schema import Data

        # 处理 None
        if output_data is None:
            return []

        # 处理 Data 对象
        if hasattr(output_data, "data"):
            return [output_data]

        # 处理列表
        if isinstance(output_data, list):
            data_list = []
            for item in output_data:
                if item is None:
                    continue
                if hasattr(item, "data"):  # Data 对象
                    data_list.append(item)
                elif isinstance(item, dict):  # 原始 dict
                    # 检查是否是嵌套的结果结构（如 SQL 脚本）
                    if "query_data" in item and isinstance(item["query_data"], list):
                        # SQL 脚本的 statement 结果
                        for row in item["query_data"]:
                            if isinstance(row, dict):
                                data_list.append(Data(data=row))
                    else:
                        data_list.append(Data(data=item))
                else:  # 其他类型
                    data_list.append(Data(data={"value": str(item)}))
            return data_list

        # 处理 DataFrame
        if hasattr(output_data, "to_dict"):
            try:
                dict_data = output_data.to_dict(orient="records")
                return [Data(data=row) for row in dict_data]
            except Exception:
                return [Data(data={"value": str(output_data)})]

        # 处理原始字典（可能包含嵌套结构）
        if isinstance(output_data, dict):
            # 检查是否是 SQL 脚本的结果结构
            if "results" in output_data and isinstance(output_data["results"], list):
                data_list = []
                for item in output_data["results"]:
                    if isinstance(item, dict) and "query_data" in item:
                        for row in item["query_data"]:
                            if isinstance(row, dict):
                                data_list.append(Data(data=row))
                if data_list:
                    return data_list

            # 否则将整个字典作为一行数据
            return [Data(data=output_data)]

        # 处理其他类型（string、number等）
        return [Data(data={"value": str(output_data)})]

    def _extract_schema(self, data_list: list) -> dict | None:
        """从Data列表中提取schema（增强版，支持精确类型推断）

        Args:
            data_list: Data对象列表

        Returns:
            Schema字典，例如：
            {
                "fields": [
                    {"name": "field1", "type": "string", "nullable": false},
                    {"name": "field2", "type": "integer", "nullable": true},
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
                return self._build_schema_from_dict(first_data.data)

            # 处理字典
            if isinstance(first_data, dict):
                return self._build_schema_from_dict(first_data)

        except Exception as e:
            logger.warning(f"Failed to extract schema: {e}")

        return None

    def _build_schema_from_dict(self, data_dict: dict) -> dict:
        """从字典构建schema，包含精确的类型推断

        Args:
            data_dict: 数据字典

        Returns:
            Schema字典，包含字段名、类型和可空性
        """
        fields = []
        for field_name, field_value in data_dict.items():
            field_type = self._infer_type(field_value)
            fields.append({"name": field_name, "type": field_type, "nullable": field_value is None})
        return {"fields": fields}

    def _infer_type(self, value) -> str:
        """推断值的精确数据类型

        Args:
            value: 要推断类型的值

        Returns:
            类型字符串（boolean, integer, float, string, array, object, null, unknown）
        """
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "unknown"

    def _estimate_data_size(self, data_list: list) -> int:
        """估算数据大小（字节）

        使用JSON序列化的长度作为数据大小的估算值

        Args:
            data_list: 数据列表

        Returns:
            估算的数据大小（字节）
        """
        try:
            # 对于小数据集，序列化整个列表
            if len(data_list) <= 100:
                data_to_serialize = []
                for item in data_list:
                    if hasattr(item, "data"):
                        data_to_serialize.append(item.data)
                    elif isinstance(item, dict):
                        data_to_serialize.append(item)
                    else:
                        data_to_serialize.append(str(item))

                json_str = json.dumps(data_to_serialize, ensure_ascii=False)
                return len(json_str.encode("utf-8"))

            # 对于大数据集，采样估算
            sample_size = min(100, len(data_list))
            sample = self._sample_data(data_list, sample_size)
            json_str = json.dumps(sample, ensure_ascii=False)
            sample_size_bytes = len(json_str.encode("utf-8"))

            # 按比例估算总大小
            total_size = int(sample_size_bytes * (len(data_list) / sample_size))
            return total_size

        except Exception as e:
            logger.warning(f"Failed to estimate data size: {e}")
            return 0

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
        return any(
            x in component_class
            for x in ["cleaning", "mapping", "pivot", "split", "merge", "filter", "transform", "manipulation"]
        )

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
        return {"type": "transformation", "note": "Detailed transformation metrics not yet implemented"}
