"""Unit tests for ETLCSVInputComponent."""

import pandas as pd
import pytest

from lfx.components.input_output.csv_input import (
    DELIMITER_COMMA,
    DELIMITER_CUSTOM,
    DELIMITER_SEMICOLON,
    DELIMITER_TAB,
    ENCODING_AUTO,
    HEADER_MODE_FIRST_ROW,
    HEADER_MODE_NO_HEADER,
    ETLCSVInputComponent,
)
from lfx.schema import Data


class TestETLCSVInputComponent:
    """Test cases for CSV Input component."""

    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file for testing."""
        df = pd.DataFrame({"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35], "City": ["NYC", "LA", "Chicago"]})
        file_path = tmp_path / "test.csv"
        df.to_csv(file_path, index=False)
        return str(file_path)

    @pytest.fixture
    def semicolon_csv_file(self, tmp_path):
        """Create a CSV file with semicolon delimiter."""
        df = pd.DataFrame({"Product": ["Apple", "Banana", "Orange"], "Price": [1.2, 0.8, 1.5]})
        file_path = tmp_path / "semicolon.csv"
        df.to_csv(file_path, index=False, sep=";")
        return str(file_path)

    @pytest.fixture
    def tab_csv_file(self, tmp_path):
        """Create a tab-delimited file."""
        df = pd.DataFrame({"ID": [1, 2, 3], "Value": [10, 20, 30]})
        file_path = tmp_path / "tab.tsv"
        df.to_csv(file_path, index=False, sep="\t")
        return str(file_path)

    @pytest.fixture
    def gbk_csv_file(self, tmp_path):
        """Create a GBK encoded CSV file."""
        df = pd.DataFrame({"姓名": ["张三", "李四", "王五"], "年龄": [25, 30, 35]})
        file_path = tmp_path / "gbk.csv"
        df.to_csv(file_path, index=False, encoding="gbk")
        return str(file_path)

    def test_load_basic_csv(self, sample_csv_file):
        """Test basic CSV file loading."""
        component = ETLCSVInputComponent(
            file_path=sample_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert isinstance(data_list[0], Data)
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[1].data["Age"] == 30
        assert data_list[2].data["City"] == "Chicago"

    def test_semicolon_delimiter(self, semicolon_csv_file):
        """Test reading CSV with semicolon delimiter."""
        component = ETLCSVInputComponent(
            file_path=semicolon_csv_file,
            delimiter=DELIMITER_SEMICOLON,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert data_list[0].data["Product"] == "Apple"
        assert data_list[1].data["Price"] == 0.8

    def test_tab_delimiter(self, tab_csv_file):
        """Test reading tab-delimited file."""
        component = ETLCSVInputComponent(
            file_path=tab_csv_file,
            delimiter=DELIMITER_TAB,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert data_list[0].data["ID"] == 1
        assert data_list[2].data["Value"] == 30

    def test_custom_delimiter(self, tmp_path):
        """Test reading CSV with custom delimiter."""
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        file_path = tmp_path / "custom.csv"
        df.to_csv(file_path, index=False, sep="|")

        component = ETLCSVInputComponent(
            file_path=str(file_path),
            delimiter=DELIMITER_CUSTOM,
            custom_delimiter="|",
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert data_list[0].data["A"] == 1
        assert data_list[1].data["B"] == 5

    def test_gbk_encoding(self, gbk_csv_file):
        """Test reading GBK encoded CSV file."""
        component = ETLCSVInputComponent(
            file_path=gbk_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="gbk",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 3
        assert data_list[0].data["姓名"] == "张三"
        assert data_list[1].data["年龄"] == 30

    def test_auto_encoding_detection(self, gbk_csv_file):
        """Test automatic encoding detection."""
        component = ETLCSVInputComponent(
            file_path=gbk_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding=ENCODING_AUTO,
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        # Should successfully read despite auto-detection
        assert len(data_list) == 3
        assert "姓名" in data_list[0].data

    def test_no_header_mode(self, sample_csv_file):
        """Test reading with no header mode."""
        component = ETLCSVInputComponent(
            file_path=sample_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_NO_HEADER,
            data_start_row=1,
        )

        data_list = component.load_data()

        # Should have 4 rows (including the header row as data)
        assert len(data_list) == 4
        # Column names should be Column_1, Column_2, Column_3
        assert "Column_1" in data_list[0].data
        assert "Column_2" in data_list[0].data
        assert "Column_3" in data_list[0].data
        # First row should be the original header
        assert data_list[0].data["Column_1"] == "Name"

    def test_max_rows_limit(self, sample_csv_file):
        """Test max rows limitation."""
        component = ETLCSVInputComponent(
            file_path=sample_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
            max_rows=2,
        )

        data_list = component.load_data()

        assert len(data_list) == 2
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[1].data["Name"] == "Bob"

    def test_skip_blank_lines(self, tmp_path):
        """Test skipping blank lines."""
        file_path = tmp_path / "with_blanks.csv"
        with open(file_path, "w") as f:
            f.write("Name,Age\n")
            f.write("Alice,25\n")
            f.write("\n")  # Blank line
            f.write("Bob,30\n")
            f.write("\n")  # Blank line
            f.write("Charlie,35\n")

        component = ETLCSVInputComponent(
            file_path=str(file_path),
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
            skip_blank_lines=True,
        )

        data_list = component.load_data()

        # Should have only 3 rows (blank lines skipped)
        assert len(data_list) == 3
        assert data_list[0].data["Name"] == "Alice"
        assert data_list[2].data["Name"] == "Charlie"

    def test_empty_cells_as_none(self, tmp_path):
        """Test that empty cells are converted to None."""
        file_path = tmp_path / "with_empty.csv"
        df = pd.DataFrame(
            {
                "Name": ["Alice", None, "Charlie"],
                "Age": [25, 30, None],
            }
        )
        df.to_csv(file_path, index=False)

        component = ETLCSVInputComponent(
            file_path=str(file_path),
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        data_list = component.load_data()

        assert data_list[1].data["Name"] is None
        assert data_list[2].data["Age"] is None

    def test_missing_file_error(self):
        """Test error when file doesn't exist."""
        component = ETLCSVInputComponent(
            file_path="/nonexistent/file.csv",
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
        )

        with pytest.raises(ValueError):
            component.load_data()

    def test_no_file_path_error(self):
        """Test error when file_path is not provided."""
        component = ETLCSVInputComponent(
            file_path="",
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
        )

        with pytest.raises(ValueError):
            component.load_data()

    async def test_preview_update_build_config(self, sample_csv_file):
        """Test preview functionality through update_build_config."""
        component = ETLCSVInputComponent(
            file_path=sample_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=2,
        )

        build_config = {
            "file_path": {"value": sample_csv_file},
            "delimiter": {"value": DELIMITER_COMMA},
            "custom_delimiter": {"value": ""},
            "encoding": {"value": "utf-8"},
            "header_mode": {"value": HEADER_MODE_FIRST_ROW},
            "header_row": {"value": 1},
            "data_start_row": {"value": 2},
            "skip_blank_lines": {"value": True},
            "preview_table": {"table_schema": [], "value": []},
        }

        # Simulate clicking preview button
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="preview_table", action="preview_csv"
        )

        # Verify preview data is populated
        assert len(updated_config["preview_table"]["value"]) == 3
        assert len(updated_config["preview_table"]["table_schema"]) == 3
        assert updated_config["preview_table"]["table_schema"][0]["name"] == "Name"
        assert updated_config["preview_table"]["value"][0]["Name"] == "Alice"

    async def test_conditional_fields_visibility(self):
        """Test conditional field visibility for delimiter and header_mode."""
        component = ETLCSVInputComponent(file_path="dummy")

        build_config = {
            "custom_delimiter": {"show": True},
            "header_row": {"show": True},
        }

        # Test delimiter conditional
        updated_config = await component.update_build_config(
            build_config=build_config,
            field_value=DELIMITER_COMMA,
            field_name="delimiter",
        )
        assert updated_config["custom_delimiter"]["show"] is False

        build_config["custom_delimiter"]["show"] = False
        updated_config = await component.update_build_config(
            build_config=build_config,
            field_value=DELIMITER_CUSTOM,
            field_name="delimiter",
        )
        assert updated_config["custom_delimiter"]["show"] is True

        # Test header_mode conditional
        build_config = {"header_row": {"show": True}}
        updated_config = await component.update_build_config(
            build_config=build_config,
            field_value=HEADER_MODE_FIRST_ROW,
            field_name="header_mode",
        )
        assert updated_config["header_row"]["show"] is False

    def test_data_start_row_skip(self, sample_csv_file):
        """Test skipping rows with data_start_row."""
        component = ETLCSVInputComponent(
            file_path=sample_csv_file,
            delimiter=DELIMITER_COMMA,
            encoding="utf-8",
            header_mode=HEADER_MODE_FIRST_ROW,
            data_start_row=3,  # Skip first data row
        )

        data_list = component.load_data()

        # Should only have 2 rows (skipped Alice)
        assert len(data_list) == 2
        assert data_list[0].data["Name"] == "Bob"
        assert data_list[1].data["Name"] == "Charlie"
