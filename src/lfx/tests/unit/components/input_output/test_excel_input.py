"""Unit tests for ETLExcelInputComponent."""

import pandas as pd
import pytest

from lfx.components.input_output.excel_input import (
    HEADER_MODE_CUSTOM_ROW,
    HEADER_MODE_FIRST_ROW,
    HEADER_MODE_NO_HEADER,
    ETLExcelInputComponent,
)
from lfx.schema import Data


class TestETLExcelInputComponent:
    """Test cases for Excel Input component."""

    @pytest.fixture
    def sample_excel_file(self, tmp_path):
        """Create a sample Excel file for testing."""
        df = pd.DataFrame({"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35], "City": ["NYC", "LA", "Chicago"]})
        file_path = tmp_path / "test.xlsx"
        df.to_excel(file_path, index=False, engine="openpyxl")
        return str(file_path)

    @pytest.fixture
    def multi_sheet_excel_file(self, tmp_path):
        """Create an Excel file with multiple sheets."""
        file_path = tmp_path / "multi_sheet.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            pd.DataFrame({"A": [1, 2, 3]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"B": [4, 5, 6]}).to_excel(writer, sheet_name="Sheet2", index=False)
        return str(file_path)

    def test_load_basic_excel(self, sample_excel_file):
        """Test basic Excel file loading."""
        component = ETLExcelInputComponent(
            file_path=sample_excel_file, sheet_index=0, header_mode=HEADER_MODE_FIRST_ROW, data_start_row=2
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert isinstance(data_list[0], Data)
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[1].data["Age"] == 30
        assert data_list[2].data["City"] == "Chicago"

    def test_load_second_sheet(self, multi_sheet_excel_file):
        """Test loading data from the second sheet."""
        component = ETLExcelInputComponent(
            file_path=multi_sheet_excel_file,
            sheet_index=1,  # Second sheet
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert "B" in data_list[0].data
        assert data_list[0].data["B"] == 4
        assert data_list[2].data["B"] == 6

    def test_no_header_mode(self, sample_excel_file):
        """Test reading with no header mode (use column identifiers)."""
        component = ETLExcelInputComponent(
            file_path=sample_excel_file, sheet_index=0, header_mode=HEADER_MODE_NO_HEADER, data_start_row=1
        )

        data_list = component.load_data()

        # Should have 4 rows (including the header row as data)
        assert len(data_list) == 4
        # Column names should be A, B, C
        assert "A" in data_list[0].data
        assert "B" in data_list[0].data
        assert "C" in data_list[0].data
        # First row should be the original header
        assert data_list[0].data["A"] == "Name"
        assert data_list[0].data["B"] == "Age"
        assert data_list[0].data["C"] == "City"

    def test_max_rows_limit(self, sample_excel_file):
        """Test max rows limitation."""
        component = ETLExcelInputComponent(
            file_path=sample_excel_file,
            sheet_index=0,
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
            max_rows=2,  # Limit to 2 rows
        )

        data_list = component.load_data()

        assert len(data_list) == 2
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[1].data["Name"] == "Bob"

    def test_custom_header_row(self, tmp_path):
        """Test using custom row as header."""
        # Create Excel with header in row 2
        file_path = tmp_path / "custom_header.xlsx"
        df = pd.DataFrame([["Title Line"], ["Name", "Age", "City"], ["Alice", 25, "NYC"], ["Bob", 30, "LA"]])
        df.to_excel(file_path, index=False, header=False, engine="openpyxl")

        component = ETLExcelInputComponent(
            file_path=str(file_path),
            sheet_index=0,
            header_mode=HEADER_MODE_CUSTOM_ROW,
            header_row=2,  # Second row is header
            data_start_row=3,  # Data starts from row 3
        )

        data_list = component.load_data()

        assert len(data_list) == 2
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[1].data["Age"] == 30

    def test_excel_column_name_generation(self):
        """Test Excel column name generation (A, B, ..., Z, AA, AB, ...)."""
        component = ETLExcelInputComponent(file_path="dummy")

        assert component._get_excel_column_name(0) == "A"
        assert component._get_excel_column_name(1) == "B"
        assert component._get_excel_column_name(25) == "Z"
        assert component._get_excel_column_name(26) == "AA"
        assert component._get_excel_column_name(27) == "AB"

    def test_empty_cells_as_none(self, tmp_path):
        """Test that empty cells are converted to None."""
        file_path = tmp_path / "with_empty.xlsx"
        df = pd.DataFrame({"Name": ["Alice", None, "Charlie"], "Age": [25, 30, None]})
        df.to_excel(file_path, index=False, engine="openpyxl")

        component = ETLExcelInputComponent(
            file_path=str(file_path), header_mode=HEADER_MODE_FIRST_ROW, data_start_row=2
        )

        data_list = component.load_data()

        assert data_list[1].data["Name"] is None
        assert data_list[2].data["Age"] is None

    def test_missing_file_error(self):
        """Test error when file doesn't exist."""
        component = ETLExcelInputComponent(file_path="/nonexistent/file.xlsx", header_mode=HEADER_MODE_FIRST_ROW)

        with pytest.raises(ValueError):
            component.load_data()

    def test_no_file_path_error(self):
        """Test error when file_path is not provided."""
        component = ETLExcelInputComponent(file_path="", header_mode=HEADER_MODE_FIRST_ROW)

        with pytest.raises(ValueError):
            component.load_data()

    async def test_preview_update_build_config(self, sample_excel_file):
        """Test preview functionality through update_build_config."""
        component = ETLExcelInputComponent(
            file_path=sample_excel_file,
            sheet_index=0,
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        build_config = {
            "file_path": {"value": sample_excel_file},
            "sheet_index": {"value": 0},
            "header_mode": {"value": HEADER_MODE_FIRST_ROW},
            "header_row": {"value": 1},
            "data_start_row": {"value": 2},
            "preview_table": {"table_schema": [], "value": []},
        }

        # Simulate clicking preview button
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="preview_table", action="preview_excel"
        )

        # Verify preview data is populated
        assert len(updated_config["preview_table"]["value"]) == 3
        assert len(updated_config["preview_table"]["table_schema"]) == 3
        assert updated_config["preview_table"]["table_schema"][0]["name"] == "Name"
        assert updated_config["preview_table"]["value"][0]["Name"] == "Alice"

    async def test_conditional_header_row_visibility(self):
        """Test that header_row field visibility changes based on header_mode."""
        component = ETLExcelInputComponent(file_path="dummy")

        build_config = {"header_row": {"show": True}}

        # When header_mode is not custom_row, header_row should be hidden
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=HEADER_MODE_FIRST_ROW, field_name="header_mode"
        )

        assert updated_config["header_row"]["show"] is False

        # When header_mode is custom_row, header_row should be shown
        build_config["header_row"]["show"] = False
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=HEADER_MODE_CUSTOM_ROW, field_name="header_mode"
        )

        assert updated_config["header_row"]["show"] is True

    def test_data_start_row_skip(self, sample_excel_file):
        """Test skipping rows with data_start_row."""
        component = ETLExcelInputComponent(
            file_path=sample_excel_file,
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=3,  # Skip first data row
        )

        data_list = component.load_data()

        # Should only have 2 rows (skipped Alice)
        assert len(data_list) == 2
        assert data_list[0].data["Name"] == "Bob"
        assert data_list[1].data["Name"] == "Charlie"
