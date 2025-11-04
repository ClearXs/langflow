"""Unit tests for datasource connection string building."""

import pytest
from lfx.base.datasource.manager import DataSourceManager


class TestConnectionStringBuilding:
    """Test connection string building for different database types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = DataSourceManager()

    def test_mysql_connection_string(self):
        """Test MySQL connection string generation."""
        datasource = {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "username": "user",
            "password": "pass",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("mysql+pymysql://")
        assert "localhost:3306" in conn_str
        assert "testdb" in conn_str

    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation."""
        datasource = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "user",
            "password": "pass",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("postgresql://")
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str

    def test_hive_connection_string_with_auth(self):
        """Test Hive connection string with authentication."""
        datasource = {
            "type": "hive",
            "host": "localhost",
            "port": 10000,
            "database": "default",
            "username": "hive",
            "password": "secret",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("jdbc:hive2://")
        assert "localhost:10000" in conn_str
        assert "default" in conn_str
        assert "user=hive" in conn_str

    def test_hive_connection_string_without_auth(self):
        """Test Hive connection string without authentication."""
        datasource = {
            "type": "hive",
            "host": "localhost",
            "port": 10000,
            "database": "default",
            "username": "",
            "password": "",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("jdbc:hive2://")
        assert "localhost:10000" in conn_str
        assert "default" in conn_str
        # Should not have authentication params
        assert "user=" not in conn_str or "user=hive" in conn_str  # Default user

    def test_neo4j_connection_string_with_auth(self):
        """Test Neo4j connection string with authentication."""
        datasource = {
            "type": "neo4j",
            "host": "localhost",
            "port": 7687,
            "database": "neo4j",
            "username": "neo4j",
            "password": "password",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("neo4j://")
        assert "localhost:7687" in conn_str

    def test_neo4j_connection_string_without_auth(self):
        """Test Neo4j connection string without authentication."""
        datasource = {
            "type": "neo4j",
            "host": "localhost",
            "port": 7687,
            "database": "neo4j",
            "username": "",
            "password": "",
        }
        conn_str = self.manager._build_connection_string(datasource)
        assert conn_str.startswith("neo4j://")
        assert "localhost:7687" in conn_str

    def test_unsupported_database_type(self):
        """Test that unsupported database types raise ValueError."""
        datasource = {
            "type": "oracle",
            "host": "localhost",
            "port": 1521,
            "database": "testdb",
            "username": "user",
            "password": "pass",
        }
        with pytest.raises(ValueError, match="Unsupported database type"):
            self.manager._build_connection_string(datasource)

    def test_special_characters_in_credentials(self):
        """Test that special characters in credentials are properly encoded."""
        datasource = {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "username": "user@domain",
            "password": "p@ss!word#123",
        }
        conn_str = self.manager._build_connection_string(datasource)
        # Special characters should be URL-encoded
        assert "user%40domain" in conn_str  # @ encoded as %40
        assert "p%40ss" in conn_str  # @ encoded
        assert "word%23123" in conn_str  # # encoded as %23
