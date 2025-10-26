"""Integration tests for ETLDataCleaningComponent with other input components."""

from lfx.components.manipulations.data_cleaning import ETLDataCleaningComponent
from lfx.schema import Data


class TestDataCleaningIntegration:
    """Integration tests for Data Cleaning component."""

    def test_integration_with_mock_data(self):
        """Test data cleaning with mock upstream data."""
        # Simulate data from TableInput/CSVInput/ExcelInput
        upstream_data = [
            Data(data={"name": "  john  ", "email": "test@example.com", "phone": "13812345678", "age": 25}),
            Data(data={"name": "  jane  ", "email": "admin@company.org", "phone": "13987654321", "age": 30}),
            Data(data={"name": "  bob  ", "email": "bob@test.com", "phone": "13711112222", "age": 20}),
        ]

        # Apply data cleaning
        cleaner = ETLDataCleaningComponent(
            data_input=upstream_data,
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "trim", "custom_expression": ""},
                {"field_name": "email", "transformation_rule": "mask_email", "custom_expression": ""},
                {"field_name": "phone", "transformation_rule": "mask_phone", "custom_expression": ""},
            ],
            filter_conditions=[{"field_name": "age", "operator": ">=", "compare_value": "25", "logic_operator": "AND"}],
            max_records=0,
        )

        result = cleaner.clean_data()

        assert len(result) == 3

        # John and Jane meet the filter (age >= 25)
        assert result[0].data["name"] == "john"
        assert result[0].data["email"] == "t***t@example.com"
        assert result[0].data["phone"] == "138****5678"

        assert result[1].data["name"] == "jane"
        assert result[1].data["email"] == "a***n@company.org"
        assert result[1].data["phone"] == "139****4321"

        # Bob doesn't meet the filter (age < 25), data unchanged
        assert result[2].data["name"] == "  bob  "  # Still has spaces
        assert result[2].data["email"] == "bob@test.com"  # Not masked
        assert result[2].data["phone"] == "13711112222"  # Not masked

    def test_cascade_data_transformations(self):
        """Test cascading multiple data cleaning operations."""
        # First stage: Initial data
        initial_data = [
            Data(data={"raw_text": "  HELLO WORLD  ", "category": "test"}),
            Data(data={"raw_text": "  GOODBYE  ", "category": "prod"}),
        ]

        # First cleaning stage: trim and lowercase
        stage1 = ETLDataCleaningComponent(
            data_input=initial_data,
            cleaning_rules=[
                {"field_name": "raw_text", "transformation_rule": "trim", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        stage1_result = stage1.clean_data()

        # Second cleaning stage: lowercase on trimmed data
        stage2 = ETLDataCleaningComponent(
            data_input=stage1_result,
            cleaning_rules=[
                {"field_name": "raw_text", "transformation_rule": "lower", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        stage2_result = stage2.clean_data()

        assert len(stage2_result) == 2
        assert stage2_result[0].data["raw_text"] == "hello world"
        assert stage2_result[1].data["raw_text"] == "goodbye"

    def test_data_quality_pipeline(self):
        """Test a complete data quality pipeline."""
        # Simulate raw data with quality issues
        raw_data = [
            Data(data={"name": "  John Doe  ", "email": "john@example.com", "age": "25", "status": "active"}),
            Data(data={"name": "Jane Smith", "email": "jane@test.com", "age": "invalid", "status": "inactive"}),
            Data(data={"name": "  Bob  ", "email": "bob@company.org", "age": "30", "status": "active"}),
        ]

        # Stage 1: Clean and normalize
        cleaner = ETLDataCleaningComponent(
            data_input=raw_data,
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "trim", "custom_expression": ""},
                {"field_name": "age", "transformation_rule": "to_int", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        cleaned_data = cleaner.clean_data()

        # Stage 2: Filter and mask sensitive data
        privacy_filter = ETLDataCleaningComponent(
            data_input=cleaned_data,
            cleaning_rules=[
                {"field_name": "email", "transformation_rule": "mask_email", "custom_expression": ""},
            ],
            filter_conditions=[
                {"field_name": "status", "operator": "=", "compare_value": "active", "logic_operator": "AND"}
            ],
            max_records=0,
        )
        final_data = privacy_filter.clean_data()

        assert len(final_data) == 3

        # John: active, should be masked
        assert final_data[0].data["name"] == "John Doe"
        assert final_data[0].data["email"] == "j***n@example.com"
        assert final_data[0].data["age"] == 25

        # Jane: inactive, should not be masked
        assert final_data[1].data["name"] == "Jane Smith"
        assert final_data[1].data["email"] == "jane@test.com"
        assert final_data[1].data["age"] is None  # Invalid age converted to None

        # Bob: active, should be masked
        assert final_data[2].data["name"] == "Bob"
        assert final_data[2].data["email"] == "b***b@company.org"
        assert final_data[2].data["age"] == 30

    def test_selective_field_cleaning(self):
        """Test cleaning only specific fields while preserving others."""
        data = [
            Data(
                data={
                    "id": "001",
                    "sensitive_name": "John Doe",
                    "public_name": "John",
                    "ssn": "123-45-6789",
                    "description": "Test user",
                }
            ),
        ]

        cleaner = ETLDataCleaningComponent(
            data_input=data,
            cleaning_rules=[
                # Only clean sensitive fields
                {"field_name": "sensitive_name", "transformation_rule": "mask_name", "custom_expression": ""},
                {"field_name": "ssn", "transformation_rule": "md5", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )

        result = cleaner.clean_data()

        assert len(result) == 1
        # Cleaned fields - mask_name keeps first and last char
        assert result[0].data["sensitive_name"] == "J******e"  # "John Doe" -> "J******e"
        assert len(result[0].data["ssn"]) == 32  # MD5 hash

        # Preserved fields
        assert result[0].data["id"] == "001"
        assert result[0].data["public_name"] == "John"
        assert result[0].data["description"] == "Test user"

    def test_batch_processing_with_max_records(self):
        """Test batch processing with max_records limit."""
        # Generate large dataset
        large_dataset = [Data(data={"id": i, "value": f"item_{i}", "category": "A"}) for i in range(100)]

        # Process in batches of 30
        batch_size = 30
        all_results = []

        for batch_start in range(0, 100, batch_size):
            batch_data = large_dataset[batch_start : batch_start + batch_size]

            cleaner = ETLDataCleaningComponent(
                data_input=batch_data,
                cleaning_rules=[
                    {"field_name": "value", "transformation_rule": "upper", "custom_expression": ""},
                ],
                filter_conditions=[],
                max_records=0,  # Process all in this batch
            )

            batch_result = cleaner.clean_data()
            all_results.extend(batch_result)

        assert len(all_results) == 100
        # All values should be uppercase
        for result in all_results:
            assert result.data["value"].startswith("ITEM_")

    def test_error_recovery_in_pipeline(self):
        """Test that pipeline continues even if some transformations fail."""
        data = [
            Data(data={"name": "John", "value": "valid"}),
            Data(data={"name": "Jane", "value": "also_valid"}),
        ]

        cleaner = ETLDataCleaningComponent(
            data_input=data,
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
                # This field doesn't exist, but should not crash
                {"field_name": "nonexistent", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )

        # Should not raise error
        result = cleaner.clean_data()

        assert len(result) == 2
        assert result[0].data["name"] == "JOHN"
        assert result[1].data["name"] == "JANE"
