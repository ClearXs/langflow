import i18n
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from lfx.custom.custom_component.component import Component
from lfx.io import (
    Output,
    StrInput,
)


class SQLDatabaseComponent(Component):
    display_name = i18n.t(
        'components.langchain_utilities.sql_database.display_name')
    description = i18n.t(
        'components.langchain_utilities.sql_database.description')
    name = "SQLDatabase"
    icon = "LangChain"

    inputs = [
        StrInput(
            name="uri",
            display_name=i18n.t(
                'components.langchain_utilities.sql_database.uri.display_name'),
            info=i18n.t(
                'components.langchain_utilities.sql_database.uri.info'),
            required=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.sql_database.outputs.sql_database.display_name'),
            name="SQLDatabase",
            method="build_sqldatabase"
        ),
    ]

    def clean_up_uri(self, uri: str) -> str:
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://")
        return uri.strip()

    def build_sqldatabase(self) -> SQLDatabase:
        uri = self.clean_up_uri(self.uri)
        # Create an engine using SQLAlchemy with StaticPool
        engine = create_engine(uri, poolclass=StaticPool)
        return SQLDatabase(engine)
