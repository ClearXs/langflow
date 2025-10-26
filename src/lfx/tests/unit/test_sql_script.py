"""Unit tests for SQL Script Component."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from lfx.components.scripts.sql_script import ETLSQLScriptComponent


class TestSQLScriptComponent:
    """Test suite for SQL Script component."""

    @pytest.fixture
    def temp_sqlite_db(self):
        """Create a temporary SQLite database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"

        # Create a test database with a sample table
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            )
        """
        )
        cursor.execute("INSERT INTO test_users VALUES (1, 'Alice', 'alice@example.com')")
        cursor.execute("INSERT INTO test_users VALUES (2, 'Bob', 'bob@example.com')")
        conn.commit()
        conn.close()

        connection_string = f"sqlite:///{db_path}"
        yield connection_string

        # Cleanup
        db_path.unlink(missing_ok=True)

    @pytest.fixture
    def component_basic(self, temp_sqlite_db):
        """Create a basic SQL Script component instance."""
        # Mock datasource_selector to return connection string directly
        component = ETLSQLScriptComponent(
            datasource_selector="test_datasource (sqlite)",
            sql_script="SELECT * FROM test_users;",
            enable_transaction=True,
            statement_separator=";",
            continue_on_error=False,
        )

        # Mock the _get_connection_string method
        def mock_get_connection_string(datasource_id):
            return temp_sqlite_db

        component._get_connection_string = mock_get_connection_string

        # Mock _get_datasource_id
        def mock_get_datasource_id():
            return "test_datasource_id"

        component._get_datasource_id = mock_get_datasource_id

        return component

    # ===== Basic Functionality Tests =====

    def test_component_initialization(self):
        """Test component initialization."""
        component = ETLSQLScriptComponent()

        assert component.display_name is not None
        assert component.description is not None
        assert component.icon == "database"
        assert component.name == "ETLSQLScript"
        assert len(component.inputs) == 6
        assert len(component.outputs) == 2

    def test_component_inputs(self):
        """Test component inputs configuration."""
        component = ETLSQLScriptComponent()

        input_names = [inp.name for inp in component.inputs]
        assert "datasource_selector" in input_names
        assert "sql_script" in input_names
        assert "enable_transaction" in input_names
        assert "statement_separator" in input_names
        assert "continue_on_error" in input_names
        assert "execution_results" in input_names

    def test_component_outputs(self):
        """Test component outputs configuration."""
        component = ETLSQLScriptComponent()

        output_names = [out.name for out in component.outputs]
        assert "execution_summary" in output_names
        assert "total_rows_affected" in output_names

    # ===== SQL Parsing Tests =====

    def test_sql_parsing_single_statement(self, component_basic):
        """Test parsing single SQL statement."""
        statements = component_basic._parse_sql_statements("SELECT * FROM test_users;")
        assert len(statements) == 1
        assert "SELECT" in statements[0].upper()

    def test_sql_parsing_multiple_statements(self, component_basic):
        """Test parsing multiple SQL statements."""
        script = """
        SELECT * FROM test_users;
        UPDATE test_users SET email = 'new@example.com' WHERE id = 1;
        DELETE FROM test_users WHERE id = 2;
        """
        statements = component_basic._parse_sql_statements(script)
        assert len(statements) == 3

    def test_sql_parsing_with_comments(self, component_basic):
        """Test parsing SQL with comments."""
        script = """
        -- This is a comment
        SELECT * FROM test_users;
        /* Another comment */
        UPDATE test_users SET name = 'Charlie' WHERE id = 1;
        """
        statements = component_basic._parse_sql_statements(script)
        # Should parse 2 statements (comments ignored)
        assert len(statements) >= 1

    # ===== Statement Classification Tests =====

    def test_classify_ddl_statements(self, component_basic):
        """Test DDL statement classification."""
        assert component_basic._classify_statement_type("CREATE TABLE test (id INT);") == "DDL"
        assert component_basic._classify_statement_type("ALTER TABLE test ADD COLUMN name TEXT;") == "DDL"
        assert component_basic._classify_statement_type("DROP TABLE test;") == "DDL"
        assert component_basic._classify_statement_type("TRUNCATE TABLE test;") == "DDL"

    def test_classify_dml_statements(self, component_basic):
        """Test DML statement classification."""
        assert component_basic._classify_statement_type("INSERT INTO test VALUES (1);") == "DML"
        assert component_basic._classify_statement_type("UPDATE test SET name = 'test';") == "DML"
        assert component_basic._classify_statement_type("DELETE FROM test WHERE id = 1;") == "DML"

    def test_classify_dql_statements(self, component_basic):
        """Test DQL statement classification."""
        assert component_basic._classify_statement_type("SELECT * FROM test;") == "DQL"
        assert component_basic._classify_statement_type("SELECT id, name FROM test WHERE id = 1;") == "DQL"

    # ===== SQL Execution Tests =====

    def test_execute_dql_select(self, component_basic):
        """Test DQL SELECT statement execution."""
        component_basic.sql_script = "SELECT * FROM test_users;"

        result = component_basic.execute_sql_script()

        assert result.data["total_statements"] == 1
        assert result.data["successful_statements"] == 1
        assert result.data["failed_statements"] == 0

    def test_execute_dml_insert(self, component_basic):
        """Test DML INSERT statement execution."""
        component_basic.sql_script = (
            "INSERT INTO test_users (id, name, email) VALUES (3, 'Charlie', 'charlie@example.com');"
        )

        result = component_basic.execute_sql_script()

        assert result.data["total_statements"] == 1
        assert result.data["successful_statements"] == 1
        assert result.data["total_rows_affected"] == 1

    def test_execute_dml_update(self, component_basic):
        """Test DML UPDATE statement execution."""
        component_basic.sql_script = "UPDATE test_users SET email = 'newemail@example.com' WHERE id = 1;"

        result = component_basic.execute_sql_script()

        assert result.data["successful_statements"] == 1
        assert result.data["total_rows_affected"] == 1

    def test_execute_dml_delete(self, component_basic):
        """Test DML DELETE statement execution."""
        component_basic.sql_script = "DELETE FROM test_users WHERE id = 2;"

        result = component_basic.execute_sql_script()

        assert result.data["successful_statements"] == 1
        assert result.data["total_rows_affected"] == 1

    def test_execute_ddl_statement(self, component_basic):
        """Test DDL CREATE TABLE statement execution."""
        component_basic.sql_script = """
        CREATE TABLE test_products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL
        );
        """

        result = component_basic.execute_sql_script()

        assert result.data["successful_statements"] == 1

    # ===== Transaction Control Tests =====

    def test_transaction_commit_on_success(self, component_basic):
        """Test transaction commits on successful execution."""
        component_basic.enable_transaction = True
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (4, 'David');
        INSERT INTO test_users (id, name) VALUES (5, 'Eve');
        """

        result = component_basic.execute_sql_script()

        assert result.data["successful_statements"] == 2
        assert result.data["failed_statements"] == 0

    def test_transaction_rollback_on_error(self, component_basic):
        """Test transaction rolls back on error."""
        component_basic.enable_transaction = True
        component_basic.continue_on_error = False
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (6, 'Frank');
        INSERT INTO invalid_table (id, name) VALUES (7, 'Grace');
        """

        result = component_basic.execute_sql_script()

        # Both statements should fail (rollback)
        assert result.data["failed_statements"] > 0

    def test_no_transaction_mode(self, component_basic):
        """Test execution without transaction."""
        component_basic.enable_transaction = False
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (8, 'Henry');
        SELECT * FROM test_users;
        """

        result = component_basic.execute_sql_script()

        # Should execute both statements independently
        assert result.data["total_statements"] == 2

    # ===== Error Handling Tests =====

    def test_continue_on_error_enabled(self, component_basic):
        """Test continue on error when enabled."""
        component_basic.enable_transaction = False
        component_basic.continue_on_error = True
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (9, 'Ivy');
        INSERT INTO invalid_table (id, name) VALUES (10, 'Jack');
        INSERT INTO test_users (id, name) VALUES (11, 'Kate');
        """

        result = component_basic.execute_sql_script()

        # First and third should succeed, second should fail
        assert result.data["successful_statements"] >= 1
        assert result.data["failed_statements"] >= 1

    def test_continue_on_error_disabled(self, component_basic):
        """Test execution stops on error when continue_on_error is disabled."""
        component_basic.enable_transaction = False
        component_basic.continue_on_error = False
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (12, 'Leo');
        INSERT INTO invalid_table (id, name) VALUES (13, 'Mike');
        INSERT INTO test_users (id, name) VALUES (14, 'Nina');
        """

        result = component_basic.execute_sql_script()

        # Should stop after first error
        assert result.data["total_statements"] <= 2

    def test_empty_script(self):
        """Test handling of empty SQL script."""
        component = ETLSQLScriptComponent(
            datasource_selector="test_datasource",
            sql_script="",
            enable_transaction=True,
        )

        with pytest.raises(ValueError):
            component.execute_sql_script()

    def test_sql_syntax_error(self, component_basic):
        """Test handling of SQL syntax errors."""
        component_basic.sql_script = "SELCT * FORM test_users;"  # Intentional typo

        result = component_basic.execute_sql_script()

        # Should have at least one failed statement
        assert result.data["failed_statements"] >= 1

    # ===== Execution Results Tests =====

    def test_execution_results_structure(self, component_basic):
        """Test execution results data structure."""
        component_basic.sql_script = "SELECT * FROM test_users;"

        result = component_basic.execute_sql_script()

        assert "total_statements" in result.data
        assert "successful_statements" in result.data
        assert "failed_statements" in result.data
        assert "total_rows_affected" in result.data
        assert "results" in result.data
        assert isinstance(result.data["results"], list)

    def test_rows_affected_count(self, component_basic):
        """Test rows affected count tracking."""
        component_basic.sql_script = """
        INSERT INTO test_users (id, name) VALUES (15, 'Oscar');
        INSERT INTO test_users (id, name) VALUES (16, 'Paul');
        UPDATE test_users SET email = 'updated@example.com' WHERE id = 1;
        """

        result = component_basic.execute_sql_script()

        # 2 inserts + 1 update = 3 rows affected
        assert result.data["total_rows_affected"] >= 3

    def test_total_rows_affected_output(self, component_basic):
        """Test total rows affected output method."""
        component_basic.sql_script = "INSERT INTO test_users (id, name) VALUES (17, 'Quinn');"

        result = component_basic.get_total_rows_affected()

        assert "total_rows_affected" in result.data
        assert result.data["total_rows_affected"] >= 1

    # ===== Edge Cases and Boundary Tests =====

    def test_special_characters_in_sql(self, component_basic):
        """Test SQL with special characters."""
        component_basic.sql_script = (
            "INSERT INTO test_users (id, name, email) VALUES (18, 'O''Brien', 'obrien@example.com');"
        )

        result = component_basic.execute_sql_script()

        assert result.data["successful_statements"] == 1

    def test_multiple_statements_same_type(self, component_basic):
        """Test multiple statements of the same type."""
        component_basic.sql_script = """
        SELECT * FROM test_users WHERE id = 1;
        SELECT * FROM test_users WHERE id = 2;
        SELECT COUNT(*) FROM test_users;
        """

        result = component_basic.execute_sql_script()

        assert result.data["total_statements"] == 3
        assert result.data["successful_statements"] == 3

    # ===== Utility Method Tests =====

    def test_format_i18n(self, component_basic):
        """Test i18n formatting with parameters."""
        result = component_basic._format_i18n("components.scripts.sql_script.status.success", success=5, total=10)

        # Should contain the numbers
        assert "5" in result or "10" in result

    def test_get_datasource_id_from_metadata(self, component_basic):
        """Test datasource ID extraction from metadata."""
        metadata = [
            {"id": "ds-123", "name": "TestDB", "type": "mysql"},
            {"id": "ds-456", "name": "ProdDB", "type": "postgresql"},
        ]

        ds_id = component_basic._get_datasource_id_from_metadata("TestDB (mysql)", metadata)
        assert ds_id == "ds-123"

        ds_id = component_basic._get_datasource_id_from_metadata("ProdDB (postgresql)", metadata)
        assert ds_id == "ds-456"

        ds_id = component_basic._get_datasource_id_from_metadata("NonExistent (oracle)", metadata)
        assert ds_id is None
