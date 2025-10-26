"""ETL Field Split to Columns Component
将单列数据按分隔符拆分为多个新列
支持固定字符串、正则表达式分隔，自动处理字段映射
"""

import re
from typing import Any

import i18n
import pandas as pd
from pandas import DataFrame

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, MessageTextInput, Output, StrInput, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Delimiter constants
DELIMITER_COMMA = ","
DELIMITER_SEMICOLON = ";"
DELIMITER_TAB = "\\t"
DELIMITER_PIPE = "|"
DELIMITER_SPACE = "SPACE"  # Use special identifier to avoid UI issues with empty string
DELIMITER_NEWLINE = "\\n"
DELIMITER_CUSTOM = "custom"


class ETLFieldSplitToColumnsComponent(Component):
    """单列拆分为多列组件 - 将一个字段按分隔符拆分成多个新字段"""

    display_name = i18n.t("components.manipulations.field_split_to_columns.display_name")
    description = i18n.t("components.manipulations.field_split_to_columns.description")
    icon = "columns"
    name = "ETLFieldSplitToColumns"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_split_to_columns.data_input.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="source_field",
            display_name=i18n.t("components.manipulations.field_split_to_columns.source_field.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.source_field.info"),
            options=[],  # Will be loaded dynamically from data_input
            refresh_button=True,
            real_time_refresh=True,
            required=True,
        ),
        DropdownInput(
            name="delimiter",
            display_name=i18n.t("components.manipulations.field_split_to_columns.delimiter.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.delimiter.info"),
            options=[
                DELIMITER_COMMA,
                DELIMITER_SEMICOLON,
                DELIMITER_TAB,
                DELIMITER_PIPE,
                DELIMITER_SPACE,
                DELIMITER_NEWLINE,
                DELIMITER_CUSTOM,
            ],
            options_metadata=[
                {
                    "value": DELIMITER_COMMA,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.comma"),
                },
                {
                    "value": DELIMITER_SEMICOLON,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.semicolon"),
                },
                {
                    "value": DELIMITER_TAB,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.tab"),
                },
                {
                    "value": DELIMITER_PIPE,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.pipe"),
                },
                {
                    "value": DELIMITER_SPACE,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.space"),
                },
                {
                    "value": DELIMITER_NEWLINE,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.newline"),
                },
                {
                    "value": DELIMITER_CUSTOM,
                    "label": i18n.t("components.manipulations.field_split_to_columns.delimiter.custom"),
                },
            ],
            value=DELIMITER_COMMA,
            required=True,
        ),
        StrInput(
            name="custom_delimiter",
            display_name=i18n.t("components.manipulations.field_split_to_columns.custom_delimiter.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.custom_delimiter.info"),
            value="",
            advanced=False,
        ),
        BoolInput(
            name="is_regex",
            display_name=i18n.t("components.manipulations.field_split_to_columns.is_regex.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.is_regex.info"),
            value=False,
            advanced=True,
        ),
        TableInput(
            name="new_fields_config",
            display_name=i18n.t("components.manipulations.field_split_to_columns.new_fields_config.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.new_fields_config.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t(
                        "components.manipulations.field_split_to_columns.new_fields_config.field_name"
                    ),
                    "type": "str",
                },
                {
                    "name": "field_order",
                    "display_name": i18n.t(
                        "components.manipulations.field_split_to_columns.new_fields_config.field_order"
                    ),
                    "type": "int",
                },
            ],
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
            },
        ),
        IntInput(
            name="max_splits",
            display_name=i18n.t("components.manipulations.field_split_to_columns.max_splits.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.max_splits.info"),
            value=-1,
            advanced=True,
        ),
        BoolInput(
            name="drop_source_field",
            display_name=i18n.t("components.manipulations.field_split_to_columns.drop_source_field.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.drop_source_field.info"),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="default_value",
            display_name=i18n.t("components.manipulations.field_split_to_columns.default_value.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.default_value.info"),
            value="",
            advanced=True,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t("components.manipulations.field_split_to_columns.chunk_size.display_name"),
            info=i18n.t("components.manipulations.field_split_to_columns.chunk_size.info"),
            value=100000,
            range_spec={"min": 1000, "max": 1000000},
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_split_to_columns.outputs.data"),
            method="split_to_columns",
        ),
        Output(
            name="fields_schema",
            display_name=i18n.t("components.manipulations.field_split_to_columns.outputs.fields_schema"),
            method="get_fields_schema",
        ),
        Output(
            name="preview",
            display_name=i18n.t("components.manipulations.field_split_to_columns.outputs.preview"),
            method="preview_result",
        ),
        Output(
            name="statistics",
            display_name=i18n.t("components.manipulations.field_split_to_columns.outputs.statistics"),
            method="get_statistics",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates to load fields from upstream data."""
        logger.info(
            f"[FieldSplitToColumns] update_build_config called - field_name: {field_name}, field_value: {field_value}, action: {action}"
        )

        # Load field options when refresh button is clicked
        if field_name == "source_field" and action == "refresh":
            logger.info("[FieldSplitToColumns] Refresh button clicked - loading field options from upstream")
            try:
                # Get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data:
                    logger.warning("[FieldSplitToColumns] No graph data available")
                    self.status = "No graph data available. Please ensure the component is connected to a data source."
                    return build_config

                # Get data sample from upstream node
                upstream_data = await self.get_upstream_data(
                    input_name="data_input", graph_data=graph_data, sample_size=1, vertex_id=node_id
                )

                if upstream_data:
                    # Extract field names
                    field_names = self._extract_field_names(upstream_data)
                    logger.debug(f"[FieldSplitToColumns] Extracted {len(field_names)} fields: {field_names}")
                    if field_names:
                        build_config["source_field"]["options"] = field_names
                        self.status = f"Successfully loaded {len(field_names)} fields from upstream data source"
                        logger.info(f"[FieldSplitToColumns] Successfully loaded {len(field_names)} field options")
                    else:
                        self.status = "No fields found in upstream data"
                        logger.warning("[FieldSplitToColumns] No fields found in upstream data")
                else:
                    self.status = (
                        "No data available from upstream component. Please ensure it's connected and has data."
                    )
                    logger.warning("[FieldSplitToColumns] No upstream data available")

            except ValueError as e:
                logger.warning(f"[FieldSplitToColumns] Expected error loading fields: {e}")
                self.status = f"Failed to load fields: {e!s}"
            except Exception as e:
                logger.error(f"[FieldSplitToColumns] Unexpected error loading field options: {e}", exc_info=True)
                self.status = f"Error loading fields: {e!s}"

        # Handle conditional display for custom_delimiter
        if field_name == "delimiter":
            if field_value == DELIMITER_CUSTOM:
                if "custom_delimiter" in build_config:
                    build_config["custom_delimiter"]["show"] = True
            elif "custom_delimiter" in build_config:
                build_config["custom_delimiter"]["show"] = False

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

    def _get_delimiter(self) -> str:
        """Get the actual delimiter to use"""
        if self.delimiter == DELIMITER_CUSTOM:
            return getattr(self, "custom_delimiter", ",")
        if self.delimiter == DELIMITER_TAB:
            return "\t"
        if self.delimiter == DELIMITER_NEWLINE:
            return "\n"
        if self.delimiter == DELIMITER_SPACE:
            return " "
        return self.delimiter

    def _process_chunk(self, df_chunk: DataFrame) -> DataFrame:
        """处理单个数据块"""
        if self.source_field not in df_chunk.columns:
            raise ValueError(
                i18n.t(
                    "components.manipulations.field_split_to_columns.errors.field_not_found", field=self.source_field
                )
            )

        # 获取分隔符
        delimiter_str = self._get_delimiter()
        delimiter = re.compile(delimiter_str) if self.is_regex else delimiter_str

        # 执行拆分
        if self.is_regex:
            split_cols = df_chunk[self.source_field].str.split(
                delimiter, n=self.max_splits if self.max_splits > 0 else -1, expand=True
            )
        else:
            split_cols = df_chunk[self.source_field].str.split(
                delimiter, n=self.max_splits if self.max_splits > 0 else -1, expand=True
            )

        # 设置列名
        if self.new_fields_config and len(self.new_fields_config) > 0:
            # 按照field_order排序
            sorted_config = sorted(self.new_fields_config, key=lambda x: x.get("field_order", 999))
            field_names = [cfg["field_name"] for cfg in sorted_config]

            # 确保有足够的列名
            if len(field_names) < len(split_cols.columns):
                # 添加默认列名
                for i in range(len(field_names), len(split_cols.columns)):
                    field_names.append(f"{self.source_field}_{i}")

            split_cols.columns = field_names[: len(split_cols.columns)]
        else:
            # 自动生成列名
            split_cols.columns = [f"{self.source_field}_{i}" for i in range(len(split_cols.columns))]

        # 填充默认值
        if self.default_value:
            split_cols = split_cols.fillna(self.default_value)

        # 合并数据
        df_result = pd.concat([df_chunk, split_cols], axis=1)

        # 删除源字段
        if self.drop_source_field:
            df_result = df_result.drop(columns=[self.source_field])

        return df_result

    def split_to_columns(self) -> list[Data]:
        """执行单列拆分为多列操作"""
        try:
            self.status = i18n.t("components.manipulations.field_split_to_columns.status.splitting")
            logger.info(f"[FieldSplitToColumns] Starting split operation on field: {self.source_field}")

            if not self.data_input:
                raise ValueError(i18n.t("components.manipulations.field_split_to_columns.errors.no_input_data"))

            # 转换为DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])
            total_rows = len(df)
            logger.info(f"[FieldSplitToColumns] Processing {total_rows} rows")

            # 对于大数据量，分块处理
            if total_rows > self.chunk_size:
                logger.info(f"[FieldSplitToColumns] Large dataset detected, processing in chunks of {self.chunk_size}")
                chunks = []
                for start in range(0, total_rows, self.chunk_size):
                    end = min(start + self.chunk_size, total_rows)
                    df_chunk = df.iloc[start:end]
                    processed_chunk = self._process_chunk(df_chunk)
                    chunks.append(processed_chunk)
                    logger.debug(f"[FieldSplitToColumns] Processed chunk {start}-{end}")

                df_result = pd.concat(chunks, ignore_index=True)
            else:
                df_result = self._process_chunk(df)

            # 转换回Data对象列表
            result = [Data(data=row.to_dict()) for _, row in df_result.iterrows()]

            self.status = i18n.t(
                "components.manipulations.field_split_to_columns.status.success",
                count=len(result),
                fields=len(df_result.columns),
            )
            logger.info(f"[FieldSplitToColumns] Split completed: {len(df_result.columns)} fields")

            return result

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_split_to_columns.errors.split_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[FieldSplitToColumns] Split failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def preview_result(self) -> Data:
        """预览拆分结果"""
        try:
            if not self.data_input:
                return Data(
                    data={"message": i18n.t("components.manipulations.field_split_to_columns.errors.no_input_data")}
                )

            # 取前10条数据进行预览
            preview_data = self.data_input[:10]
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in preview_data])

            if self.source_field not in df.columns:
                return Data(
                    data={
                        "error": i18n.t(
                            "components.manipulations.field_split_to_columns.errors.field_not_found",
                            field=self.source_field,
                        )
                    }
                )

            # 执行拆分预览
            df_preview = self._process_chunk(df.head(5))

            # 获取新增字段
            original_columns = set(df.columns)
            result_columns = set(df_preview.columns)
            new_columns = list(result_columns - original_columns)
            if self.drop_source_field:
                removed_columns = [self.source_field]
            else:
                removed_columns = []

            return Data(
                data={
                    "original_fields": list(df.columns),
                    "result_fields": list(df_preview.columns),
                    "new_fields": new_columns,
                    "removed_fields": removed_columns,
                    "source_field": self.source_field,
                    "delimiter": str(self._get_delimiter()),
                    "is_regex": self.is_regex,
                    "sample_data": df_preview.head(10).to_dict("records"),
                }
            )

        except Exception as e:
            logger.error(f"[FieldSplitToColumns] Preview failed: {e}")
            return Data(data={"error": str(e)})

    def get_statistics(self) -> Data:
        """获取拆分统计信息"""
        try:
            if not self.data_input:
                return Data(
                    data={"message": i18n.t("components.manipulations.field_split_to_columns.errors.no_input_data")}
                )

            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            stats = {
                "total_rows": len(df),
                "original_fields": len(df.columns),
                "source_field": self.source_field,
                "delimiter": self._get_delimiter(),
                "is_regex": self.is_regex,
            }

            if self.source_field in df.columns:
                # 获取分隔符
                delimiter_str = self._get_delimiter()
                delimiter = re.compile(delimiter_str) if self.is_regex else delimiter_str

                # 统计拆分情况
                if self.is_regex:
                    split_counts = df[self.source_field].str.split(delimiter).apply(len)
                else:
                    split_counts = df[self.source_field].str.split(delimiter).apply(len)

                stats.update(
                    {
                        "avg_splits": split_counts.mean(),
                        "max_splits": split_counts.max(),
                        "min_splits": split_counts.min(),
                        "estimated_new_fields": split_counts.max(),
                    }
                )

            return Data(data=stats)

        except Exception as e:
            logger.error(f"[FieldSplitToColumns] Statistics failed: {e}")
            return Data(data={"error": str(e)})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the split result.

        Returns:
            Data: A Data object containing fields metadata
        """
        try:
            logger.info("[FieldSplitToColumns] get_fields_schema called")

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

            logger.info(f"[FieldSplitToColumns] Returning schema with {len(fields)} fields")
            return Data(data={"fields": fields, "field_names": field_names})

        except Exception as e:
            logger.error(f"[FieldSplitToColumns] Failed to get fields schema: {e}")
            return Data(data={"fields": [], "field_names": []})
