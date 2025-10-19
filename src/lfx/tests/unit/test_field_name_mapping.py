"""Unit tests for ETLFieldNameMappingComponent."""

import pytest

from lfx.components.manipulations.field_name_mapping import ETLFieldNameMappingComponent
from lfx.schema import Data


class TestETLFieldNameMappingComponent:
    """Test suite for Field Name Mapping component."""

    def test_basic_field_mapping(self):
        """Test basic field name mapping functionality."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John", "age": "25"}),
                Data(data={"id": "2", "name": "Jane", "age": "30"}),
            ],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "user_id",
                    "description": "User identifier",
                },
                {
                    "source_field": "name",
                    "target_field": "user_name",
                    "description": "User full name",
                },
                {
                    "source_field": "age",
                    "target_field": "user_age",
                    "description": "User age in years",
                },
            ],
        )

        result = component.map_field_names()

        assert len(result) == 2
        # Check first record
        assert result[0].data["user_id"] == "1"
        assert result[0].data["user_name"] == "John"
        assert result[0].data["user_age"] == "25"
        # Check second record
        assert result[1].data["user_id"] == "2"
        assert result[1].data["user_name"] == "Jane"
        assert result[1].data["user_age"] == "30"

    def test_partial_field_mapping(self):
        """Test mapping only some fields, keeping others unchanged."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John", "age": "25", "city": "NYC"}),
            ],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "user_id",
                    "description": "",
                },
                {
                    "source_field": "name",
                    "target_field": "user_name",
                    "description": "",
                },
            ],
        )

        result = component.map_field_names()

        assert len(result) == 1
        assert result[0].data["user_id"] == "1"
        assert result[0].data["user_name"] == "John"
        # Unmapped fields should be preserved with original names
        assert result[0].data["age"] == "25"
        assert result[0].data["city"] == "NYC"

    def test_same_source_and_target_field(self):
        """Test when source and target field names are the same."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John"}),
            ],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "id",  # Same as source
                    "description": "Keep same name",
                },
                {
                    "source_field": "name",
                    "target_field": "full_name",
                    "description": "Rename to full_name",
                },
            ],
        )

        result = component.map_field_names()

        assert len(result) == 1
        assert result[0].data["id"] == "1"
        assert result[0].data["full_name"] == "John"
        assert "name" not in result[0].data  # Original name should be removed

    def test_empty_field_mappings(self):
        """Test with empty field mappings list raises error."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John"}),
            ],
            field_mappings=[],
        )

        # Empty mappings should raise ValueError
        with pytest.raises(ValueError):
            component.map_field_names()

    def test_empty_data_input(self):
        """Test with empty data input raises error."""
        component = ETLFieldNameMappingComponent(
            data_input=[],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "user_id",
                    "description": "",
                },
            ],
        )

        # Empty data input should raise ValueError
        with pytest.raises(ValueError):
            component.map_field_names()

    def test_missing_source_field_in_data(self):
        """Test when a source field in mapping doesn't exist in data raises error."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John"}),  # age missing
            ],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "user_id",
                    "description": "",
                },
                {
                    "source_field": "age",  # This field doesn't exist
                    "target_field": "user_age",
                    "description": "",
                },
            ],
        )

        # Missing source field should raise ValueError
        with pytest.raises(ValueError):
            component.map_field_names()

    def test_multiple_records_with_different_fields(self):
        """Test mapping multiple records - all must have the same required fields."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John", "age": "25"}),
                Data(data={"id": "2", "name": "Jane", "age": "30"}),
                Data(data={"id": "3", "name": "Bob", "age": "35", "city": "LA"}),
            ],
            field_mappings=[
                {
                    "source_field": "id",
                    "target_field": "user_id",
                    "description": "",
                },
                {
                    "source_field": "name",
                    "target_field": "user_name",
                    "description": "",
                },
                {
                    "source_field": "age",
                    "target_field": "user_age",
                    "description": "",
                },
            ],
        )

        result = component.map_field_names()

        assert len(result) == 3
        # First record
        assert result[0].data["user_id"] == "1"
        assert result[0].data["user_name"] == "John"
        assert result[0].data["user_age"] == "25"
        # Second record
        assert result[1].data["user_id"] == "2"
        assert result[1].data["user_name"] == "Jane"
        assert result[1].data["user_age"] == "30"
        # Third record - has extra city field
        assert result[2].data["user_id"] == "3"
        assert result[2].data["user_name"] == "Bob"
        assert result[2].data["user_age"] == "35"
        assert result[2].data["city"] == "LA"  # Unmapped field preserved

    def test_extract_field_mappings_helper(self):
        """Test the _extract_field_mappings helper method."""
        component = ETLFieldNameMappingComponent(
            data_input=[],
            field_mappings=[],
        )

        # Test with sample data
        sample_data = [
            Data(data={"id": "1", "name": "John", "age": "25"}),
        ]

        field_mappings = component._extract_field_mappings(sample_data)

        assert len(field_mappings) == 3
        assert any(fm["source_field"] == "id" for fm in field_mappings)
        assert any(fm["source_field"] == "name" for fm in field_mappings)
        assert any(fm["source_field"] == "age" for fm in field_mappings)

        # All should have same target_field as source_field by default
        for fm in field_mappings:
            assert fm["source_field"] == fm["target_field"]
            assert fm["description"] == ""

    def test_extract_field_mappings_with_empty_data(self):
        """Test _extract_field_mappings with empty data list."""
        component = ETLFieldNameMappingComponent(
            data_input=[],
            field_mappings=[],
        )

        field_mappings = component._extract_field_mappings([])

        assert field_mappings == []

    def test_extract_field_mappings_with_non_dict_data(self):
        """Test _extract_field_mappings handles non-dict data gracefully."""
        component = ETLFieldNameMappingComponent(
            data_input=[],
            field_mappings=[],
        )

        # Create Data object with dict that contains non-dict value
        # Since Data validates that data must be a dict, we need to test
        # when the dict contains unexpected nested structure
        sample_data = [Data(data={"value": "some string"})]

        # This should work - extracts field 'value'
        field_mappings = component._extract_field_mappings(sample_data)

        assert len(field_mappings) == 1
        assert field_mappings[0]["source_field"] == "value"

    @pytest.mark.asyncio
    async def test_update_build_config_no_action(self):
        """Test update_build_config without action (no-op)."""
        component = ETLFieldNameMappingComponent(
            data_input=[],
            field_mappings=[],
        )

        build_config = {
            "field_mappings": {
                "value": [],
            },
        }

        result = await component.update_build_config(
            build_config=build_config,
            field_value=None,
            field_name="some_field",
            action=None,
        )

        # Should return unchanged
        assert result == build_config

    def test_complex_field_mapping_scenario(self):
        """Test complex real-world scenario with database field mapping."""
        component = ETLFieldNameMappingComponent(
            data_input=[
                Data(
                    data={
                        "user_id": "1001",
                        "first_name": "John",
                        "last_name": "Doe",
                        "email_address": "john@example.com",
                        "phone_number": "+1234567890",
                        "created_at": "2024-01-01",
                        "is_active": "1",
                    }
                ),
            ],
            field_mappings=[
                {"source_field": "user_id", "target_field": "id", "description": "Primary key"},
                {"source_field": "first_name", "target_field": "firstName", "description": "User's first name"},
                {"source_field": "last_name", "target_field": "lastName", "description": "User's last name"},
                {"source_field": "email_address", "target_field": "email", "description": "Contact email"},
                {"source_field": "phone_number", "target_field": "phone", "description": "Contact phone"},
                {"source_field": "created_at", "target_field": "createdAt", "description": "Registration date"},
                {"source_field": "is_active", "target_field": "active", "description": "Account status"},
            ],
        )

        result = component.map_field_names()

        assert len(result) == 1
        record = result[0].data

        # Check all fields are correctly mapped
        assert record["id"] == "1001"
        assert record["firstName"] == "John"
        assert record["lastName"] == "Doe"
        assert record["email"] == "john@example.com"
        assert record["phone"] == "+1234567890"
        assert record["createdAt"] == "2024-01-01"
        assert record["active"] == "1"

        # Original field names should not be present
        assert "user_id" not in record
        assert "first_name" not in record
        assert "last_name" not in record
        assert "email_address" not in record
        assert "phone_number" not in record
        assert "created_at" not in record
        assert "is_active" not in record
