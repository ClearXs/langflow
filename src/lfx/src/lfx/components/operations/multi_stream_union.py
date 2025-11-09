from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, MessageTextInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLMultiStreamUnionComponent(Component):
    display_name = i18n.t("components.operations.multi_stream_union.display_name")
    description = i18n.t("components.operations.multi_stream_union.description")
    icon = "layers"
    name = "ETLMultiStreamUnion"

    inputs = [
        DataInput(
            name="stream_1",
            display_name=i18n.t("components.operations.multi_stream_union.stream_1.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_1.info"),
            is_list=True,
            required=True,
        ),
        DataInput(
            name="stream_2",
            display_name=i18n.t("components.operations.multi_stream_union.stream_2.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_2.info"),
            is_list=True,
        ),
        DataInput(
            name="stream_3",
            display_name=i18n.t("components.operations.multi_stream_union.stream_3.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_3.info"),
            is_list=True,
            advanced=True,
        ),
        DataInput(
            name="stream_4",
            display_name=i18n.t("components.operations.multi_stream_union.stream_4.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_4.info"),
            is_list=True,
            advanced=True,
        ),
        DataInput(
            name="stream_5",
            display_name=i18n.t("components.operations.multi_stream_union.stream_5.display_name"),
            info=i18n.t("components.operations.multi_stream_union.stream_5.info"),
            is_list=True,
            advanced=True,
        ),
        TableInput(
            name="union_field_config",
            display_name=i18n.t("components.operations.multi_stream_union.union_field_config.display_name"),
            info=i18n.t("components.operations.multi_stream_union.union_field_config.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.operations.multi_stream_union.union_field_config.field_name"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "source_stream",
                    "display_name": i18n.t("components.operations.multi_stream_union.union_field_config.source_stream"),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "keep_field",
                    "display_name": i18n.t("components.operations.multi_stream_union.union_field_config.keep_field"),
                    "type": "bool",
                    "formatter": "boolean",
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t(
                            "components.operations.multi_stream_union.union_field_config.load_fields_button"
                        ),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        BoolInput(
            name="drop_duplicates",
            display_name=i18n.t("components.operations.multi_stream_union.drop_duplicates.display_name"),
            info=i18n.t("components.operations.multi_stream_union.drop_duplicates.info"),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="align_schemas",
            display_name=i18n.t("components.operations.multi_stream_union.align_schemas.display_name"),
            info=i18n.t("components.operations.multi_stream_union.align_schemas.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="source_column",
            display_name=i18n.t("components.operations.multi_stream_union.source_column.display_name"),
            info=i18n.t("components.operations.multi_stream_union.source_column.info"),
            value="_source_stream",
            advanced=True,
        ),
        BoolInput(
            name="include_source_info",
            display_name=i18n.t("components.operations.multi_stream_union.include_source_info.display_name"),
            info=i18n.t("components.operations.multi_stream_union.include_source_info.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.operations.multi_stream_union.outputs.data"),
            method="union_streams",
        ),
        Output(
            name="union_stats",
            display_name=i18n.t("components.operations.multi_stream_union.outputs.union_stats"),
            method="get_union_stats",
        ),
        Output(
            name="field_preview",
            display_name=i18n.t("components.operations.multi_stream_union.outputs.field_preview"),
            method="preview_fields",
        ),
    ]

    async def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """动态更新field_config的字段选项"""
        logger.info(f"[MultiStreamUnion] update_build_config called - field_name: {field_name}, action: {action}")

        # 当点击"加载字段列表"按钮时
        if field_name == "union_field_config" and action == "load_fields":
            try:
                # Try to get graph_data and node_id from build_config (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        # PlaceholderGraph - no data available
                        logger.warning("[MultiStreamUnion] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[MultiStreamUnion] No graph data available")
                    self.status = i18n.t("components.operations.multi_stream_union.errors.no_graph_data")
                    return build_config

                # 从所有上游数据流提取字段列表
                all_fields = []
                field_seen = {}  # 用于去重和记录来源

                # 尝试从每个输入流获取上游数据
                for i in range(1, 6):
                    input_name = f"stream_{i}"
                    fields = []

                    # Primary strategy: Try to execute upstream node to get actual data
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name=input_name, graph_data=graph_data, sample_size=1, vertex_id=node_id
                        )

                        if upstream_data:
                            # Extract field names from upstream data
                            fields = self._extract_field_names(upstream_data)
                            logger.debug(f"[MultiStreamUnion] {input_name}: found {len(fields)} fields from upstream data")

                    except ValueError as e:
                        # Fallback strategy: Extract from upstream node configuration
                        logger.debug(f"[MultiStreamUnion] {input_name}: upstream execution failed - {e}")
                        logger.debug(f"[MultiStreamUnion] {input_name}: trying static analysis...")

                        try:
                            from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                            fields = find_and_extract_upstream_fields(
                                graph_data, node_id, input_name, "MultiStreamUnion"
                            )

                            if fields:
                                logger.debug(
                                    f"[MultiStreamUnion] {input_name}: found {len(fields)} fields from static config"
                                )
                            else:
                                logger.debug(f"[MultiStreamUnion] {input_name}: no fields found in static config")

                        except Exception:  # noqa: BLE001
                            logger.exception(f"[MultiStreamUnion] {input_name}: static analysis also failed")

                    except Exception as e:
                        # Unexpected error - log but continue with other streams
                        logger.warning(f"[MultiStreamUnion] {input_name}: unexpected error - {e}")

                    # Collect fields found by either strategy
                    if fields:
                        for field_dict in fields:
                            field_name = field_dict["name"]
                            if field_name not in field_seen:
                                field_seen[field_name] = []
                            field_seen[field_name].append(input_name)

                if not field_seen:
                    logger.warning("[MultiStreamUnion] No fields found from any upstream node")
                    self.status = i18n.t("components.operations.multi_stream_union.warnings.field_load_failed")
                    return build_config

                # 构建字段配置列表
                for field_name_str, sources in field_seen.items():
                    all_fields.append(
                        {
                            "field_name": field_name_str,
                            "source_stream": ", ".join(sources),
                            "keep_field": True,  # 默认保留所有字段
                        }
                    )

                # 更新配置
                build_config["union_field_config"]["value"] = all_fields

                self.status = i18n.t(
                    "components.operations.multi_stream_union.status.fields_loaded", count=len(all_fields)
                )
                logger.info(f"[MultiStreamUnion] Loaded {len(all_fields)} fields from upstream nodes")

            except Exception as e:
                logger.error(f"[MultiStreamUnion] Failed to load fields: {e}", exc_info=True)
                self.status = i18n.t("components.operations.multi_stream_union.status.load_fields_failed", error=str(e))

        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """从数据流中提取字段名列表"""
        if not data_list or len(data_list) == 0:
            return []

        # 取第一条数据获取字段
        first_record = data_list[0]
        if hasattr(first_record, "data") and isinstance(first_record.data, dict):
            return list(first_record.data.keys())
        if isinstance(first_record, dict):
            return list(first_record.keys())

        return []

    def union_streams(self) -> list[Data]:
        """Merge multiple data streams with schema alignment and field filtering."""
        try:
            self.status = i18n.t("components.operations.multi_stream_union.status.merging")
            logger.info("[MultiStreamUnion] Starting union operation")

            # Collect all streams
            all_streams = []
            stream_names = []

            for i in range(1, 6):
                stream = getattr(self, f"stream_{i}", None)
                if stream:
                    all_streams.append(stream)
                    stream_names.append(f"stream_{i}")

            if not all_streams:
                raise ValueError(i18n.t("components.operations.multi_stream_union.errors.no_streams"))

            logger.debug(f"[MultiStreamUnion] Found {len(all_streams)} streams to merge")

            # Convert to DataFrames
            dataframes = []
            for idx, stream in enumerate(all_streams):
                df = self._convert_to_dataframe(stream)

                if self.include_source_info:
                    df[self.source_column] = stream_names[idx]

                dataframes.append(df)
                logger.debug(
                    f"[MultiStreamUnion] Stream {stream_names[idx]}: {len(df)} records, {len(df.columns)} fields"
                )

            # Merge all DataFrames (Union ALL)
            if self.align_schemas:
                merged_df = pd.concat(dataframes, ignore_index=True, sort=False)
                merged_df = merged_df.fillna("")
            else:
                merged_df = pd.concat(dataframes, ignore_index=True)

            logger.debug(f"[MultiStreamUnion] After merge: {len(merged_df)} records, {len(merged_df.columns)} fields")

            # Apply field filtering (if union_field_config is configured)
            if self.union_field_config:
                keep_fields = [f["field_name"] for f in self.union_field_config if f.get("keep_field", True)]
                if keep_fields:
                    # Only keep fields that actually exist in the merged dataframe
                    available_fields = [f for f in keep_fields if f in merged_df.columns]
                    if available_fields:
                        merged_df = merged_df[available_fields]
                        logger.debug(f"[MultiStreamUnion] Field filtering applied, kept {len(available_fields)} fields")

            # Drop duplicates if requested
            if self.drop_duplicates:
                original_count = len(merged_df)
                merged_df = merged_df.drop_duplicates()
                logger.debug(f"[MultiStreamUnion] Removed {original_count - len(merged_df)} duplicate records")

            # Convert back to Data objects
            result_data = []
            for _, row in merged_df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            self.status = i18n.t("components.operations.multi_stream_union.status.success", records=len(result_data))
            logger.info(f"[MultiStreamUnion] Union completed: {len(result_data)} records")
            return result_data

        except Exception as e:
            error_msg = i18n.t("components.operations.multi_stream_union.errors.union_failed", error=str(e))
            self.status = error_msg
            logger.error(f"[MultiStreamUnion] Union failed: {e}", exc_info=True)
            raise ValueError(error_msg) from e

    def _convert_to_dataframe(self, data_list: list[Data]) -> pd.DataFrame:
        """Convert list of Data objects to pandas DataFrame."""
        records = []
        for data_obj in data_list:
            if hasattr(data_obj, "data") and isinstance(data_obj.data, dict):
                records.append(data_obj.data)
            elif isinstance(data_obj, dict):
                records.append(data_obj)

        return pd.DataFrame(records)

    def get_union_stats(self) -> Data:
        """Get statistics about the union operation."""
        merged = self.union_streams()

        stream_counts = []
        for i in range(1, 6):
            stream = getattr(self, f"stream_{i}", None)
            if stream:
                stream_counts.append(len(stream))

        stats = {
            "total_streams": len(stream_counts),
            "stream_counts": stream_counts,
            "merged_count": len(merged),
            "drop_duplicates": self.drop_duplicates,
            "align_schemas": self.align_schemas,
        }

        return Data(data=stats)

    def preview_fields(self) -> Data:
        """预览合并后的字段信息"""
        try:
            all_streams = []
            for i in range(1, 6):
                stream = getattr(self, f"stream_{i}", None)
                if stream:
                    all_streams.append((f"stream_{i}", stream))

            if not all_streams:
                return Data(
                    data={
                        "fields": [],
                        "message": i18n.t("components.operations.multi_stream_union.errors.no_streams_for_preview"),
                    }
                )

            # Collect all fields with their source information
            field_info = {}
            for stream_name, stream in all_streams:
                fields = self._extract_field_names(stream)
                for field in fields:
                    if field not in field_info:
                        field_info[field] = {"field_name": field, "sources": [], "appears_in_streams": 0}
                    field_info[field]["sources"].append(stream_name)
                    field_info[field]["appears_in_streams"] += 1

            fields_list = list(field_info.values())

            return Data(
                data={"total_fields": len(fields_list), "total_streams": len(all_streams), "fields": fields_list}
            )

        except Exception as e:
            logger.error(f"[MultiStreamUnion] Field preview failed: {e}")
            return Data(data={"error": str(e)})
