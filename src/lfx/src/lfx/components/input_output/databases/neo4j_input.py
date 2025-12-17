"""Neo4j Input Component - 从 Neo4j 图数据库读取数据"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.nosql_base import BaseNoSQLInputComponent
from lfx.io import DropdownInput, MultilineInput, Output
from lfx.schema import Data


class Neo4jInputComponent(BaseNoSQLInputComponent):
    display_name = i18n.t("components.input_output.databases.neo4j_input.display_name")
    description = i18n.t("components.input_output.databases.neo4j_input.description")
    icon = "Neo4j"
    name = "Neo4jInput"
    DATASOURCE_TYPE = "Neo4j"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.neo4j_input.datasource_selector.display_name"),
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
            name="cypher_query",
            display_name=i18n.t("components.input_output.databases.neo4j_input.cypher_query.display_name"),
            required=True,
            placeholder="MATCH (n) RETURN n LIMIT 100",
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.neo4j_input.outputs.data.display_name"),
            method="load_data",
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

    async def _read_data(self) -> Data:
        import pandas as pd
        from neo4j import GraphDatabase

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        driver = GraphDatabase.driver(self._build_connection_string(), auth=(params["username"], params["password"]))
        with driver.session() as session:
            result = session.run(self.cypher_query)
            records = [record.data() for record in result]
            df = pd.DataFrame(records)
            return Data(data=df)

    async def load_data(self) -> list[Data]:
        datasource_id = getattr(self, "datasource_selector", None)
        self.datasource_obj = self._get_datasource_by_id(datasource_id)
        self.status = i18n.t("components.input_output.databases.neo4j_input.status.reading")
        result = await self._read_data()
        self.status = i18n.t("components.input_output.databases.neo4j_input.status.success", rows=len(result.data))
        return [result]
