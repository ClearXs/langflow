"""Neo4j Output Component - 写入数据到 Neo4j 图数据库"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.nosql_base import BaseNoSQLOutputComponent
from lfx.io import DataInput, DropdownInput, Output
from lfx.schema import Data


class Neo4jOutputComponent(BaseNoSQLOutputComponent):
    display_name = i18n.t("components.input_output.databases.neo4j_output.display_name")
    description = i18n.t("components.input_output.databases.neo4j_output.description")
    icon = "Neo4j"
    name = "Neo4jOutput"
    DATASOURCE_TYPE = "Neo4j"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.databases.neo4j_output.data_input.display_name"),
            required=True,
            is_list=True,
        ),
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.neo4j_output.datasource_selector.display_name"),
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
            name="label",
            display_name=i18n.t("components.input_output.databases.neo4j_output.label.display_name"),
            required=False,
            options=[],
        ),
        DropdownInput(
            name="write_mode",
            display_name=i18n.t("components.input_output.databases.neo4j_output.write_mode.display_name"),
            options=["batch_insert", "append"],
            value="batch_insert",
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.neo4j_output.outputs.data.display_name"),
            method="write_to_graph",
        )
    ]

    def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ):
        """动态更新配置 - 加载数据源列表"""
        # 加载数据源列表（初始加载或刷新）
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

        return build_config

    def _build_connection_string(self) -> str:
        if not self.datasource_obj:
            raise ValueError("Datasource not selected")
        return datasource_utils.build_connection_string(self.datasource_obj)

    def _load_tables(self) -> list[str]:
        from neo4j import GraphDatabase

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        driver = GraphDatabase.driver(self._build_connection_string(), auth=(params["username"], params["password"]))
        with driver.session() as session:
            result = session.run("CALL db.labels()")
            return [record[0] for record in result]

    async def _write_data(self, data: Data) -> Data:
        from neo4j import GraphDatabase

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        driver = GraphDatabase.driver(self._build_connection_string(), auth=(params["username"], params["password"]))
        df = data.data
        label = self.label if self.label else "Node"
        with driver.session() as session:
            for _, row in df.iterrows():
                props = row.to_dict()
                session.run(f"CREATE (n:{label} $props)", props=props)
        return Data(data=df, metadata={"label": label, "rows_written": len(df)})

    async def write_to_graph(self) -> list[Data]:
        datasource_id = getattr(self, "datasource_selector", None)
        self.datasource_obj = self._get_datasource_by_id(datasource_id)
        self.status = i18n.t("components.input_output.databases.neo4j_output.status.writing")
        result = await self._write_data(self.data_input)
        self.status = i18n.t(
            "components.input_output.databases.neo4j_output.status.success", rows=result.metadata.get("rows_written", 0)
        )
        return [result]
