"""MongoDB Input Component - 从 MongoDB 数据库集合读取数据"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.nosql_base import BaseNoSQLInputComponent
from lfx.io import DropdownInput, MultilineInput, Output
from lfx.schema import Data


class MongoDBInputComponent(BaseNoSQLInputComponent):
    display_name = i18n.t("components.input_output.databases.mongodb_input.display_name")
    description = i18n.t("components.input_output.databases.mongodb_input.description")
    icon = "MongoDB"
    name = "MongoDBInput"
    DATASOURCE_TYPE = "MongoDB"

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.mongodb_input.datasource_selector.display_name"),
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
            name="collection_name",
            display_name=i18n.t("components.input_output.databases.mongodb_input.collection_name.display_name"),
            required=True,
            refresh_button=True,
            options=[],
        ),
        MultilineInput(
            name="query",
            display_name=i18n.t("components.input_output.databases.mongodb_input.query.display_name"),
            value="{}",
            placeholder='{"field": "value"}',
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.mongodb_input.outputs.data.display_name"),
            method="load_data",
        )
    ]

    def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ):
        """动态更新配置 - 加载数据源列表和集合列表"""
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

        # 2. 当数据源选中或collection_name刷新时，加载集合列表
        elif field_name == "datasource_selector" and field_value:
            # 数据源被选中，加载集合列表
            try:
                datasource_id = field_value
                self.datasource_obj = self._get_datasource_by_id(datasource_id)
                if self.datasource_obj:
                    collections = self._load_tables()
                    build_config["collection_name"]["options"] = collections
            except Exception:
                build_config["collection_name"]["options"] = []

        elif field_name == "collection_name" and action == "refresh":
            # 集合列表刷新按钮被点击
            try:
                datasource_id = build_config.get("datasource_selector", {}).get("value")
                if datasource_id:
                    self.datasource_obj = self._get_datasource_by_id(datasource_id)
                    if self.datasource_obj:
                        collections = self._load_tables()
                        build_config["collection_name"]["options"] = collections
            except Exception:
                build_config["collection_name"]["options"] = []

        return build_config

    def _build_connection_string(self) -> str:
        if not self.datasource_obj:
            raise ValueError("Datasource not selected")
        return datasource_utils.build_connection_string(self.datasource_obj)

    def _load_tables(self) -> list[str]:
        from pymongo import MongoClient

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        client = MongoClient(self._build_connection_string())
        db = client[params["database"]]
        return db.list_collection_names()

    async def _read_data(self) -> Data:
        import json

        import pandas as pd
        from pymongo import MongoClient

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        client = MongoClient(self._build_connection_string())
        db = client[params["database"]]
        collection = db[self.collection_name]
        query = json.loads(self.query) if self.query else {}
        cursor = collection.find(query)
        data = list(cursor)
        df = pd.DataFrame(data)
        return Data(data=df)

    async def load_data(self) -> list[Data]:
        datasource_id = getattr(self, "datasource_selector", None)
        self.datasource_obj = self._get_datasource_by_id(datasource_id)
        self.status = i18n.t("components.input_output.databases.mongodb_input.status.reading")
        result = await self._read_data()
        self.status = i18n.t("components.input_output.databases.mongodb_input.status.success", rows=len(result.data))
        return [result]
