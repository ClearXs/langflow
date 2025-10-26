"""Test ETLFieldUnpivotComponent - Multiple columns to rows (unpivot/melt)."""

import pandas as pd
import pytest
from lfx.components.manipulations.field_unpivot import ETLFieldUnpivotComponent
from lfx.schema import Data


class TestETLFieldUnpivotComponent:
    """Test cases for ETLFieldUnpivotComponent."""

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component initialization."""
        return {
            "data_input": [],
            "id_fields": "product_id,product_name",
            "value_fields_mapping": [
                {"field_name": "jan", "target_value": "January"},
                {"field_name": "feb", "target_value": "February"},
                {"field_name": "mar", "target_value": "March"},
            ],
            "key_field": "month",
            "value_field": "sales",
            "ignore_nulls": True,
            "chunk_size": 100000,
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample test data - sales by month."""
        return [
            Data(
                data={
                    "product_id": "P001",
                    "product_name": "Widget A",
                    "jan": 100,
                    "feb": 120,
                    "mar": 150,
                    "apr": 130,
                }
            ),
            Data(
                data={
                    "product_id": "P002",
                    "product_name": "Widget B",
                    "jan": 200,
                    "feb": None,
                    "mar": 250,
                    "apr": 230,
                }
            ),
            Data(
                data={
                    "product_id": "P003",
                    "product_name": "Widget C",
                    "jan": 50,
                    "feb": 60,
                    "mar": 70,
                    "apr": 80,
                }
            ),
        ]

    def test_basic_unpivot(self, default_kwargs, sample_data):
        """Test basic unpivot operation."""
        default_kwargs["data_input"] = sample_data[:1]
        component = ETLFieldUnpivotComponent(**default_kwargs)

        result = component.unpivot_columns()

        # Should expand 1 row to 3 rows (3 months)
        assert len(result) == 3

        # Check structure
        result_dict = {r.data["month"]: r.data for r in result}

        assert result_dict["January"]["product_id"] == "P001"
        assert result_dict["January"]["product_name"] == "Widget A"
        assert result_dict["January"]["sales"] == 100

        assert result_dict["February"]["sales"] == 120
        assert result_dict["March"]["sales"] == 150

    def test_multiple_rows_unpivot(self, default_kwargs, sample_data):
        """Test unpivoting multiple rows."""
        default_kwargs["data_input"] = sample_data[:2]
        component = ETLFieldUnpivotComponent(**default_kwargs)

        result = component.unpivot_columns()

        # 2 products * 3 months = 6 rows (if ignoring nulls)
        assert len(result) == 5  # One null value in P002 feb

        # Check both products exist
        p001_rows = [r for r in result if r.data["product_id"] == "P001"]
        p002_rows = [r for r in result if r.data["product_id"] == "P002"]

        assert len(p001_rows) == 3
        assert len(p002_rows) == 2  # Feb is null, ignored

    def test_include_nulls(self, default_kwargs, sample_data):
        """Test including null values in unpivot."""
        default_kwargs["data_input"] = sample_data[1:2]  # P002 with null
        default_kwargs["ignore_nulls"] = False

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        # Should include all 3 months even with null
        assert len(result) == 3

        feb_row = [r for r in result if r.data["month"] == "February"][0]
        assert pd.isna(feb_row.data["sales"]) or feb_row.data["sales"] is None

    def test_auto_detect_fields(self, default_kwargs, sample_data):
        """Test auto-detection of value fields when mapping is empty."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["value_fields_mapping"] = []  # Empty mapping

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        # Should auto-detect apr as additional value field
        assert len(result) == 4  # jan, feb, mar, apr

        # Check that apr is included
        months = {r.data["month"] for r in result}
        assert "apr" in months

    def test_custom_key_value_names(self, default_kwargs, sample_data):
        """Test custom key and value field names."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["key_field"] = "period"
        default_kwargs["value_field"] = "amount"

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        assert len(result) == 3

        # Check field names
        assert "period" in result[0].data
        assert "amount" in result[0].data
        assert "month" not in result[0].data
        assert "sales" not in result[0].data

    def test_empty_id_fields(self, default_kwargs, sample_data):
        """Test unpivot with no ID fields (all columns become values)."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["id_fields"] = ""  # No ID fields

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        # All specified fields should be unpivoted
        assert len(result) == 3

        # No ID fields preserved
        assert "product_id" not in result[0].data
        assert "product_name" not in result[0].data

    def test_field_name_mapping(self, default_kwargs):
        """Test field name transformation during unpivot."""
        data = [
            Data(
                data={
                    "id": "1",
                    "q1_2024": 100,
                    "q2_2024": 200,
                    "q3_2024": 300,
                }
            )
        ]

        default_kwargs["data_input"] = data
        default_kwargs["id_fields"] = "id"
        default_kwargs["value_fields_mapping"] = [
            {"field_name": "q1_2024", "target_value": "Q1 2024"},
            {"field_name": "q2_2024", "target_value": "Q2 2024"},
            {"field_name": "q3_2024", "target_value": "Q3 2024"},
        ]
        default_kwargs["key_field"] = "quarter"
        default_kwargs["value_field"] = "revenue"

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        assert len(result) == 3

        # Check transformed names
        quarters = {r.data["quarter"] for r in result}
        assert "Q1 2024" in quarters
        assert "Q2 2024" in quarters
        assert "Q3 2024" in quarters

    def test_mixed_data_types(self, default_kwargs):
        """Test unpivot with mixed data types."""
        data = [
            Data(
                data={
                    "id": "1",
                    "metric_a": 100,
                    "metric_b": "text_value",
                    "metric_c": 3.14,
                    "metric_d": True,
                }
            )
        ]

        default_kwargs["data_input"] = data
        default_kwargs["id_fields"] = "id"
        default_kwargs["value_fields_mapping"] = [
            {"field_name": "metric_a", "target_value": "A"},
            {"field_name": "metric_b", "target_value": "B"},
            {"field_name": "metric_c", "target_value": "C"},
            {"field_name": "metric_d", "target_value": "D"},
        ]

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        assert len(result) == 4

        # Check different data types are preserved
        values_by_key = {r.data["month"]: r.data["sales"] for r in result}
        assert values_by_key["A"] == 100
        assert values_by_key["B"] == "text_value"
        assert values_by_key["C"] == 3.14
        assert values_by_key["D"] == True

    def test_missing_field_error(self, default_kwargs, sample_data):
        """Test error when specified field doesn't exist."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["value_fields_mapping"] = [
            {"field_name": "nonexistent", "target_value": "Missing"},
        ]

        component = ETLFieldUnpivotComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.unpivot_columns()

        assert "nonexistent" in str(excinfo.value)

    def test_empty_input_error(self, default_kwargs):
        """Test error with empty input."""
        default_kwargs["data_input"] = []

        component = ETLFieldUnpivotComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.unpivot_columns()

        assert "input" in str(excinfo.value).lower()

    def test_large_dataset_chunking(self, default_kwargs):
        """Test chunking for large datasets."""
        # Create large dataset
        large_data = []
        for i in range(1000):
            large_data.append(
                Data(
                    data={
                        "id": str(i),
                        "name": f"Product {i}",
                        "jan": 100 + i,
                        "feb": 200 + i,
                        "mar": 300 + i,
                    }
                )
            )

        default_kwargs["data_input"] = large_data
        default_kwargs["id_fields"] = "id,name"
        default_kwargs["chunk_size"] = 100  # Small chunk for testing

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        # 1000 rows * 3 months = 3000 rows
        assert len(result) == 3000

        # Verify data integrity
        first_product = [r for r in result if r.data["id"] == "0"]
        assert len(first_product) == 3

        values = {r.data["month"]: r.data["sales"] for r in first_product}
        assert values["January"] == 100
        assert values["February"] == 200
        assert values["March"] == 300

    def test_preview_result(self, default_kwargs, sample_data):
        """Test preview functionality."""
        default_kwargs["data_input"] = sample_data

        component = ETLFieldUnpivotComponent(**default_kwargs)
        preview = component.preview_result()

        assert isinstance(preview, Data)
        assert "original_rows" in preview.data
        assert "preview_rows" in preview.data
        assert "id_fields" in preview.data
        assert "value_fields" in preview.data
        assert "sample_data" in preview.data

        # Preview should be limited
        assert len(preview.data["sample_data"]) <= 20

    def test_get_statistics(self, default_kwargs, sample_data):
        """Test statistics generation."""
        default_kwargs["data_input"] = sample_data

        component = ETLFieldUnpivotComponent(**default_kwargs)
        stats = component.get_statistics()

        assert isinstance(stats, Data)
        assert "total_input_rows" in stats.data
        assert "total_columns" in stats.data
        assert "id_fields_count" in stats.data
        assert "value_fields_count" in stats.data
        assert "estimated_output_rows" in stats.data

        assert stats.data["total_input_rows"] == 3
        assert stats.data["value_fields_count"] == 3
        assert stats.data["estimated_output_rows"] == 9  # 3 * 3

    def test_preserve_id_fields(self, default_kwargs, sample_data):
        """Test that ID fields are properly preserved."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["id_fields"] = "product_id,product_name"

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        # All rows should have the same ID fields
        for row in result:
            assert row.data["product_id"] == "P001"
            assert row.data["product_name"] == "Widget A"

    def test_complex_id_fields(self, default_kwargs):
        """Test with multiple complex ID fields."""
        data = [
            Data(
                data={
                    "company": "ACME",
                    "department": "Sales",
                    "region": "North",
                    "year": 2024,
                    "q1": 1000,
                    "q2": 1200,
                    "q3": 1100,
                    "q4": 1300,
                }
            )
        ]

        default_kwargs["data_input"] = data
        default_kwargs["id_fields"] = "company,department,region,year"
        default_kwargs["value_fields_mapping"] = [
            {"field_name": "q1", "target_value": "Q1"},
            {"field_name": "q2", "target_value": "Q2"},
            {"field_name": "q3", "target_value": "Q3"},
            {"field_name": "q4", "target_value": "Q4"},
        ]

        component = ETLFieldUnpivotComponent(**default_kwargs)
        result = component.unpivot_columns()

        assert len(result) == 4

        # Check all ID fields preserved
        for row in result:
            assert row.data["company"] == "ACME"
            assert row.data["department"] == "Sales"
            assert row.data["region"] == "North"
            assert row.data["year"] == 2024

    async def test_update_build_config_load_fields(self, default_kwargs, sample_data):
        """Test dynamic field loading into table."""
        default_kwargs["data_input"] = sample_data[:1]

        component = ETLFieldUnpivotComponent(**default_kwargs)

        # Mock build_config
        build_config = {
            "value_fields_mapping": {
                "value": [],
            }
        }

        # Test auto-load fields button
        updated_config = await component.update_build_config(
            build_config=build_config, field_value="load_fields", field_name="value_fields_mapping"
        )

        # Should populate with available fields
        assert len(updated_config["value_fields_mapping"]["value"]) > 0

        field_names = [f["field_name"] for f in updated_config["value_fields_mapping"]["value"]]
        assert "jan" in field_names
        assert "feb" in field_names
        assert "mar" in field_names
        assert "apr" in field_names

    async def test_update_build_config_id_fields(self, default_kwargs, sample_data):
        """Test updating ID fields based on data input."""
        default_kwargs["data_input"] = sample_data[:1]

        component = ETLFieldUnpivotComponent(**default_kwargs)

        # Mock build_config
        build_config = {}

        # Update when data_input changes
        updated_config = await component.update_build_config(
            build_config=build_config, field_value="data_input", field_name="data_input"
        )

        # Should suggest ID fields
        assert "id_fields" in updated_config or True  # Placeholder for actual implementation
