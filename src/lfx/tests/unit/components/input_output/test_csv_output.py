"""Unit tests for ETLCSVOutputComponent."""

from unittest.mock import patch

import pytest

from lfx.components.input_output.csv_output import ETLCSVOutputComponent
from lfx.schema import Data


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        Data(data={"name": "Alice", "age": 30, "city": "Beijing"}),
        Data(data={"name": "Bob", "age": 25, "city": "Shanghai"}),
        Data(data={"name": "Charlie", "age": 35, "city": "Guangzhou"}),
    ]


@pytest.fixture
def component_config():
    """Component configuration."""
    return {
        "filename": "test_output.csv",
        "delimiter": ",",
        "encoding": "utf-8",
        "include_header": True,
    }


class TestETLCSVOutputComponent:
    """Test cases for CSV output component."""

    @pytest.mark.asyncio
    async def test_export_csv_success(self, sample_data, component_config):
        """Test successful CSV export and upload."""
        with patch("lfx.components.input_output.csv_output.upload_file_to_folder") as mock_upload:
            # Mock upload response
            mock_upload.return_value = {"id": 456, "name": "test_output.csv", "path": "/Test/Folder/test_output.csv"}

            # Create component
            component = ETLCSVOutputComponent(data_input=sample_data, output_folder="123", **component_config)

            # Mock _parameters to simulate FileInput
            component._parameters = {"output_folder": {"file_path": "123"}}

            # Execute export
            result = await component.export_to_csv()

            # Verify result
            assert result.data["success"] is True
            assert result.data["file_id"] == 456
            assert result.data["rows_exported"] == 3
            assert result.data["file_name"] == "test_output.csv"
            assert result.data["folder_id"] == "123"

            # Verify upload was called
            mock_upload.assert_called_once()
            call_args = mock_upload.call_args
            assert call_args.kwargs["folder_id"] == 123
            assert call_args.kwargs["filename"] == "test_output.csv"

    @pytest.mark.asyncio
    async def test_export_csv_no_data(self, component_config):
        """Test export with no data raises error."""
        component = ETLCSVOutputComponent(data_input=[], output_folder="123", **component_config)

        component._parameters = {"output_folder": {"file_path": "123"}}

        with pytest.raises(ValueError, match="no_data|没有提供要导出的数据"):
            await component.export_to_csv()

    @pytest.mark.asyncio
    async def test_export_csv_no_folder_selected(self, sample_data, component_config):
        """Test export with no folder selected raises error."""
        component = ETLCSVOutputComponent(data_input=sample_data, output_folder="", **component_config)

        component._parameters = {"output_folder": {"file_path": ""}}

        with pytest.raises(ValueError, match="no_folder_selected|请选择目标文件夹"):
            await component.export_to_csv()

    @pytest.mark.asyncio
    async def test_export_csv_upload_failure(self, sample_data, component_config):
        """Test handling of upload failure."""
        with patch("lfx.components.input_output.csv_output.upload_file_to_folder") as mock_upload:
            mock_upload.side_effect = ValueError("Upload failed (code=500): Network error")

            component = ETLCSVOutputComponent(data_input=sample_data, output_folder="123", **component_config)

            component._parameters = {"output_folder": {"file_path": "123"}}

            with pytest.raises(ValueError, match="ValueError"):
                await component.export_to_csv()

    @pytest.mark.asyncio
    async def test_export_csv_custom_delimiter(self, sample_data):
        """Test CSV export with custom delimiter."""
        config = {"filename": "test.csv", "delimiter": ";", "encoding": "utf-8", "include_header": True}

        with patch("lfx.components.input_output.csv_output.upload_file_to_folder") as mock_upload:
            mock_upload.return_value = {"id": 789}

            component = ETLCSVOutputComponent(data_input=sample_data, output_folder="123", **config)

            component._parameters = {"output_folder": {"file_path": "123"}}

            result = await component.export_to_csv()
            assert result.data["delimiter"] == ";"

    @pytest.mark.asyncio
    async def test_temp_file_cleanup(self, sample_data, component_config):
        """Test that temporary files are cleaned up."""
        with patch("lfx.components.input_output.csv_output.upload_file_to_folder") as mock_upload:
            mock_upload.return_value = {"id": 999}

            with patch("lfx.components.input_output.csv_output.cleanup_temp_file") as mock_cleanup:
                component = ETLCSVOutputComponent(data_input=sample_data, output_folder="123", **component_config)

                component._parameters = {"output_folder": {"file_path": "123"}}

                await component.export_to_csv()

                # Verify cleanup was called
                mock_cleanup.assert_called_once()
                temp_path = mock_cleanup.call_args[0][0]
                assert temp_path is not None
                assert "lfx_csv_output_" in temp_path
