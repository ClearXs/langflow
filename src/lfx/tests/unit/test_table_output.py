"""Unit tests for ETL Table Output Component."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lfx.components.input_output.table_output import ETLTableOutputComponent
from lfx.schema import Data


class TestETLTableOutputComponent:
    """Test suite for ETLTableOutputComponent."""

    @pytest.fixture
    def component(self):
        """Create a basic component instance."""
        return ETLTableOutputComponent()

    @pytest.fixture
    def sample_data(self):
        """Create sample Data objects."""
        return [
            Data(data={"id": 1, "name": "Alice", "age": 30}),
            Data(data={"id": 2, "name": "Bob", "age": 25}),
            Data(data={"id": 3, "name": "Charlie", "age": 35}),
        ]

    @pytest.fixture
    def sample_field_mappings(self):
        """Create sample field mappings."""
        return [
            {
                "source_field": "id",
                "target_field": "id",
                "data_type": "integer",
                "update_option": "sync_update",
                "is_key_field": True,
                "null_value": "",
            },
            {
                "source_field": "name",
                "target_field": "name",
                "data_type": "string",
                "update_option": "sync_update",
                "is_key_field": False,
                "null_value": "",
            },
            {
                "source_field": "age",
                "target_field": "age",
                "data_type": "integer",
                "update_option": "sync_update",
                "is_key_field": False,
                "null_value": "0",
            },
        ]

    # ========== Component Initialization Tests ==========

    def test_component_creation(self, component):
        """Test that component is created successfully."""
        assert component is not None
        assert component.name == "ETLTableOutput"
        assert component.display_name is not None
        assert component.icon == "database"

    def test_component_has_required_inputs(self, component):
        """Test that component has all required inputs."""
        input_names = [inp.name for inp in component.inputs]

        assert "data_input" in input_names
        assert "datasource_selector" in input_names
        assert "table_selector" in input_names
        assert "field_mappings" in input_names
        assert "write_mode" in input_names
        assert "batch_size" in input_names

    def test_component_has_outputs(self, component):
        """Test that component has expected outputs."""
        output_names = [out.name for out in component.outputs]

        assert "result" in output_names
        assert "row_count" in output_names

    # ========== Helper Method Tests ==========

    def test_get_datasource_id_from_metadata(self, component):
        """Test datasource ID extraction from metadata."""
        metadata = [
            {"id": "ds1", "name": "TestDB", "type": "mysql"},
            {"id": "ds2", "name": "ProdDB", "type": "postgresql"},
        ]

        # Test exact match
        ds_id = component._get_datasource_id_from_metadata("TestDB (mysql)", metadata)
        assert ds_id == "ds1"

        # Test second item
        ds_id = component._get_datasource_id_from_metadata("ProdDB (postgresql)", metadata)
        assert ds_id == "ds2"

        # Test no match
        ds_id = component._get_datasource_id_from_metadata("Unknown (mysql)", metadata)
        assert ds_id is None

    def test_infer_data_type(self, component):
        """Test data type inference."""
        assert component._infer_data_type(None) == "string"
        assert component._infer_data_type(True) == "boolean"
        assert component._infer_data_type(False) == "boolean"
        assert component._infer_data_type(42) == "integer"
        assert component._infer_data_type(3.14) == "float"
        assert component._infer_data_type("hello") == "string"
        assert component._infer_data_type([1, 2, 3]) == "string"  # Fallback

    def test_apply_field_mappings(self, component, sample_data, sample_field_mappings):
        """Test field mapping application."""
        component.field_mappings = sample_field_mappings

        # Convert sample data to DataFrame
        df = pd.DataFrame([d.data for d in sample_data])

        # Apply mappings
        df_mapped = component._apply_field_mappings(df)

        # Verify columns are renamed (in this case, no change)
        assert list(df_mapped.columns) == ["id", "name", "age"]

        # Verify null value handling
        assert df_mapped is not None

    def test_apply_field_mappings_with_rename(self, component):
        """Test field mapping with column renaming."""
        component.field_mappings = [
            {"source_field": "old_name", "target_field": "new_name", "null_value": ""},
            {"source_field": "status", "target_field": "user_status", "null_value": "active"},
        ]

        df = pd.DataFrame([{"old_name": "Alice", "status": None}])

        df_mapped = component._apply_field_mappings(df)

        # Verify renaming
        assert "new_name" in df_mapped.columns
        assert "user_status" in df_mapped.columns
        assert "old_name" not in df_mapped.columns

        # Verify null value replacement
        assert df_mapped.loc[0, "user_status"] == "active"

    # ========== Update Build Config Tests ==========

    @patch("lfx.components.input_output.table_output.httpx.Client")
    def test_update_build_config_loads_datasources(self, mock_client_class, component):
        """Test that update_build_config loads datasources on initial call."""
        # Mock HTTP response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "ds1", "name": "TestDB", "type": "mysql"},
            {"id": "ds2", "name": "ProdDB", "type": "postgresql"},
        ]
        mock_client.get.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        build_config = {"datasource_selector": {}}

        result = component.update_build_config(build_config, None, field_name=None)

        # Verify datasources were loaded
        assert "options" in result["datasource_selector"]
        assert len(result["datasource_selector"]["options"]) == 2
        assert "TestDB (mysql)" in result["datasource_selector"]["options"]
        assert "ProdDB (postgresql)" in result["datasource_selector"]["options"]

        # Verify metadata was set
        assert "options_metadata" in result["datasource_selector"]
        assert len(result["datasource_selector"]["options_metadata"]) == 2

    @patch("lfx.components.input_output.table_output.httpx.Client")
    def test_update_build_config_loads_tables(self, mock_client_class, component):
        """Test that selecting a datasource loads tables."""
        # Mock HTTP response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["users", "orders", "products"]
        mock_client.get.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        build_config = {
            "datasource_selector": {
                "value": "TestDB (mysql)",
                "options_metadata": [{"id": "ds1", "name": "TestDB", "type": "mysql"}],
            },
            "table_selector": {},
        }

        result = component.update_build_config(build_config, "TestDB (mysql)", field_name="datasource_selector")

        # Verify tables were loaded
        assert "options" in result["table_selector"]
        assert len(result["table_selector"]["options"]) == 3
        assert "users" in result["table_selector"]["options"]

    @patch("lfx.components.input_output.table_output.httpx.Client")
    def test_update_build_config_analyze_schema(self, mock_client_class, component):
        """Test schema analysis button."""
        build_config = {
            "data_input": {"value": [Data(data={"id": 1, "name": "Alice", "age": 30})]},
            "field_mappings": {"value": [], "table_schema": []},
        }

        result = component.update_build_config(build_config, None, field_name="field_mappings", action="analyze_schema")

        # Verify field mappings were generated
        assert len(result["field_mappings"]["value"]) == 3
        field_names = [f["source_field"] for f in result["field_mappings"]["value"]]
        assert "id" in field_names
        assert "name" in field_names
        assert "age" in field_names

    def test_update_build_config_auto_map_fields(self, component):
        """Test auto field mapping."""
        build_config = {
            "field_mappings": {
                "value": [
                    {"source_field": "id", "target_field": "", "update_option": "sync_update"},
                    {"source_field": "name", "target_field": "", "update_option": "sync_update"},
                ],
                "table_schema": [
                    {"name": "target_field", "options": ["ID", "NAME", "EMAIL"]},
                ],
            }
        }

        result = component.update_build_config(
            build_config, None, field_name="field_mappings", action="auto_map_fields"
        )

        # Verify fields were auto-mapped (case-insensitive)
        mappings = result["field_mappings"]["value"]
        assert mappings[0]["target_field"] == "ID"
        assert mappings[1]["target_field"] == "NAME"

    # ========== Write Mode Tests ==========

    @patch("lfx.components.input_output.table_output.create_engine")
    @patch("lfx.components.input_output.table_output.httpx.Client")
    def test_write_batch_insert(self, mock_client_class, mock_create_engine, component, sample_data):
        """Test batch insert mode."""
        # Setup component
        component.data_input = sample_data
        component.datasource_selector = "TestDB (mysql)"
        component.table_selector = "users"
        component.write_mode = "batch_insert"
        component.field_mappings = []

        # Mock datasource API
        mock_client = MagicMock()
        mock_ds_response = MagicMock()
        mock_ds_response.status_code = 200
        mock_ds_response.json.return_value = [{"id": "ds1", "name": "TestDB", "type": "mysql"}]

        mock_conn_response = MagicMock()
        mock_conn_response.status_code = 200
        mock_conn_response.json.return_value = {"connection_string": "mysql://user:pass@localhost/testdb"}

        mock_client.get.side_effect = [mock_ds_response, mock_conn_response]
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        # Mock database engine
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.connect.return_value.__exit__.return_value = None
        mock_create_engine.return_value = mock_engine

        # Execute
        result = component.write_to_table()

        # Verify result
        assert result.data["success"] is True
        assert result.data["rows_written"] == 3
        assert result.data["write_mode"] == "batch_insert"

    @patch("lfx.components.input_output.table_output.create_engine")
    @patch("lfx.components.input_output.table_output.httpx.Client")
    def test_write_upsert_mode(
        self, mock_client_class, mock_create_engine, component, sample_data, sample_field_mappings
    ):
        """Test upsert mode with key fields."""
        # Setup component
        component.data_input = sample_data
        component.datasource_selector = "TestDB (mysql)"
        component.table_selector = "users"
        component.write_mode = "upsert"
        component.field_mappings = sample_field_mappings

        # Mock datasource API
        mock_client = MagicMock()
        mock_ds_response = MagicMock()
        mock_ds_response.status_code = 200
        mock_ds_response.json.return_value = [{"id": "ds1", "name": "TestDB", "type": "mysql"}]

        mock_conn_response = MagicMock()
        mock_conn_response.status_code = 200
        mock_conn_response.json.return_value = {"connection_string": "mysql://user:pass@localhost/testdb"}

        mock_client.get.side_effect = [mock_ds_response, mock_conn_response]
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        # Mock database engine
        mock_engine = MagicMock()
        mock_connection = MagicMock()

        # Mock scalar() to return 0 (no existing records)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_connection.execute.return_value = mock_result

        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.connect.return_value.__exit__.return_value = None
        mock_create_engine.return_value = mock_engine

        # Execute
        result = component.write_to_table()

        # Verify result
        assert result.data["success"] is True
        assert result.data["write_mode"] == "upsert"

    def test_write_upsert_without_key_fields_raises_error(self, component, sample_data):
        """Test that upsert without key fields raises an error."""
        component.data_input = sample_data
        component.datasource_selector = "TestDB (mysql)"
        component.table_selector = "users"
        component.write_mode = "upsert"
        component.field_mappings = [
            {"source_field": "name", "target_field": "name", "is_key_field": False}  # No key field!
        ]

        with pytest.raises(ValueError, match="No key fields"):
            # Mock the datasource ID methods to bypass API calls
            with patch.object(component, "_get_datasource_id", return_value="ds1"):
                with patch.object(component, "_get_connection_string", return_value="mysql://localhost/test"):
                    with patch("lfx.components.input_output.table_output.create_engine"):
                        component.write_to_table()

    # ========== Validation Tests ==========

    def test_write_without_data_raises_error(self, component):
        """Test that writing without data raises an error."""
        component.data_input = []
        component.datasource_selector = "TestDB (mysql)"
        component.table_selector = "users"

        with pytest.raises(ValueError, match="No data"):
            component.write_to_table()

    def test_write_without_datasource_raises_error(self, component, sample_data):
        """Test that writing without datasource raises an error."""
        component.data_input = sample_data
        component.datasource_selector = None
        component.table_selector = "users"

        with pytest.raises(ValueError, match="No datasource"):
            component.write_to_table()

    def test_write_without_table_raises_error(self, component, sample_data):
        """Test that writing without table raises an error."""
        component.data_input = sample_data
        component.datasource_selector = "TestDB (mysql)"
        component.table_selector = None

        with pytest.raises(ValueError, match="No table"):
            component.write_to_table()

    # ========== Integration Tests ==========

    def test_get_row_count(self, component):
        """Test get_row_count output."""
        # Mock write_to_table to return a result
        mock_result = Data(data={"rows_written": 42, "table": "users"})

        with patch.object(component, "write_to_table", return_value=mock_result):
            result = component.get_row_count()

            assert result.data["row_count"] == 42
            assert "table" in result.data

    @pytest.mark.parametrize(
        "write_mode",
        ["batch_insert", "append", "replace", "upsert"],
    )
    def test_all_write_modes_supported(self, component, write_mode):
        """Test that all write modes are recognized."""
        component.write_mode = write_mode

        # Create a mock DataFrame
        mock_df = pd.DataFrame([{"id": 1, "name": "Test"}])
        mock_connection = MagicMock()

        # For upsert mode, add field_mappings with key field
        if write_mode == "upsert":
            component.field_mappings = [
                {"source_field": "id", "target_field": "id", "is_key_field": True, "update_option": "sync_update"}
            ]
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_connection.execute.return_value = mock_result

        # Execute
        rows = component._execute_write(mock_connection, mock_df)

        # Verify execution completed without error
        assert rows is not None

    def test_unknown_write_mode_raises_error(self, component):
        """Test that unknown write mode raises an error."""
        component.write_mode = "invalid_mode"
        mock_df = pd.DataFrame([{"id": 1}])
        mock_connection = MagicMock()

        with pytest.raises(ValueError, match="Unknown write mode"):
            component._execute_write(mock_connection, mock_df)
