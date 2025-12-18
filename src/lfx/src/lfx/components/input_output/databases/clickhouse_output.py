"""ClickHouse Output Component - 写入数据到 ClickHouse 数据库表"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.sql_base import (
    UPDATE_OPTION_VALUE_MAPPING,
    WRITE_MODE_VALUE_MAPPING,
    BaseSQLOutputComponent,
    get_update_option_metadata,
    get_write_mode_metadata,
)
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, Output, TableInput
from lfx.schema import Data



class ClickHouseOutputComponent(BaseSQLOutputComponent):
    """ClickHouse 输出组件 - 写入数据到 ClickHouse 数据库表"""

    display_name = i18n.t("components.input_output.databases.clickhouse_output.display_name")
    description = i18n.t("components.input_output.databases.clickhouse_output.description")
    icon = "ClickHouse"
    name = "ClickHouseOutput"

    # 指定数据源类型
    DATASOURCE_TYPE = "ClickHouse"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.data_input.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.data_input.info"),
            required=True,
            is_list=True,
        ),
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.datasource_selector.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],
            real_time_refresh=True,
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        DropdownInput(
            name="table_name",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.table_name.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.table_name.info"),
            required=True,
            refresh_button=True,
            options=[],
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.field_mappings.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.source_field"
                    ),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "target_field",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.target_field"
                    ),
                    "type": "str",
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.data_type"
                    ),
                    "type": "str",
                    "disable_edit": True,
                    "formatter": "code",
                    "translate_value": False,
                },
                {
                    "name": "update_option",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.update_option"
                    ),
                    "type": "str",
                    "options": list(UPDATE_OPTION_VALUE_MAPPING.keys()),
                    "options_metadata": get_update_option_metadata(),
                    "formatter": "text",
                },
                {
                    "name": "is_key_field",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.is_key_field"
                    ),
                    "type": "bool",
                    "formatter": "boolean",
                    "description": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.is_key_field_desc"
                    ),
                },
                {
                    "name": "null_value",
                    "display_name": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.null_value"
                    ),
                    "type": "str",
                    "description": i18n.t(
                        "components.input_output.databases.clickhouse_output.field_mappings.null_value_desc"
                    ),
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "analyze_schema",
                        "label": i18n.t(
                            "components.input_output.databases.clickhouse_output.field_mappings.analyze_schema_button"
                        ),
                        "icon": "Search",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.preview_table.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.preview_table.info"),
            table_schema=[],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "preview_target_data",
                        "label": i18n.t("components.input_output.databases.clickhouse_output.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],,
            advanced=False,
        ),
        DropdownInput(
            name="write_mode",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.write_mode.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.write_mode.info"),
            options=list(WRITE_MODE_VALUE_MAPPING.keys()),  # ["append", "overwrite", "fail"]
            options_metadata=get_write_mode_metadata(),  # [{"value": "append", "label": "追加"}, ...]
            value="append",  # 使用内部值，前端通过 options_metadata 显示翻译
            advanced=False,
        ),
        BoolInput(
            name="clear_table_first",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.clear_table_first.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.clear_table_first.info"),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.batch_size.display_name"),
            info=i18n.t("components.input_output.databases.clickhouse_output.batch_size.info"),
            value=1000,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.clickhouse_output.outputs.data.display_name"),
            method="write_to_table",
        ),
    ]

    def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ):
        """动态更新配置"""
        # 1. 加载数据源列表（初始加载或刷新）
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            datasources = self._load_datasource_metadata()
            options = [ds["id"] for ds in datasources]
            options_metadata = [
                {
                    "value": ds["id"],
                    "label": ds["display_name"],
                    "id": ds["id"],
                    "name": ds["name"],
                    "type": ds["type"],
                    "source": ds["source"],
                    "display_name": ds["display_name"],
                    "raw_data": ds.get("raw_data"),
                }
                for ds in datasources
            ]
            build_config["datasource_selector"]["options"] = options
            build_config["datasource_selector"]["options_metadata"] = options_metadata

        # 2. 当数据源被选择或表名刷新时，加载表列表
        elif field_name == "datasource_selector" and field_value:
            self.datasource_obj = self._get_datasource_by_id(field_value)
            if self.datasource_obj:
                try:
                    tables = self._load_tables()
                    build_config["table_name"]["options"] = tables
                except Exception:
                    pass

        elif field_name == "table_name" and action == "refresh":
            datasource_id = build_config.get("datasource_selector", {}).get("value")
            if datasource_id:
                self.datasource_obj = self._get_datasource_by_id(datasource_id)
                if self.datasource_obj:
                    try:
                        tables = self._load_tables()
                        build_config["table_name"]["options"] = tables
                    except Exception:
                        pass

        # 3. 处理 analyze_schema 动作按钮
        elif field_name == "field_mappings" and action == "analyze_schema":
            import logging

            logger = logging.getLogger(__name__)
            logger.info("[ClickHouseOutput] Schema analysis triggered")

            try:
                # 获取 graph 数据和当前节点 ID
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # 如果 build_config 中没有，尝试从 self.graph 获取
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[ClickHouseOutput] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[ClickHouseOutput] No graph data available for schema analysis")
                    self.status = i18n.t("components.input_output.databases.clickhouse_output.errors.no_graph_data")
                    return build_config

                # 使用静态字段提取（不执行上游组件）
                self.status = i18n.t("components.input_output.databases.clickhouse_output.status.analyzing_schema")
                logger.info("[ClickHouseOutput] Using static field extraction from upstream component")

                try:
                    from lfx.components.helpers.field_extraction import extract_fields_from_node_template
                    from lfx.custom.graph_utils import find_upstream_node_id

                    # 查找连接到 data_input 的上游节点
                    upstream_node_id = find_upstream_node_id(graph_data, node_id, "data_input")
                    if not upstream_node_id:
                        logger.warning("[ClickHouseOutput] No upstream node found for field analysis")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_fields_found")
                        return build_config

                    # 在 graph data 中查找上游节点
                    upstream_node = None
                    for node in graph_data.get("nodes", []):
                        if node.get("id") == upstream_node_id:
                            upstream_node = node
                            break

                    if not upstream_node:
                        logger.warning(f"[ClickHouseOutput] Upstream node {upstream_node_id} not found in graph data")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_fields_found")
                        return build_config

                    # 提取字段名（与 FieldNameMapping 使用相同逻辑）
                    field_names = extract_fields_from_node_template(
                        upstream_node, component_name="ClickHouseOutput", graph_data=graph_data
                    )

                    if not field_names:
                        logger.warning("[ClickHouseOutput] No fields extracted from upstream configuration")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_fields_found")
                        return build_config

                    logger.info(f"[ClickHouseOutput] Extracted {len(field_names)} fields from upstream: {field_names}")

                    # 转换字段信息为 field_mappings 格式
                    field_info = []
                    for field_item in field_names:
                        # 处理新的字典格式: {"name": "field1", "type": "string"}
                        if isinstance(field_item, dict):
                            field_name = field_item.get("name")
                            data_type = field_item.get("type", "string")
                        else:
                            # 向后兼容：如果是字符串
                            field_name = field_item
                            data_type = "string"

                        field_info.append(
                            {
                                "source_field": field_name,
                                "target_field": field_name,  # 默认使用相同名称
                                "data_type": data_type,  # 使用提取的类型
                                "update_option": "sync_update",  # 使用内部值（前端会通过 options_metadata 翻译）
                                "is_key_field": False,
                                "null_value": "",
                            }
                        )

                    build_config["field_mappings"]["value"] = field_info
                    logger.info(
                        f"[ClickHouseOutput] Static field analysis completed, generated {len(field_info)} field mappings"
                    )
                    self.status = i18n.t(
                        "components.input_output.databases.clickhouse_output.status.analysis_success", count=len(field_info)
                    )

                except Exception as e:
                    logger.error(f"[ClickHouseOutput] Static field extraction failed: {e}")
                    import traceback

                    logger.error(f"[ClickHouseOutput] Traceback: {traceback.format_exc()}")
                    self.status = i18n.t(
                        "components.input_output.databases.clickhouse_output.errors.analysis_failed", error=str(e)
                    )

            except ValueError as e:
                import logging

                logger = logging.getLogger(__name__)
                error_msg = str(e)
                logger.warning(f"[ClickHouseOutput] Schema analysis warning: {error_msg}")
                self.status = i18n.t(
                    "components.input_output.databases.clickhouse_output.errors.analysis_failed", error=error_msg
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                error_msg = str(e)
                logger.error(f"[ClickHouseOutput] Unexpected error during schema analysis: {error_msg}")
                import traceback

                logger.error(f"[ClickHouseOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t(
                    "components.input_output.databases.clickhouse_output.errors.analysis_failed", error=error_msg
                )
        # 4. 处理数据预览 preview_target_data 动作按钮
        elif field_name == "preview_table" and action == "preview_target_data":
            import logging
            import pandas as pd

            logger = logging.getLogger(__name__)
            logger.info("[ClickHouseOutput] Output data preview triggered by action button")

            try:
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data:
                    logger.warning("[ClickHouseOutput] No graph data available for preview")
                    self.status = i18n.t("components.input_output.databases.clickhouse_output.errors.no_graph_data")
                    return build_config

                self.status = i18n.t("components.input_output.databases.clickhouse_output.status.previewing_data")
                logger.info("[ClickHouseOutput] Generating preview data from upstream component")

                try:
                    from lfx.components.helpers.field_extraction import extract_fields_from_node_template
                    from lfx.custom.graph_utils import find_upstream_node_id

                    upstream_node_id = find_upstream_node_id(graph_data, node_id, "data_input")
                    if not upstream_node_id:
                        logger.warning("[ClickHouseOutput] No upstream node found for data preview")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_data_to_preview")
                        return build_config

                    upstream_node = None
                    for node in graph_data.get("nodes", []):
                        if node.get("id") == upstream_node_id:
                            upstream_node = node
                            break

                    if not upstream_node:
                        logger.warning(f"[ClickHouseOutput] Upstream node {upstream_node_id} not found in graph data")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_data_to_preview")
                        return build_config

                    field_names = extract_fields_from_node_template(
                        upstream_node, component_name="ClickHouseOutput", graph_data=graph_data
                    )

                    if not field_names:
                        logger.warning("[ClickHouseOutput] No fields found for preview generation")
                        self.status = i18n.t("components.input_output.databases.clickhouse_output.status.no_fields_found")
                        return build_config

                    # 生成示例数据
                    sample_data = {}
                    for field_item in field_names:
                        if isinstance(field_item, dict):
                            field_name = field_item.get("name")
                        else:
                            field_name = field_item

                        field_lower = field_name.lower()
                        if "id" in field_lower:
                            sample_data[field_name] = f"sample_{hash(field_name) % 1000:03d}"
                        elif "name" in field_lower:
                            sample_data[field_name] = f"Sample {field_name.title()}"
                        elif "email" in field_lower:
                            sample_data[field_name] = f"sample_{field_name}@example.com"
                        elif "phone" in field_lower:
                            sample_data[field_name] = "13800138000"
                        elif "date" in field_lower or "time" in field_lower:
                            sample_data[field_name] = "2024-01-01 12:00:00"
                        elif "amount" in field_lower or "price" in field_lower:
                            sample_data[field_name] = f"{(hash(field_name) % 10000) / 100:.2f}"
                        elif "count" in field_lower or "num" in field_lower:
                            sample_data[field_name] = hash(field_name) % 100
                        else:
                            sample_data[field_name] = f"Sample {field_name}"

                    df = pd.DataFrame([sample_data])
                    table_schema = [
                        {"name": str(col), "display_name": str(col), "type": "str", "disable_edit": True}
                        for col in df.columns
                    ]
                    preview_data = df.fillna("").to_dict("records")

                    build_config["preview_table"]["table_schema"] = table_schema
                    build_config["preview_table"]["value"] = preview_data

                    logger.info(f"[ClickHouseOutput] Preview completed, showing {len(preview_data)} rows")
                    self.status = i18n.t(
                        "components.input_output.databases.clickhouse_output.status.preview_success", count=len(preview_data)
                    )

                except Exception as e:
                    error_msg = f"{type(e).__name__}: {e!s}"
                    logger.error(f"[ClickHouseOutput] Preview generation failed: {error_msg}")
                    import traceback

                    logger.error(f"[ClickHouseOutput] Traceback: {traceback.format_exc()}")
                    self.status = i18n.t(
                        "components.input_output.databases.clickhouse_output.errors.preview_failed", error=error_msg
                    )

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                logger.error(f"[ClickHouseOutput] Unexpected error during preview: {error_msg}")
                import traceback

                logger.error(f"[ClickHouseOutput] Traceback: {traceback.format_exc()}")
                self.status = i18n.t(
                    "components.input_output.databases.clickhouse_output.errors.preview_failed", error=error_msg
                )



        return build_config

    def _build_connection_string(self) -> str:
        """构建 ClickHouse 连接字符串"""
        if not self.datasource_obj:
            raise ValueError("Datasource not selected")

        # 从数据源对象构建连接字符串
        conn_str = datasource_utils.build_connection_string(self.datasource_obj)
        return conn_str

    async def write_to_table(self) -> list[Data]:
        """主入口方法 - 写入数据到表"""
        try:
            # 获取选中的数据源
            datasource_id = getattr(self, "datasource_selector", None)
            if not datasource_id:
                raise ValueError(i18n.t("components.input_output.databases.clickhouse_output.errors.no_datasource"))

            # 加载数据源对象
            self.datasource_obj = self._get_datasource_by_id(datasource_id)
            if not self.datasource_obj:
                raise ValueError(
                    i18n.t(
                        "components.input_output.databases.clickhouse_output.errors.datasource_not_found",
                        id=datasource_id,
                    )
                )

            # 更新状态
            self.status = i18n.t("components.input_output.databases.clickhouse_output.status.writing")

            # 如果需要先清空表
            if getattr(self, "clear_table_first", False):
                table_name = getattr(self, "table_name", "")
                if table_name:
                    self._clear_table(table_name)

            # 写入数据（使用基类的方法）
            result = await self._write_data(self.data_input)

            # 更新状态 - metadata 现在是 data 字典的一部分
            row_count = result.data.get("metadata", {}).get("rows_written", 0)
            self.status = i18n.t("components.input_output.databases.clickhouse_output.status.success", rows=row_count)

            return [result]

        except Exception as e:
            error_msg = i18n.t("components.input_output.databases.clickhouse_output.errors.write_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
