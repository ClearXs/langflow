"""Unit tests for TableInputComponent.

This test suite covers all functionality of the TableInputComponent including:
- Component initialization
- Database connection management
- SQL query validation and execution
- Data transformation and output
- Error handling and edge cases
"""

import re
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from lfx.components.input_output.table_input import TableInputComponent
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class TestTableInputComponent:
    """Test suite for TableInputComponent."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock i18n translation to return test strings
        self.i18n_patcher = patch(
            'lfx.components.input_output.table_input.i18n.t', side_effect=self._mock_translation)
        self.i18n_patcher.start()

        self.component = TableInputComponent()

        # Set default attributes
        self.component.database_connection = "test_db"
        self.component.sql_query = "SELECT * FROM users"
        self.component.safe_mode = True

    def teardown_method(self):
        """Clean up after each test method."""
        self.i18n_patcher.stop()

    @staticmethod
    def _mock_translation(key, **kwargs):
        """Mock translation function for i18n.t."""
        translations = {
            'components.input_output.table_input.display_name': 'Table Input',
            'components.input_output.table_input.description': 'Execute SQL queries on database connections',
            'components.input_output.table_input.database_connection.display_name': 'Database Connection',
            'components.input_output.table_input.database_connection.info': 'Select a database connection',
            'components.input_output.table_input.sql_query.display_name': 'SQL Query',
            'components.input_output.table_input.sql_query.info': 'Enter your SQL query',
            'components.input_output.table_input.safe_mode.display_name': 'Safe Mode',
            'components.input_output.table_input.safe_mode.info': 'Enable safe mode to prevent dangerous operations',
            'components.input_output.table_input.outputs.data.display_name': 'Data',
            'components.input_output.table_input.outputs.dataframe.display_name': 'DataFrame',
            'components.input_output.table_input.errors.missing_connection': 'Database connection is required',
            'components.input_output.table_input.errors.connection_not_found': 'Connection {name} not found',
            'components.input_output.table_input.errors.sqlalchemy_required': 'SQLAlchemy is required',
            'components.input_output.table_input.errors.connection_failed': 'Connection failed: {error}',
            'components.input_output.table_input.errors.dangerous_operation': 'Dangerous operation {keyword} is not allowed',
            'components.input_output.table_input.errors.empty_query': 'SQL query cannot be empty',
            'components.input_output.table_input.errors.execution_error': 'Query execution failed: {error}',
            'components.input_output.table_input.errors.dataframe_error': 'DataFrame creation failed: {error}',
            'components.input_output.table_input.warnings.no_results': 'Query returned no results',
            'components.input_output.table_input.success.loaded': 'Successfully loaded {rows} rows',
        }
        result = translations.get(key, key)
        if kwargs:
            result = result.format(**kwargs)
        return result

    # ===== Component Initialization Tests =====

    def test_component_initialization(self):
        """Test that component initializes with correct attributes."""
        assert self.component.display_name == 'Table Input'
        assert self.component.description == 'Execute SQL queries on database connections'
        assert self.component.icon == "table"
        assert self.component.name == "TableInput"

    def test_component_has_required_inputs(self):
        """Test that component has all required input fields."""
        assert len(self.component.inputs) == 3

        input_names = [inp.name for inp in self.component.inputs]
        assert "database_connection" in input_names
        assert "sql_query" in input_names
        assert "safe_mode" in input_names

    def test_component_has_required_outputs(self):
        """Test that component has all required output methods."""
        assert len(self.component.outputs) == 2

        output_names = [out.name for out in self.component.outputs]
        assert "data" in output_names
        assert "dataframe" in output_names

    # ===== Update Build Config Tests =====

    def test_update_build_config_database_connection(self):
        """Test updating build config for database_connection field."""
        build_config = {
            "database_connection": {
                "options": [],
                "options_metadata": []
            }
        }

        result = self.component.update_build_config(
            build_config,
            None,
            "database_connection"
        )

        assert "database_connection" in result
        assert len(result["database_connection"]["options"]) > 0

    def test_update_build_config_other_field(self):
        """Test that update_build_config doesn't modify non-database fields."""
        build_config = {"sql_query": {"value": "SELECT * FROM test"}}

        result = self.component.update_build_config(
            build_config,
            "SELECT * FROM test",
            "sql_query"
        )

        # Should return unchanged for non-database_connection fields
        assert result == build_config

    # ===== Database Connection Tests =====

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_database_connections_with_dict_config(self, mock_nacos):
        """Test retrieving database connections from Nacos with dict config."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [
                {"name": "db1", "host": "localhost"},
                {"name": "db2", "host": "remote"}
            ]
        }
        mock_nacos.return_value = mock_client

        connections = self.component._get_database_connections()

        assert connections == ["db1", "db2"]
        mock_client.get_json.assert_called_once_with(
            "database-connections", "DEFAULT_GROUP")

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_database_connections_with_list_config(self, mock_nacos):
        """Test retrieving database connections from Nacos with list config."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = [
            {"name": "db1", "host": "localhost"},
            {"name": "db2", "host": "remote"}
        ]
        mock_nacos.return_value = mock_client

        connections = self.component._get_database_connections()

        assert connections == ["db1", "db2"]

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_database_connections_no_nacos(self, mock_nacos):
        """Test retrieving database connections when Nacos is unavailable."""
        mock_nacos.return_value = None

        connections = self.component._get_database_connections()

        assert connections == []

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_database_connections_exception(self, mock_nacos):
        """Test retrieving database connections when exception occurs."""
        mock_nacos.side_effect = Exception("Connection error")

        connections = self.component._get_database_connections()

        assert connections == []

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_connection_config(self, mock_nacos):
        """Test retrieving specific connection configuration."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [
                {"name": "db1", "host": "localhost", "port": 3306},
                {"name": "db2", "host": "remote", "port": 5432}
            ]
        }
        mock_nacos.return_value = mock_client

        config = self.component._get_connection_config("db1")

        assert config["name"] == "db1"
        assert config["host"] == "localhost"
        assert config["port"] == 3306

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_connection_config_not_found(self, mock_nacos):
        """Test retrieving non-existent connection configuration."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [
                {"name": "db1", "host": "localhost"}
            ]
        }
        mock_nacos.return_value = mock_client

        config = self.component._get_connection_config("nonexistent")

        assert config is None

    # ===== SQL Query Validation Tests =====

    def test_validate_query_safety_safe_query(self):
        """Test that safe SELECT query passes validation."""
        query = "SELECT * FROM users WHERE id = 1"

        # Should not raise exception
        self.component._validate_query_safety(query)

    def test_validate_query_safety_drop_query(self):
        """Test that DROP query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "DROP TABLE users"

        with pytest.raises(ValueError, match="DROP"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_delete_query(self):
        """Test that DELETE query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "DELETE FROM users WHERE id = 1"

        with pytest.raises(ValueError, match="DELETE"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_update_query(self):
        """Test that UPDATE query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "UPDATE users SET name = 'test'"

        with pytest.raises(ValueError, match="UPDATE"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_insert_query(self):
        """Test that INSERT query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "INSERT INTO users (name) VALUES ('test')"

        with pytest.raises(ValueError, match="INSERT"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_truncate_query(self):
        """Test that TRUNCATE query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "TRUNCATE TABLE users"

        with pytest.raises(ValueError, match="TRUNCATE"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_alter_query(self):
        """Test that ALTER query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "ALTER TABLE users ADD COLUMN email VARCHAR(255)"

        with pytest.raises(ValueError, match="ALTER"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_create_query(self):
        """Test that CREATE query is blocked in safe mode."""
        self.component.safe_mode = True
        query = "CREATE TABLE test (id INT)"

        with pytest.raises(ValueError, match="CREATE"):
            self.component._validate_query_safety(query)

    def test_validate_query_safety_disabled(self):
        """Test that dangerous queries are allowed when safe mode is disabled."""
        self.component.safe_mode = False
        query = "DROP TABLE users"

        # Should not raise exception
        self.component._validate_query_safety(query)

    def test_validate_query_safety_case_insensitive(self):
        """Test that validation is case-insensitive."""
        self.component.safe_mode = True
        query = "drop table users"

        with pytest.raises(ValueError, match="DROP"):
            self.component._validate_query_safety(query)

    # ===== Connection Creation Tests =====

    @patch('lfx.base.nacos.create_nacos_config')
    @patch('sqlalchemy.create_engine')
    def test_get_connection_mysql(self, mock_create_engine, mock_nacos):
        """Test creating MySQL database connection."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [{
                "name": "test_db",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "testdb",
                "username": "user",
                "password": "pass"
            }]
        }
        mock_nacos.return_value = mock_client

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        # Test
        connection = self.component._get_connection()

        # Verify
        assert connection == mock_connection
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "mysql+pymysql" in call_args
        assert "localhost" in call_args
        assert "3306" in call_args

    @patch('lfx.base.nacos.create_nacos_config')
    @patch('sqlalchemy.create_engine')
    def test_get_connection_postgresql(self, mock_create_engine, mock_nacos):
        """Test creating PostgreSQL database connection."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [{
                "name": "test_db",
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user",
                "password": "pass"
            }]
        }
        mock_nacos.return_value = mock_client

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        connection = self.component._get_connection()

        assert connection == mock_connection
        call_args = mock_create_engine.call_args[0][0]
        assert "postgresql+psycopg2" in call_args

    @patch('lfx.base.nacos.create_nacos_config')
    @patch('sqlalchemy.create_engine')
    def test_get_connection_sqlite(self, mock_create_engine, mock_nacos):
        """Test creating SQLite database connection."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [{
                "name": "test_db",
                "type": "sqlite",
                "database": "/path/to/db.sqlite"
            }]
        }
        mock_nacos.return_value = mock_client

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        connection = self.component._get_connection()

        assert connection == mock_connection
        call_args = mock_create_engine.call_args[0][0]
        assert "sqlite:///" in call_args

    def test_get_connection_missing_database_connection(self):
        """Test that missing database_connection raises ValueError."""
        self.component.database_connection = None

        with pytest.raises(ValueError, match="required"):
            self.component._get_connection()

    @patch('lfx.base.nacos.create_nacos_config')
    def test_get_connection_config_not_found(self, mock_nacos):
        """Test that connection error is raised when config not found."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {"connections": []}
        mock_nacos.return_value = mock_client

        with pytest.raises(ValueError, match="not found"):
            self.component._get_connection()

    @patch('lfx.base.nacos.create_nacos_config')
    @patch('sqlalchemy.create_engine')
    def test_get_connection_engine_failure(self, mock_create_engine, mock_nacos):
        """Test that connection error is raised when engine creation fails."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [{
                "name": "test_db",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "testdb",
                "username": "user",
                "password": "pass"
            }]
        }
        mock_nacos.return_value = mock_client
        mock_create_engine.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError, match="Connection failed"):
            self.component._get_connection()

    # ===== Load Data Tests =====

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_data_success(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test successful data loading."""
        # Setup
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35]
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"

        # Execute
        result = self.component.load_data()

        # Verify
        assert len(result) == 3
        assert all(isinstance(item, Data) for item in result)
        assert result[0].data['name'] == 'Alice'
        assert result[1].data['name'] == 'Bob'
        assert result[2].data['name'] == 'Charlie'
        assert '_row_index' in result[0].data
        assert 'text' in result[0].data

        mock_validate.assert_called_once()
        mock_get_conn.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_data_empty_result(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test loading data with empty query result."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        empty_df = pd.DataFrame()
        mock_read_sql.return_value = empty_df

        self.component.sql_query = "SELECT * FROM users WHERE id = 999"

        result = self.component.load_data()

        assert result == []
        assert "no results" in self.component.status.lower()
        mock_connection.close.assert_called_once()

    def test_load_data_empty_query(self):
        """Test that empty query raises ValueError."""
        self.component.sql_query = "   "

        with pytest.raises(ValueError, match="empty"):
            self.component.load_data()

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_data_execution_error(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test that query execution error is properly handled."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection
        mock_read_sql.side_effect = Exception("SQL syntax error")

        self.component.sql_query = "SELECT * FORM users"  # Intentional typo

        with pytest.raises(ValueError, match="execution"):
            self.component.load_data()

        mock_connection.close.assert_called_once()

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_data_text_generation(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test that text field is properly generated from row data."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'id': [1],
            'name': ['Alice'],
            'email': ['alice@test.com']
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"
        result = self.component.load_data()

        # Verify text field contains all non-underscore fields
        text = result[0].data['text']
        assert 'id: 1' in text
        assert 'name: Alice' in text
        assert 'email: alice@test.com' in text
        assert '_row_index' not in text  # Should not include underscore fields

        mock_connection.close.assert_called_once()

    # ===== Load DataFrame Tests =====

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_dataframe_success(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test successful DataFrame loading."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"

        result = self.component.load_dataframe()

        assert isinstance(result, DataFrame)
        assert len(result.data) == 3
        assert list(result.data.columns) == ['id', 'name']

        mock_validate.assert_called_once()
        mock_get_conn.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_load_dataframe_empty_query(self):
        """Test that empty query raises ValueError for DataFrame."""
        self.component.sql_query = ""

        with pytest.raises(ValueError, match="empty"):
            self.component.load_dataframe()

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_load_dataframe_execution_error(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test that DataFrame execution error is properly handled."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection
        mock_read_sql.side_effect = Exception("Database error")

        self.component.sql_query = "SELECT * FROM users"

        with pytest.raises(ValueError, match="DataFrame|dataframe"):
            self.component.load_dataframe()

        mock_connection.close.assert_called_once()

    # ===== Integration Tests =====

    @patch.object(TableInputComponent, '_get_connection')
    @patch.object(TableInputComponent, '_validate_query_safety')
    @patch('pandas.read_sql_query')
    def test_safe_mode_integration(self, mock_read_sql, mock_validate, mock_get_conn):
        """Test safe mode validation during data loading."""
        self.component.safe_mode = True
        self.component.sql_query = "DROP TABLE users"

        # Mock validate to raise error as it would in real scenario
        mock_validate.side_effect = ValueError(
            "Dangerous operation DROP is not allowed")

        with pytest.raises(ValueError, match="DROP"):
            self.component.load_data()

        # Connection should not be attempted
        mock_get_conn.assert_not_called()

    @patch.object(TableInputComponent, '_get_connection')
    @patch('pandas.read_sql_query')
    def test_load_data_with_special_characters(self, mock_read_sql, mock_get_conn):
        """Test loading data with special characters in values."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'name': ['O\'Brien', 'José', '北京'],
            'description': ['Test | Pipe', 'Line\nBreak', 'Tab\there']
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"
        result = self.component.load_data()

        assert len(result) == 3
        assert result[0].data['name'] == 'O\'Brien'
        assert result[1].data['name'] == 'José'
        assert result[2].data['name'] == '北京'

        mock_connection.close.assert_called_once()

    @patch.object(TableInputComponent, '_get_connection')
    @patch('pandas.read_sql_query')
    def test_load_data_with_null_values(self, mock_read_sql, mock_get_conn):
        """Test loading data with NULL/None values."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', None, 'Charlie'],
            'email': ['alice@test.com', 'bob@test.com', None]
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"
        result = self.component.load_data()

        assert len(result) == 3
        assert result[0].data['name'] == 'Alice'
        assert pd.isna(result[1].data['name'])
        assert pd.isna(result[2].data['email'])

        mock_connection.close.assert_called_once()

    @patch.object(TableInputComponent, '_get_connection')
    @patch('pandas.read_sql_query')
    def test_status_messages(self, mock_read_sql, mock_get_conn):
        """Test that status messages are properly set during execution."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        test_df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5]
        })
        mock_read_sql.return_value = test_df

        self.component.sql_query = "SELECT * FROM users"
        result = self.component.load_data()

        assert "5" in str(self.component.status)
        assert "loaded" in self.component.status.lower(
        ) or "success" in self.component.status.lower()

        mock_connection.close.assert_called_once()


# ===== Edge Case Tests =====

class TestTableInputEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.i18n_patcher = patch('lfx.components.input_output.table_input.i18n.t',
                                  side_effect=TestTableInputComponent._mock_translation)
        self.i18n_patcher.start()
        self.component = TableInputComponent()
        self.component.safe_mode = True
        self.component.sql_query = "SELECT * FROM test"

    def teardown_method(self):
        """Clean up."""
        self.i18n_patcher.stop()

    def test_query_with_multiple_spaces(self):
        """Test query validation with multiple spaces."""
        self.component.safe_mode = True
        self.component.sql_query = "  SELECT  *  FROM  users  "

        # Should not raise for safe query
        self.component._validate_query_safety(self.component.sql_query.strip())

    def test_dangerous_keyword_in_table_name(self):
        """Test that dangerous keywords in table names are handled correctly."""
        self.component.safe_mode = True
        # The current implementation uses word boundary check \b which means
        # "DELETE" in "user_DELETE_log" would NOT match because it's surrounded
        # by underscores (not word boundaries), so this should pass
        query = "SELECT * FROM user_DELETE_log"

        # Should not raise since DELETE is part of a word, not a standalone keyword
        self.component._validate_query_safety(query)

    def test_query_with_comments(self):
        """Test query with SQL comments."""
        self.component.safe_mode = True
        query = """
        -- This is a comment
        SELECT * FROM users
        -- Another comment
        WHERE id = 1
        """

        # Should not raise for safe query
        self.component._validate_query_safety(query)

    @patch.object(TableInputComponent, '_get_connection')
    @patch('pandas.read_sql_query')
    def test_large_result_set(self, mock_read_sql, mock_get_conn):
        """Test loading large result sets."""
        mock_connection = MagicMock()
        mock_get_conn.return_value = mock_connection

        # Create a large DataFrame
        large_df = pd.DataFrame({
            'id': range(10000),
            'value': [f'value_{i}' for i in range(10000)]
        })
        mock_read_sql.return_value = large_df

        self.component.sql_query = "SELECT * FROM large_table"
        result = self.component.load_data()

        assert len(result) == 10000
        assert all(isinstance(item, Data) for item in result)

        mock_connection.close.assert_called_once()

    @patch('lfx.base.nacos.create_nacos_config')
    @patch('sqlalchemy.create_engine')
    def test_connection_with_special_characters_in_password(
        self, mock_create_engine, mock_nacos
    ):
        """Test creating connection with special characters in password."""
        mock_client = MagicMock()
        mock_client.get_json.return_value = {
            "connections": [{
                "name": "test_db",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "testdb",
                "username": "user",
                "password": "p@ss:w0rd/special"  # Special characters
            }]
        }
        mock_nacos.return_value = mock_client

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        self.component.database_connection = "test_db"
        connection = self.component._get_connection()

        # Verify password is URL-encoded
        call_args = mock_create_engine.call_args[0][0]
        assert "p%40ss%3Aw0rd%2Fspecial" in call_args or "p@ss:w0rd/special" not in call_args
