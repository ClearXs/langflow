"""Integration test for ETLTableInput component."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from lfx.components.input_output.table_input import ETLTableInputComponent
from lfx.schema import Data


class TestETLTableInputComponent:
    """Test ETL Table Input component."""

    @pytest.fixture
    def component(self):
        """Create component instance."""
        component = ETLTableInputComponent()
        # Set required attributes
        component.datasource_selector = "test_datasource"
        component.table_name = "test_table"
        component.sql_query = "SELECT * FROM test_table"
        component.use_pagination = False
        component.max_records = 0
        component.enable_transaction = False
        component.isolation_level = "DEFAULT"
        component.field_mappings = []
        component.page_size = 1000
        component.log = Mock()
        component.status = ""
        return component

    @pytest.mark.asyncio
    async def test_update_build_config_initial_load(self, component):
        """Test initial configuration loading."""
        build_config = {
            "datasource_selector": {"options": []},
            "table_name": {"options": []},
            "sql_query": {"value": ""},
            "field_mappings": {"table_schema": []},
        }

        # Mock datasource manager
        with patch.object(component.datasource_manager, "get_datasources") as mock_get_ds:
            mock_get_ds.return_value = {
                "enterprise": [{"id": "ent_1", "name": "Production DB", "type": "mysql"}],
                "custom": [{"id": "cust_1", "name": "Test DB", "type": "postgresql"}],
            }

            result = await component.update_build_config(build_config, None, None)

            # Check datasources were loaded
            assert len(result["datasource_selector"]["options"]) > 0
            mock_get_ds.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_build_config_datasource_selected(self, component):
        """Test table loading when datasource is selected."""
        build_config = {
            "table_name": {"options": [], "value": ""},
            "sql_query": {"value": ""},
            "field_mappings": {"table_schema": []},
        }

        with patch.object(component.datasource_manager, "get_tables") as mock_get_tables:
            mock_get_tables.return_value = ["users", "products", "orders"]

            result = await component.update_build_config(build_config, "test_datasource", "datasource_selector")

            # Check tables were loaded
            assert len(result["table_name"]["options"]) == 3
            assert result["table_name"]["value"] == ""
            mock_get_tables.assert_called_once_with("test_datasource")

    @pytest.mark.asyncio
    async def test_update_build_config_table_selected(self, component):
        """Test column loading when table is selected."""
        build_config = {
            "sql_query": {"value": ""},
            "field_mappings": {"table_schema": [{"name": "source_field", "options": []}]},
        }

        with patch.object(component.datasource_manager, "get_columns") as mock_get_cols:
            mock_get_cols.return_value = [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "varchar"},
                {"name": "email", "type": "varchar"},
            ]

            result = await component.update_build_config(build_config, "users", "table_name")

            # Check columns were loaded
            schema = result["field_mappings"]["table_schema"]
            source_field_schema = next((s for s in schema if s["name"] == "source_field"), None)
            assert source_field_schema is not None
            assert len(source_field_schema["options"]) == 3

            # Check SQL was generated
            assert result["sql_query"]["value"] == "SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_extract_data_with_transformation(self, component):
        """Test data extraction with field transformations."""
        # Mock data
        test_data = pd.DataFrame(
            [
                {"id": 1, "name": "john doe", "email": "john@example.com", "age": "25"},
                {"id": 2, "name": "jane smith", "email": "jane@example.com", "age": "30"},
            ]
        )

        # Configure field mappings
        component.field_mappings = [
            {
                "source_field": "name",
                "target_field": "full_name",
                "transformation_rule": "upper",
                "data_type": "string",
                "enabled": True,
            },
            {
                "source_field": "email",
                "target_field": "masked_email",
                "transformation_rule": "mask_email",
                "data_type": "string",
                "enabled": True,
            },
            {
                "source_field": "age",
                "target_field": "user_age",
                "transformation_rule": "to_int",
                "data_type": "integer",
                "enabled": True,
            },
        ]

        # Mock database connection
        with patch.object(component.datasource_manager, "_get_datasource_by_id") as mock_get_ds:
            mock_get_ds.return_value = {"connection_string": "sqlite:///:memory:"}

            with patch("pandas.read_sql_query") as mock_read_sql:
                mock_read_sql.return_value = test_data

                # Execute
                result = await component.extract_data()

                # Verify results
                assert len(result) == 2
                assert isinstance(result[0], Data)

                # Check first record transformations
                first_record = result[0].data
                assert first_record["full_name"] == "JOHN DOE"
                assert "***" in first_record["masked_email"]
                assert first_record["user_age"] == 25

                # Check second record
                second_record = result[1].data
                assert second_record["full_name"] == "JANE SMITH"
                assert "***" in second_record["masked_email"]
                assert second_record["user_age"] == 30

    @pytest.mark.asyncio
    async def test_extract_data_with_pagination(self, component):
        """Test data extraction with pagination."""
        component.use_pagination = True
        component.page_size = 2

        # Mock data for multiple pages
        page1_data = pd.DataFrame([{"id": 1, "name": "user1"}, {"id": 2, "name": "user2"}])
        page2_data = pd.DataFrame([{"id": 3, "name": "user3"}])
        empty_data = pd.DataFrame()

        with patch.object(component.datasource_manager, "_get_datasource_by_id") as mock_get_ds:
            mock_get_ds.return_value = {"connection_string": "sqlite:///:memory:"}

            with patch("pandas.read_sql_query") as mock_read_sql:
                # Return different data for each call
                mock_read_sql.side_effect = [page1_data, page2_data, empty_data]

                result = await component.extract_data()

                # Should have all 3 records
                assert len(result) == 3
                assert result[0].data["name"] == "user1"
                assert result[1].data["name"] == "user2"
                assert result[2].data["name"] == "user3"

                # Check pagination queries were made
                assert mock_read_sql.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_data_with_max_records(self, component):
        """Test data extraction with max records limit."""
        component.max_records = 2

        test_data = pd.DataFrame(
            [
                {"id": 1, "name": "user1"},
                {"id": 2, "name": "user2"},
                {"id": 3, "name": "user3"},
                {"id": 4, "name": "user4"},
            ]
        )

        with patch.object(component.datasource_manager, "_get_datasource_by_id") as mock_get_ds:
            mock_get_ds.return_value = {"connection_string": "sqlite:///:memory:"}

            with patch("pandas.read_sql_query") as mock_read_sql:
                mock_read_sql.return_value = test_data

                result = await component.extract_data()

                # Should only have 2 records due to max_records
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_row_count(self, component):
        """Test row count output."""
        test_data = pd.DataFrame([{"id": 1, "name": "user1"}, {"id": 2, "name": "user2"}])

        with patch.object(component.datasource_manager, "_get_datasource_by_id") as mock_get_ds:
            mock_get_ds.return_value = {"connection_string": "sqlite:///:memory:"}

            with patch("pandas.read_sql_query") as mock_read_sql:
                mock_read_sql.return_value = test_data

                result = await component.get_row_count()

                assert isinstance(result, Data)
                assert result.data["row_count"] == 2
                assert result.data["table"] == "test_table"

    @pytest.mark.asyncio
    async def test_error_handling(self, component):
        """Test error handling."""
        # Test missing datasource
        component.datasource_selector = None
        with pytest.raises(ValueError) as exc_info:
            await component.extract_data()
        assert "missing_config" in str(exc_info.value).lower()

        # Test invalid datasource
        component.datasource_selector = "invalid_ds"
        with patch.object(component.datasource_manager, "_get_datasource_by_id") as mock_get_ds:
            mock_get_ds.return_value = None
            with pytest.raises(ValueError) as exc_info:
                await component.extract_data()
            assert "invalid_datasource" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
