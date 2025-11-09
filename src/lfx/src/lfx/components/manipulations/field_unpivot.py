"""ETL Field Unpivot Component
多列转换为多行组件 - 将多个列转换为行数据（unpivot操作）
支持灵活的键值对映射和大数据量处理
"""

from typing import Any

import i18n
import pandas as pd
from pandas import DataFrame

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, IntInput, MessageTextInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFieldUnpivotComponent(Component):
    """多列转换为多行组件 - 执行unpivot操作"""

    display_name = i18n.t("components.manipulations.field_unpivot.display_name")
    description = i18n.t("components.manipulations.field_unpivot.description")
    icon = "unfold-vertical"
    name = "ETLFieldUnpivot"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_unpivot.data_input.display_name"),
            info=i18n.t("components.manipulations.field_unpivot.data_input.info"),
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="key_field",
            display_name=i18n.t("components.manipulations.field_unpivot.key_field.display_name"),
            info=i18n.t("components.manipulations.field_unpivot.key_field.info"),
            value="key",
            required=True,
        ),
        MessageTextInput(
            name="value_field",
            display_name=i18n.t("components.manipulations.field_unpivot.value_field.display_name"),
            info=i18n.t("components.manipulations.field_unpivot.value_field.info"),
            value="value",
            required=True,
        ),
        TableInput(
            name="field_mapping",
            display_name=i18n.t("components.manipulations.field_unpivot.field_mapping.display_name"),
            info=i18n.t("components.manipulations.field_unpivot.field_mapping.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t("components.manipulations.field_unpivot.field_mapping.source_field"),
                    "type": "str",
                },
                {
                    "name": "key_value",
                    "display_name": i18n.t("components.manipulations.field_unpivot.field_mapping.key_value"),
                    "type": "str",
                },
            ],
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.manipulations.field_unpivot.field_mapping.load_fields_button"),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
            required=True,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t("components.manipulations.field_unpivot.chunk_size.display_name"),
            info=i18n.t("components.manipulations.field_unpivot.chunk_size.info"),
            value=100000,
            range_spec={"min": 1000, "max": 1000000},
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_unpivot.outputs.data"),
            method="unpivot_columns",
        ),
        Output(
            name="fields_schema",
            display_name=i18n.t("components.manipulations.field_unpivot.outputs.fields_schema"),
            method="get_fields_schema",
        ),
        Output(
            name="preview",
            display_name=i18n.t("components.manipulations.field_unpivot.outputs.preview"),
            method="preview_result",
        ),
        Output(
            name="statistics",
            display_name=i18n.t("components.manipulations.field_unpivot.outputs.statistics"),
            method="get_statistics",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """动态加载上游节点的字段列表"""
        logger.info(
            f"[FieldUnpivot] update_build_config called - field_name: {field_name}, action: {action}, field_value: {field_value}"
        )

        # 当点击"加载字段列表"按钮时（TableInput action button）
        if field_name == "field_mapping" and action == "load_fields":
            logger.info("[FieldUnpivot] Load fields button clicked - loading field options from upstream")
            try:
                # Get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data:
                    logger.warning("[FieldUnpivot] No graph data available")
                    self.status = "No graph data available. Please ensure the component is connected to a data source."
                    return build_config

                fields = []

                # Primary strategy: Try to execute upstream node to get actual data
                try:
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input", graph_data=graph_data, sample_size=1, vertex_id=node_id
                    )

                    if upstream_data:
                        # Extract field names
                        fields = self._extract_field_names(upstream_data)
                        logger.debug(f"[FieldUnpivot] Extracted {len(fields)} fields from upstream data: {fields}")
                    else:
                        logger.warning("[FieldUnpivot] No data returned from upstream node")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configuration
                    logger.warning(f"[FieldUnpivot] Upstream execution failed: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        fields = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "FieldUnpivot"
                        )

                        if fields:
                            logger.info(f"[FieldUnpivot] Extracted {len(fields)} fields from static config")
                        else:
                            logger.warning("[FieldUnpivot] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[FieldUnpivot] Static analysis also failed")

                # Update build_config with results
                if fields:
                    field_names = [field["name"] for field in fields]
                    # 1. Update source_field dropdown options in table schema
                    build_config["field_mapping"]["table_schema"][0]["options"] = field_names

                    # 2. Auto-fill field_mapping table with default mappings
                    default_mappings = []
                    for field_name in field_names:
                        default_mappings.append({"source_field": field_name, "key_value": field_name})

                    build_config["field_mapping"]["value"] = default_mappings
                    self.status = f"Successfully loaded {len(fields)} fields from upstream data source"
                    logger.info(f"[FieldUnpivot] Successfully loaded {len(fields)} fields")
                else:
                    self.status = "Unable to automatically load fields, please configure manually"
                    logger.warning("[FieldUnpivot] No fields could be extracted")

            except Exception as e:  # noqa: BLE001
                logger.error(f"[FieldUnpivot] Unexpected error loading fields: {e}", exc_info=True)
                self.status = f"Error loading fields: {e!s}"

        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """从数据流中提取字段名列表"""
        if not data_list or len(data_list) == 0:
            return []

        first_record = data_list[0]
        if hasattr(first_record, "data") and isinstance(first_record.data, dict):
            return list(first_record.data.keys())
        if isinstance(first_record, dict):
            return list(first_record.keys())

        return []

    def _process_chunk(self, df_chunk: DataFrame) -> DataFrame:
        """处理单个数据块"""
        # 获取要转换的字段和保留的字段
        if self.field_mapping:
            value_vars = [m["source_field"] for m in self.field_mapping if m.get("source_field")]
            key_mapping = {m["source_field"]: m["key_value"] for m in self.field_mapping}
        else:
            # 如果没有配置，转换所有字段
            value_vars = list(df_chunk.columns)
            key_mapping = {col: col for col in value_vars}

        # 找出id_vars（保留的字段）
        id_vars = [col for col in df_chunk.columns if col not in value_vars]

        if not value_vars:
            raise ValueError(i18n.t("components.manipulations.field_unpivot.errors.no_fields_to_unpivot"))

        # 执行unpivot操作（melt）
        melted = df_chunk.melt(
            id_vars=id_vars, value_vars=value_vars, var_name=self.key_field, value_name=self.value_field
        )

        # 应用key_value映射
        melted[self.key_field] = melted[self.key_field].map(key_mapping)

        return melted

    def unpivot_columns(self) -> list[Data]:
        """执行多列转换为多行操作"""
        try:
            self.status = i18n.t("components.manipulations.field_unpivot.status.unpivoting")
            logger.info("[FieldUnpivot] Starting unpivot operation")

            if not self.data_input:
                raise ValueError(i18n.t("components.manipulations.field_unpivot.errors.no_input_data"))

            # Handle both single Data objects and lists of Data objects
            data_items = self.data_input
            if not isinstance(data_items, list):
                data_items = [data_items]

            # Convert to DataFrame with proper error handling
            processed_data = []
            for d in data_items:
                if hasattr(d, "data") and isinstance(d.data, dict):
                    processed_data.append(d.data)
                elif isinstance(d, dict):
                    processed_data.append(d)
                elif isinstance(d, tuple):
                    # Handle tuple case - try to extract meaningful data
                    logger.warning(f"Received tuple instead of Data object: {d}")
                    if len(d) >= 2 and isinstance(d[1], dict):
                        processed_data.append(d[1])  # Use the second element if it's a dict
                    else:
                        logger.error(f"Cannot process tuple: {d}")
                        continue
                else:
                    logger.warning(f"Unknown data type {type(d)}: {d}")
                    continue

            df = pd.DataFrame(processed_data)
            total_rows = len(df)
            logger.info(f"[FieldUnpivot] Processing {total_rows} rows with {len(df.columns)} columns")

            # 对于大数据量，分块处理
            if total_rows > self.chunk_size:
                logger.info(f"[FieldUnpivot] Large dataset detected, processing in chunks of {self.chunk_size}")
                chunks = []
                for start in range(0, total_rows, self.chunk_size):
                    end = min(start + self.chunk_size, total_rows)
                    df_chunk = df.iloc[start:end]
                    processed_chunk = self._process_chunk(df_chunk)
                    chunks.append(processed_chunk)
                    logger.debug(f"[FieldUnpivot] Processed chunk {start}-{end}")

                df_result = pd.concat(chunks, ignore_index=True)
            else:
                df_result = self._process_chunk(df)

            # 转换回Data对象列表
            result = [Data(data=row.to_dict()) for _, row in df_result.iterrows()]

            self.status = i18n.t(
                "components.manipulations.field_unpivot.status.success", original=total_rows, result=len(result)
            )
            logger.info(f"[FieldUnpivot] Unpivot completed: {total_rows} rows -> {len(result)} rows")

            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_unpivot.errors.unpivot_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[FieldUnpivot] Unpivot failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def preview_result(self) -> Data:
        """预览unpivot结果"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_unpivot.errors.no_input_data")})

            # 取前10条数据进行预览
            preview_data = self.data_input[:10]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in preview_data])

            # 执行unpivot预览
            df_preview = self._process_chunk(df.head(5))

            # 计算转换信息
            original_columns = list(df.columns)
            result_columns = list(df_preview.columns)

            if self.field_mapping:
                unpivoted_fields = [m["source_field"] for m in self.field_mapping]
            else:
                unpivoted_fields = original_columns

            retained_fields = [col for col in original_columns if col not in unpivoted_fields]

            return Data(
                data={
                    "original_rows": len(df),
                    "preview_rows": len(df_preview),
                    "original_columns": original_columns,
                    "result_columns": result_columns,
                    "unpivoted_fields": unpivoted_fields,
                    "retained_fields": retained_fields,
                    "key_field": self.key_field,
                    "value_field": self.value_field,
                    "expansion_factor": len(df_preview) / len(df) if len(df) > 0 else 0,
                    "sample_data": df_preview.head(20).to_dict("records"),
                }
            )

        except Exception as e:
            logger.error(f"[FieldUnpivot] Preview failed: {e}")
            return Data(data={"error": str(e)})

    def get_statistics(self) -> Data:
        """获取unpivot统计信息"""
        try:
            if not self.data_input:
                return Data(data={"message": i18n.t("components.manipulations.field_unpivot.errors.no_input_data")})

            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            # 获取要unpivot的字段
            if self.field_mapping:
                unpivot_fields = [m["source_field"] for m in self.field_mapping if m.get("source_field")]
            else:
                unpivot_fields = list(df.columns)

            retained_fields = [col for col in df.columns if col not in unpivot_fields]

            stats = {
                "total_input_rows": len(df),
                "total_columns": len(df.columns),
                "unpivot_fields_count": len(unpivot_fields),
                "retained_fields_count": len(retained_fields),
                "estimated_output_rows": len(df) * len(unpivot_fields),
                "key_field": self.key_field,
                "value_field": self.value_field,
            }

            # 计算非空值统计
            if unpivot_fields:
                non_null_counts = []
                for field in unpivot_fields:
                    if field in df.columns:
                        non_null_counts.append(df[field].notna().sum())

                if non_null_counts:
                    stats.update(
                        {
                            "avg_non_null_values_per_field": sum(non_null_counts) / len(non_null_counts),
                            "total_non_null_values": sum(non_null_counts),
                        }
                    )

            return Data(data=stats)

        except Exception as e:
            logger.error(f"[FieldUnpivot] Statistics failed: {e}")
            return Data(data={"error": str(e)})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the unpivot result.

        Returns:
            Data: A Data object containing fields metadata
        """
        try:
            logger.info("[FieldUnpivot] get_fields_schema called")

            if not self.data_input:
                return Data(data={"fields": [], "field_names": []})

            # Get sample data to infer schema
            sample_data = self.data_input[:1]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in sample_data])

            if df.empty:
                return Data(data={"fields": [], "field_names": []})

            # Process sample to get result schema
            df_result = self._process_chunk(df)

            fields = []
            for col in df_result.columns:
                dtype = df_result[col].dtype
                if pd.api.types.is_integer_dtype(dtype):
                    data_type = "integer"
                elif pd.api.types.is_float_dtype(dtype):
                    data_type = "float"
                elif pd.api.types.is_bool_dtype(dtype):
                    data_type = "boolean"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    data_type = "datetime"
                else:
                    data_type = "string"

                fields.append({"name": col, "type": data_type})

            field_names = [f["name"] for f in fields]

            logger.info(f"[FieldUnpivot] Returning schema with {len(fields)} fields")
            return Data(data={"fields": fields, "field_names": field_names})

        except Exception as e:
            logger.error(f"[FieldUnpivot] Failed to get fields schema: {e}")
            return Data(data={"fields": [], "field_names": []})
