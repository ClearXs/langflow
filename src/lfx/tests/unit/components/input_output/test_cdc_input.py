"""Unit tests for ETLCDCStreamInputComponent."""

from unittest.mock import MagicMock, patch

import pytest

from lfx.components.input_output.cdc_input import ETLCDCStreamInputComponent


class TestETLCDCStreamInputComponent:
    """Test cases for CDC Input component."""

    @pytest.fixture
    def component_class(self):
        """Return the component class to test."""
        return ETLCDCStreamInputComponent

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component instantiation."""
        return {
            "datasource_selector": "test_db (mysql)",
            "table_selector": "users",
            "cdc_mode": "时间戳模式",  # Use Chinese to test i18n
            "timestamp_column": "updated_at",
            "last_sync_time": "2024-01-01 00:00:00",
            "poll_interval_seconds": 5,
            "batch_size": 1000,
            "capture_deletes": True,
            "include_change_type": True,
            "primary_keys": "id",
        }

    @pytest.fixture
    def sample_datasources(self):
        """Sample datasources for API responses."""
        return [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "test_db",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "test_db",
                "username": "test_user",
                "status": "active",
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "prod_db",
                "type": "postgresql",
                "host": "prod-host",
                "port": 5432,
                "database": "production",
                "username": "prod_user",
                "status": "active",
            },
        ]

    @pytest.fixture
    def sample_tables(self):
        """Sample tables for API responses."""
        return ["users", "orders", "products", "categories"]

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_component_instantiation(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test component can be instantiated."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        assert component is not None
        assert component.name == "ETLCDCStreamInput"
        assert component.datasource_selector == "test_db (mysql)"
        assert component.table_selector == "users"
        assert mock_datasource_manager.called

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    @patch("lfx.components.input_output.cdc_input.httpx.Client")
    def test_update_build_config_load_datasources(
        self, mock_client, mock_datasource_manager, mock_i18n, component_class, default_kwargs, sample_datasources
    ):
        """Test loading datasources on initial configuration."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_datasources
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        component = component_class(**default_kwargs)
        build_config = {}

        # Test initial loading
        result = component.update_build_config(build_config, None, None)

        # Verify datasources were loaded
        assert "datasource_selector" in result
        assert len(result["datasource_selector"]["options"]) == 2
        assert "test_db (mysql)" in result["datasource_selector"]["options"]
        assert "prod_db (postgresql)" in result["datasource_selector"]["options"]
        assert "options_metadata" in result["datasource_selector"]
        assert len(result["datasource_selector"]["options_metadata"]) == 2

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_get_datasource_id_from_metadata(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test getting datasource ID from metadata."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)

        metadata = [
            {"id": "123e4567-e89b-12d3-a456-426614174000", "name": "test_db", "type": "mysql"},
            {"id": "123e4567-e89b-12d3-a456-426614174001", "name": "prod_db", "type": "postgresql"},
        ]

        # Test successful lookup
        datasource_id = component._get_datasource_id_from_metadata("test_db (mysql)", metadata)
        assert datasource_id == "123e4567-e89b-12d3-a456-426614174000"

        # Test not found
        datasource_id = component._get_datasource_id_from_metadata("unknown_db (mysql)", metadata)
        assert datasource_id is None

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_normalize_cdc_mode(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test CDC mode normalization."""
        mock_i18n.side_effect = lambda key, **kwargs: {
            "components.input_output.cdc_input.cdc_mode.timestamp": "时间戳模式",
            "components.input_output.cdc_input.cdc_mode.log_based": "日志模式",
            "components.input_output.cdc_input.cdc_mode.trigger_based": "触发器模式",
        }.get(key, key)

        component = component_class(**default_kwargs)

        # Test Chinese translations
        assert component._normalize_cdc_mode("时间戳模式") == "Timestamp"
        assert component._normalize_cdc_mode("日志模式") == "Log-Based"
        assert component._normalize_cdc_mode("触发器模式") == "Trigger-Based"

        # Test standard values
        assert component._normalize_cdc_mode("Timestamp") == "Timestamp"
        assert component._normalize_cdc_mode("Log-Based") == "Log-Based"
        assert component._normalize_cdc_mode("Trigger-Based") == "Trigger-Based"

        # Test variations
        assert component._normalize_cdc_mode("Timestamp-Based") == "Timestamp"
        assert component._normalize_cdc_mode("timestamp") == "Timestamp"
        assert component._normalize_cdc_mode("log_based") == "Log-Based"
        assert component._normalize_cdc_mode("trigger_based") == "Trigger-Based"

        # Test unknown value returns as-is
        assert component._normalize_cdc_mode("Unknown") == "Unknown"

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_format_i18n(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test i18n text formatting."""
        mock_i18n.return_value = "Error: {error} occurred in {context}"

        component = component_class(**default_kwargs)

        formatted = component._format_i18n("test.error", error="network timeout", context="database connection")
        assert formatted == "Error: network timeout occurred in database connection"

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    @patch("lfx.components.input_output.cdc_input.httpx.Client")
    def test_get_datasource_id(
        self, mock_client, mock_datasource_manager, mock_i18n, component_class, default_kwargs, sample_datasources
    ):
        """Test getting datasource ID from API."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_datasources
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        component = component_class(**default_kwargs)
        component.datasource_selector = "test_db (mysql)"

        datasource_id = component._get_datasource_id()
        assert datasource_id == "123e4567-e89b-12d3-a456-426614174000"

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    @patch("lfx.components.input_output.cdc_input.httpx.Client")
    def test_get_connection_string(
        self, mock_client, mock_datasource_manager, mock_i18n, component_class, default_kwargs
    ):
        """Test getting connection string from API."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"connection_string": "mysql+pymysql://user:pass@localhost:3306/test"}
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        component = component_class(**default_kwargs)

        connection_string = component._get_connection_string("test-datasource-id")
        assert connection_string == "mysql+pymysql://user:pass@localhost:3306/test"

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_get_datasource_id_missing_datasource(
        self, mock_datasource_manager, mock_i18n, component_class, default_kwargs
    ):
        """Test error when no datasource selected."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component.datasource_selector = None

        with pytest.raises(ValueError, match="No data source selected"):
            component._get_datasource_id()

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_capture_changes_missing_datasource(
        self, mock_datasource_manager, mock_i18n, component_class, default_kwargs
    ):
        """Test error handling when datasource is missing."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component.datasource_selector = None

        with pytest.raises(ValueError, match="No data source selected"):
            component.capture_changes()

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_capture_changes_missing_table(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test error handling when table is missing."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component.datasource_selector = "test_db (mysql)"
        component.table_selector = None

        with pytest.raises(ValueError, match="No table selected"):
            component.capture_changes()

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_capture_changes_invalid_mode(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test error handling for invalid CDC mode."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component.datasource_selector = "test_db (mysql)"
        component.table_selector = "users"
        component.cdc_mode = "InvalidMode"
        component._normalize_cdc_mode = MagicMock(return_value="InvalidMode")

        with pytest.raises(ValueError, match="Invalid CDC mode"):
            component.capture_changes()

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_capture_log_based_placeholder(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test log-based CDC returns placeholder."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component.cdc_mode = "Log-Based"

        results = component.capture_changes()

        assert len(results) == 1
        data = results[0].data
        assert "message" in data
        assert "log_based_requirement" in data["message"]
        assert data["table"] == "users"
        assert data["datasource"] == "test_db (mysql)"
        assert data["mode"] == "log-based"

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_get_change_summary_success(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test successful change summary generation."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component._normalize_cdc_mode = MagicMock(return_value="Timestamp")

        # Mock capture_changes to return some data
        from lfx.schema import Data

        with patch.object(component, "capture_changes") as mock_capture:
            mock_capture.return_value = [Data(data={"id": 1, "name": "Alice"}), Data(data={"id": 2, "name": "Bob"})]

            summary = component.get_change_summary()
            summary_data = summary.data

            assert summary_data["datasource"] == "test_db (mysql)"
            assert summary_data["table_name"] == "users"
            assert summary_data["cdc_mode"] == "Timestamp"
            assert summary_data["total_changes"] == 2
            assert "capture_time" in summary_data

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_get_change_summary_error(self, mock_datasource_manager, mock_i18n, component_class, default_kwargs):
        """Test change summary generation when capture fails."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)
        component._normalize_cdc_mode = MagicMock(return_value="Timestamp")

        # Mock capture_changes to raise an exception
        with patch.object(component, "capture_changes") as mock_capture:
            mock_capture.side_effect = Exception("Database connection failed")

            summary = component.get_change_summary()
            summary_data = summary.data

            assert summary_data["total_changes"] == 0
            assert "error" in summary_data
            assert "Database connection failed" in summary_data["error"]

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    def test_component_has_correct_properties(
        self, mock_datasource_manager, mock_i18n, component_class, default_kwargs
    ):
        """Test component has correct properties."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        component = component_class(**default_kwargs)

        # Verify component properties
        assert component.name == "ETLCDCStreamInput"
        assert component.icon == "database"
        assert hasattr(component, "datasource_manager")
        assert hasattr(component, "inputs")
        assert hasattr(component, "outputs")
        assert len(component.inputs) > 0
        assert len(component.outputs) > 0

    @patch("lfx.components.input_output.cdc_input.i18n.t")
    @patch("lfx.components.input_output.cdc_input.DataSourceManager")
    @patch("lfx.components.input_output.cdc_input.httpx.Client")
    def test_update_build_config_api_error(
        self, mock_client, mock_datasource_manager, mock_i18n, component_class, default_kwargs
    ):
        """Test error handling when API call fails."""
        mock_i18n.side_effect = lambda key, **kwargs: key

        # Mock API failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        component = component_class(**default_kwargs)
        build_config = {}

        # Should not raise exception, just log warning
        result = component.update_build_config(build_config, None, None)
        # Should not crash and should return empty options
        assert "datasource_selector" in result
        assert result["datasource_selector"]["options"] == []
