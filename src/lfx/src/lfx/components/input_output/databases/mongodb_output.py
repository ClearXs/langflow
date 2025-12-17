"""MongoDB Output Component - 写入数据到 MongoDB 数据库集合"""

import i18n

from lfx.base.io import datasource_utils
from lfx.base.io.nosql_base import BaseNoSQLOutputComponent
from lfx.io import DataInput, DropdownInput, Output
from lfx.schema import Data


class MongoDBOutputComponent(BaseNoSQLOutputComponent):
    display_name = i18n.t("components.input_output.databases.mongodb_output.display_name")
    description = i18n.t("components.input_output.databases.mongodb_output.description")
    icon = "MongoDB"
    name = "MongoDBOutput"
    DATASOURCE_TYPE = "MongoDB"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.databases.mongodb_output.data_input.display_name"),
            required=True,
            is_list=True,
        ),
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.databases.mongodb_output.datasource_selector.display_name"),
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
            display_name=i18n.t("components.input_output.databases.mongodb_output.collection_name.display_name"),
            required=True,
            refresh_button=True,
            options=[],
        ),
        DropdownInput(
            name="write_mode",
            display_name=i18n.t("components.input_output.databases.mongodb_output.write_mode.display_name"),
            options=["insert", "replace"],
            value="insert",
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.databases.mongodb_output.outputs.data.display_name"),
            method="write_to_collection",
        )
    ]

    def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ):
        """动态更新配置 - 加载数据源列表和集合列表"""
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

        # 当数据源被选择时，加载集合列表
        elif field_name == "datasource_selector" and field_value:
            self.datasource_obj = self._get_datasource_by_id(field_value)
            if self.datasource_obj:
                try:
                    collections = self._load_tables()
                    build_config["collection_name"]["options"] = collections
                except Exception:
                    pass

        # 当刷新集合列表时
        elif field_name == "collection_name" and action == "refresh":
            datasource_id = build_config.get("datasource_selector", {}).get("value")
            if datasource_id:
                self.datasource_obj = self._get_datasource_by_id(datasource_id)
                if self.datasource_obj:
                    try:
                        collections = self._load_tables()
                        build_config["collection_name"]["options"] = collections
                    except Exception:
                        pass

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

    async def _write_data(self, data: Data) -> Data:
        from pymongo import MongoClient

        params = datasource_utils.extract_connection_params(self.datasource_obj)
        client = MongoClient(self._build_connection_string())
        db = client[params["database"]]
        collection = db[self.collection_name]
        df = data.data
        records = df.to_dict("records")
        if self.write_mode == "replace":
            collection.delete_many({})
        result = collection.insert_many(records)
        return Data(
            data=df, metadata={"collection_name": self.collection_name, "rows_written": len(result.inserted_ids)}
        )

    async def write_to_collection(self) -> list[Data]:
        datasource_id = getattr(self, "datasource_selector", None)
        self.datasource_obj = self._get_datasource_by_id(datasource_id)
        self.status = i18n.t("components.input_output.databases.mongodb_output.status.writing")
        result = await self._write_data(self.data_input)
        self.status = i18n.t(
            "components.input_output.databases.mongodb_output.status.success",
            rows=result.metadata.get("rows_written", 0),
        )
        return [result]
