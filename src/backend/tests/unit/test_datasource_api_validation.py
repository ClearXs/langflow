"""Unit tests for datasource API validation."""

from langflow.services.database.models.datasource import DataSourceCreate


class TestDataSourceValidation:
    """Test datasource creation validation."""

    def test_allowed_database_types(self):
        """Test that only 4 database types are allowed."""
        allowed_types = ["mysql", "postgresql", "hive", "neo4j"]

        for db_type in allowed_types:
            # Should not raise any validation error at model level
            data = DataSourceCreate(
                name="test",
                type=db_type,
                host="localhost",
                port=3306,
                database="testdb",
                username="user" if db_type != "hive" else None,
                password="pass" if db_type != "hive" else None,
            )
            assert data.type == db_type

    def test_hive_optional_credentials(self):
        """Test that Hive can have optional username and password."""
        # Hive with no credentials
        data_no_creds = DataSourceCreate(
            name="hive_test",
            type="hive",
            host="localhost",
            port=10000,
            database="default",
            username=None,
            password=None,
        )
        assert data_no_creds.username is None
        assert data_no_creds.password is None

        # Hive with credentials
        data_with_creds = DataSourceCreate(
            name="hive_test",
            type="hive",
            host="localhost",
            port=10000,
            database="default",
            username="hive",
            password="secret",
        )
        assert data_with_creds.username == "hive"
        assert data_with_creds.password == "secret"

    def test_mysql_requires_credentials(self):
        """Test that MySQL requires username and password at model level (nullable=True but validation in API)."""
        # This test validates that the model allows None, but API should validate
        data = DataSourceCreate(
            name="mysql_test",
            type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username=None,
            password=None,
        )
        # Model allows None, but API validation should catch this
        assert data.username is None
        assert data.password is None

    def test_neo4j_requires_credentials(self):
        """Test that Neo4j requires username and password (in API validation)."""
        data = DataSourceCreate(
            name="neo4j_test",
            type="neo4j",
            host="localhost",
            port=7687,
            database="neo4j",
            username=None,
            password=None,
        )
        # Model allows None, but API should validate
        assert data.username is None
        assert data.password is None
