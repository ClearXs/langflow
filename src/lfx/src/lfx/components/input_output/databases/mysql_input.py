"""MySQL Input Component - 从 MySQL 数据库表读取数据"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.sql_base import TRANSFORMATION_RULE_VALUES, BaseSQLInputComponent
from lfx.io import BoolInput, DropdownInput, IntInput, MultilineInput, Output, TableInput
from lfx.schema import Data


class MySQLInputComponent(BaseSQLInputComponent):
    """MySQL 输入组件 - 使用 SQL 查询从 MySQL 数据库读取数据"""

    display_name = i18n.t("components.input_output.databases.mysql_input.display_name")
    description = i18n.t("components.input_output.databases.mysql_input.description")
    icon = "MySQL"
    name = "MySQLInput"

    DATASOURCE_TYPE = "MySQL"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.mysql_input.datasource_selector.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.datasource_selector.info"),
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
        MultilineInput(
            name="sql_query",
            display_name=i18n.t("components.input_output.databases.mysql_input.sql_query.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.sql_query.info"),
            required=True,
            placeholder="SELECT * FROM your_table WHERE 1=1",
            advanced=False,
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.input_output.databases.mysql_input.field_mappings.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t(
                        "components.input_output.databases.mysql_input.field_mappings.source_field"
                    ),
                    "type": "str",
                    "disable_edit": True,
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.databases.mysql_input.field_mappings.data_type"),
                    "type": "str",
                    "disable_edit": True,
                    "formatter": "code",
                    "translate_value": False,
                },
                {
                    "name": "null_value",
                    "display_name": i18n.t("components.input_output.databases.mysql_input.field_mappings.null_value"),
                    "type": "str",
                    "description": i18n.t(
                        "components.input_output.databases.mysql_input.field_mappings.null_value_desc"
                    ),
                },
                {
                    "name": "transformation_rule",
                    "display_name": i18n.t(
                        "components.input_output.databases.mysql_input.field_mappings.transformation_rule"
                    ),
                    "type": "str",
                    "formatter": "text",
                    "options": TRANSFORMATION_RULE_VALUES,
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "analyze_sql",
                        "label": i18n.t(
                            "components.input_output.databases.mysql_input.field_mappings.analyze_sql_button"
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
            display_name=i18n.t("components.input_output.databases.mysql_input.preview_table.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.preview_table.info"),
            table_schema=[],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "block_edit": True,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "preview_data",
                        "label": i18n.t("components.input_output.databases.mysql_input.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        BoolInput(
            name="use_pagination",
            display_name=i18n.t("components.input_output.databases.mysql_input.use_pagination.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.use_pagination.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="page_size",
            display_name=i18n.t("components.input_output.databases.mysql_input.page_size.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.page_size.info"),
            value=1000,
            advanced=True,
        ),
        IntInput(
            name="max_records",
            display_name=i18n.t("components.input_output.databases.mysql_input.max_records.display_name"),
            info=i18n.t("components.input_output.databases.mysql_input.max_records.info"),
            value=10000,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.mysql_input.outputs.data.display_name"),
            method="load_data",
        ),
    ]

    def _build_connection_string(self) -> str:
        """构建 MySQL 连接字符串"""
        if not self.datasource_obj:
            raise ValueError("Datasource not selected")
        return datasource_utils.build_connection_string(self.datasource_obj)

    async def load_data(self) -> list[Data]:
        """主入口方法"""
        try:
            datasource_id = getattr(self, "datasource_selector", None)
            if not datasource_id:
                raise ValueError(i18n.t("components.input_output.databases.mysql_input.errors.no_datasource"))

            self.datasource_obj = self._get_datasource_by_id(datasource_id)
            if not self.datasource_obj:
                raise ValueError(
                    i18n.t(
                        "components.input_output.databases.mysql_input.errors.datasource_not_found", id=datasource_id
                    )
                )

            self.status = i18n.t("components.input_output.databases.mysql_input.status.reading")
            result = await self._read_data()

            row_count = len(result)
            self.status = i18n.t("components.input_output.databases.mysql_input.status.success", rows=row_count)

            return result

        except Exception as e:
            error_msg = i18n.t("components.input_output.databases.mysql_input.errors.read_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
