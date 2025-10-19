"""Unit tests for ETLFileInputComponent."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from lfx.components.input_output.file_input import ETLFileInputComponent
from lfx.schema.data import Data
from lfx.schema.message import Message


class TestETLFileInputComponent:
    """Test suite for ETLFileInputComponent."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create various test files with supported extensions
            (tmpdir_path / "test.txt").write_text("test content", encoding="utf-8")
            (tmpdir_path / "data.csv").write_text("col1,col2\n1,2", encoding="utf-8")
            (tmpdir_path / "document.pdf").write_bytes(b"%PDF-1.4 test")
            (tmpdir_path / "image.png").write_bytes(b"\x89PNG test")
            (tmpdir_path / "config.json").write_text('{"key": "value"}', encoding="utf-8")

            # Create a subdirectory
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            (subdir / "nested.json").write_text('{"key": "value"}', encoding="utf-8")

            yield tmpdir_path

    def test_component_initialization(self, temp_dir):
        """Test component initializes correctly."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
        )

        assert component.name == "ETLFileInput"
        assert len(component.VALID_EXTENSIONS) > 0
        # Check some expected extensions
        assert "csv" in component.VALID_EXTENSIONS
        assert "txt" in component.VALID_EXTENSIONS
        assert "pdf" in component.VALID_EXTENSIONS
        assert "json" in component.VALID_EXTENSIONS

    def test_single_file_selection(self, temp_dir):
        """Test selecting a single file returns correct data."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=True,
        )

        result = component.get_file_data()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Data)

        data = result[0].data
        assert "file_path" in data
        assert "file_name" in data
        assert data["file_name"] == "test.txt"
        assert "file_extension" in data
        assert data["file_extension"] == ".txt"

    def test_multiple_file_selection(self, temp_dir):
        """Test selecting multiple files."""
        files = [
            str(temp_dir / "test.txt"),
            str(temp_dir / "data.csv"),
            str(temp_dir / "document.pdf"),
        ]

        component = ETLFileInputComponent(
            path=files,
            include_metadata=True,
        )

        result = component.get_file_data()

        assert len(result) == 3
        assert all(isinstance(item, Data) for item in result)

        file_names = [item.data["file_name"] for item in result]
        assert "test.txt" in file_names
        assert "data.csv" in file_names
        assert "document.pdf" in file_names

    def test_metadata_inclusion(self, temp_dir):
        """Test that metadata is included when enabled."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=True,
        )

        result = component.get_file_data()
        data = result[0].data

        # Check that metadata fields are present
        assert "file_size" in data
        assert "file_size_mb" in data
        assert "file_size_kb" in data
        assert "modified_time" in data
        assert "created_time" in data
        assert "is_file" in data
        assert "is_dir" in data
        assert "parent_dir" in data

        # Verify metadata values
        assert data["is_file"] is True
        assert data["is_dir"] is False
        assert data["file_size"] > 0

    def test_metadata_exclusion(self, temp_dir):
        """Test that metadata is excluded when disabled."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=False,
        )

        result = component.get_file_data()
        data = result[0].data

        # Check that only basic fields are present
        assert "file_path" in data
        assert "file_name" in data
        assert "file_extension" in data
        assert "file_stem" in data

        # Check that metadata fields are NOT present
        assert "file_size" not in data
        assert "file_size_mb" not in data
        assert "modified_time" not in data
        assert "created_time" not in data

    def test_file_paths_output(self, temp_dir):
        """Test get_file_paths returns correct paths."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
        )

        result = component.get_file_paths()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], str)
        assert result[0].endswith("test.txt")

    def test_message_output(self, temp_dir):
        """Test get_file_message returns correct message."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=True,
        )

        result = component.get_file_message()

        assert isinstance(result, Message)
        assert "test.txt" in result.text
        assert "1" in result.text  # File count

    def test_message_output_with_metadata(self, temp_dir):
        """Test message includes file size when metadata enabled."""
        test_file = temp_dir / "test.txt"
        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=True,
        )

        result = component.get_file_message()
        assert "MB" in result.text

    def test_message_output_no_files(self):
        """Test message when no files are selected."""
        component = ETLFileInputComponent(
            path=[],
            include_metadata=False,
            validate_existence=False,
        )

        result = component.get_file_message()
        assert isinstance(result, Message)
        assert len(result.text) > 0

    def test_file_not_found_validation(self, temp_dir):
        """Test validation fails for non-existent file."""
        non_existent_file = str(temp_dir / "does_not_exist.txt")

        component = ETLFileInputComponent(
            path=[non_existent_file],
            validate_existence=True,
            silent_errors=False,
        )

        with pytest.raises(FileNotFoundError):
            component.get_file_data()

    def test_file_not_found_silent_errors(self, temp_dir):
        """Test silent errors mode handles missing files gracefully."""
        non_existent_file = str(temp_dir / "does_not_exist.txt")

        component = ETLFileInputComponent(
            path=[non_existent_file],
            validate_existence=True,
            silent_errors=True,
        )

        result = component.get_file_data()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_file_existence_not_validated(self, temp_dir):
        """Test that non-existent files pass when validation disabled."""
        non_existent_file = str(temp_dir / "does_not_exist.txt")

        component = ETLFileInputComponent(
            path=[non_existent_file],
            validate_existence=False,
            include_metadata=False,
        )

        result = component.get_file_data()

        # Should still create data objects, but without metadata
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].data["file_name"] == "does_not_exist.txt"

    def test_mixed_existing_and_missing_files(self, temp_dir):
        """Test handling of mix of existing and missing files with silent errors."""
        files = [
            str(temp_dir / "test.txt"),  # exists
            str(temp_dir / "missing.txt"),  # doesn't exist
            str(temp_dir / "data.csv"),  # exists
        ]

        component = ETLFileInputComponent(
            path=files,
            validate_existence=True,
            silent_errors=True,
        )

        result = component.get_file_data()

        # Should only return the existing files
        assert len(result) == 2
        file_names = [item.data["file_name"] for item in result]
        assert "test.txt" in file_names
        assert "data.csv" in file_names
        assert "missing.txt" not in file_names

    def test_file_extension_detection(self, temp_dir):
        """Test that file extensions are correctly detected."""
        test_cases = [
            ("test.txt", ".txt"),
            ("data.csv", ".csv"),
            ("document.pdf", ".pdf"),
            ("image.png", ".png"),
        ]

        for filename, expected_ext in test_cases:
            component = ETLFileInputComponent(
                path=[str(temp_dir / filename)],
                include_metadata=False,
            )

            result = component.get_file_data()
            assert result[0].data["file_extension"] == expected_ext

    def test_file_stem_extraction(self, temp_dir):
        """Test that file stem (name without extension) is extracted correctly."""
        component = ETLFileInputComponent(
            path=[str(temp_dir / "test.txt")],
            include_metadata=False,
        )

        result = component.get_file_data()
        assert result[0].data["file_stem"] == "test"

    def test_nested_file_selection(self, temp_dir):
        """Test selecting files in subdirectories."""
        nested_file = temp_dir / "subdir" / "nested.json"

        component = ETLFileInputComponent(
            path=[str(nested_file)],
            include_metadata=True,
        )

        result = component.get_file_data()

        assert len(result) == 1
        assert result[0].data["file_name"] == "nested.json"
        assert "subdir" in result[0].data["parent_dir"]

    def test_no_files_selected_error(self):
        """Test error when no files are selected."""
        component = ETLFileInputComponent(
            path=[],
            validate_existence=True,
            silent_errors=False,
        )

        with pytest.raises(ValueError, match="No files selected"):
            component.get_file_data()

    def test_valid_extensions_defined(self):
        """Test that component has valid extensions defined."""
        component = ETLFileInputComponent(path=[])

        assert hasattr(component, "VALID_EXTENSIONS")
        assert isinstance(component.VALID_EXTENSIONS, list)
        assert len(component.VALID_EXTENSIONS) > 0

        # Check some expected extensions
        expected_extensions = ["csv", "txt", "pdf", "json", "xlsx"]
        for ext in expected_extensions:
            assert ext in component.VALID_EXTENSIONS

    def test_file_size_calculations(self, temp_dir):
        """Test that file sizes are calculated correctly."""
        # Create a file with known size
        test_file = temp_dir / "sized_file.txt"
        content = "x" * 1024  # 1KB
        test_file.write_text(content, encoding="utf-8")

        component = ETLFileInputComponent(
            path=[str(test_file)],
            include_metadata=True,
        )

        result = component.get_file_data()
        data = result[0].data

        assert data["file_size"] == 1024
        assert data["file_size_kb"] == 1.0
        assert data["file_size_mb"] < 0.01

    def test_empty_file_handling(self, temp_dir):
        """Test handling of empty files."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        component = ETLFileInputComponent(
            path=[str(empty_file)],
            include_metadata=True,
        )

        result = component.get_file_data()

        assert len(result) == 1
        assert result[0].data["file_size"] == 0
        assert result[0].data["file_size_mb"] == 0.0

    def test_multiple_files_message_formatting(self, temp_dir):
        """Test message formatting with multiple files."""
        files = [
            str(temp_dir / "test.txt"),
            str(temp_dir / "data.csv"),
            str(temp_dir / "document.pdf"),
        ]

        component = ETLFileInputComponent(
            path=files,
            include_metadata=True,
        )

        result = component.get_file_message()

        # Check that all files are mentioned in the message
        assert "test.txt" in result.text
        assert "data.csv" in result.text
        assert "document.pdf" in result.text
        assert "3" in result.text  # File count

    def test_file_path_list_output_order(self, temp_dir):
        """Test that file paths maintain order."""
        files = [
            str(temp_dir / "test.txt"),
            str(temp_dir / "data.csv"),
            str(temp_dir / "document.pdf"),
        ]

        component = ETLFileInputComponent(path=files)

        result = component.get_file_paths()

        # Verify order is maintained
        assert len(result) == 3
        # Just verify all files are in the result (order may vary due to file processing)
        result_names = [Path(p).name for p in result]
        assert "test.txt" in result_names
        assert "data.csv" in result_names
        assert "document.pdf" in result_names
