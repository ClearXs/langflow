"""Unit tests for ETLQualityModelComponent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lfx.components.quality.quality_model import ETLQualityModelComponent
from lfx.schema import Data


@pytest.fixture
def mock_feign_service():
    """Mock FeignService for testing."""
    service = AsyncMock()
    return service


@pytest.fixture
def sample_quality_models():
    """Sample quality model list from API."""
    return [
        {"id": 1, "name": "Data Completeness Check", "status": 1},
        {"id": 2, "name": "Data Accuracy Validation", "status": 1},
        {"id": 3, "name": "Data Consistency Test", "status": 1},
    ]


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        Data(data={"field1": "value1", "field2": 100}),
        Data(data={"field1": "value2", "field2": 200}),
        Data(data={"field1": "value3", "field2": 300}),
    ]


class TestETLQualityModelComponent:
    """Test ETLQualityModelComponent."""

    def test_component_initialization(self):
        """Test component can be initialized."""
        component = ETLQualityModelComponent()
        assert component.display_name is not None
        assert component.description is not None
        assert component.icon == "shield-check"
        assert component.name == "ETLQualityModel"

    def test_component_has_required_inputs(self):
        """Test component has all required inputs."""
        component = ETLQualityModelComponent()
        input_names = [input_field.name for input_field in component.inputs]
        assert "data_input" in input_names
        assert "quality_model_config" in input_names
        assert "auto_evaluate" in input_names

    def test_component_has_required_outputs(self):
        """Test component has all required outputs."""
        component = ETLQualityModelComponent()
        output_names = [output.name for output in component.outputs]
        assert "data" in output_names
        assert "quality_result" in output_names

    def test_transform_models_to_config(self, sample_quality_models):
        """Test transforming API models to table config format."""
        component = ETLQualityModelComponent()
        result = component._transform_models_to_config(sample_quality_models)

        assert len(result) == 3
        assert result[0]["model_id"] == 1
        assert result[0]["model_name"] == "Data Completeness Check"
        assert result[0]["enabled"] is False

    def test_transform_models_empty_list(self):
        """Test transforming empty model list."""
        component = ETLQualityModelComponent()
        result = component._transform_models_to_config([])
        assert result == []

    def test_transform_models_missing_id(self):
        """Test transforming models with missing ID."""
        component = ETLQualityModelComponent()
        models = [{"name": "Model A"}, {"id": 2, "name": "Model B"}]
        result = component._transform_models_to_config(models)

        # Should skip model without ID
        assert len(result) == 1
        assert result[0]["model_id"] == 2

    @pytest.mark.asyncio
    async def test_update_build_config_load_models_success(self, mock_feign_service, sample_quality_models):
        """Test loading quality models via action button."""
        component = ETLQualityModelComponent()
        build_config = {"quality_model_config": {"value": []}}

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 200, "data": sample_quality_models}
        mock_feign_service.get.return_value = mock_response

        with patch("lfx.services.deps.get_feign_service", return_value=mock_feign_service):
            result = await component.update_build_config(
                build_config=build_config, field_value=None, field_name="quality_model_config", action="load_models"
            )

        # Verify models were loaded
        assert len(result["quality_model_config"]["value"]) == 3
        assert result["quality_model_config"]["value"][0]["model_id"] == 1
        assert result["quality_model_config"]["value"][0]["model_name"] == "Data Completeness Check"

    @pytest.mark.asyncio
    async def test_update_build_config_load_models_empty(self, mock_feign_service):
        """Test loading quality models when API returns empty list."""
        component = ETLQualityModelComponent()
        build_config = {"quality_model_config": {"value": []}}

        # Mock API response with empty data
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 200, "data": []}
        mock_feign_service.get.return_value = mock_response

        with patch("lfx.services.deps.get_feign_service", return_value=mock_feign_service):
            result = await component.update_build_config(
                build_config=build_config, field_value=None, field_name="quality_model_config", action="load_models"
            )

        # Verify no models were added
        assert result["quality_model_config"]["value"] == []

    @pytest.mark.asyncio
    async def test_update_build_config_api_error(self, mock_feign_service):
        """Test handling API errors when loading models."""
        component = ETLQualityModelComponent()
        build_config = {"quality_model_config": {"value": []}}

        # Mock API error
        mock_feign_service.get.side_effect = ValueError("API connection failed")

        with patch("lfx.services.deps.get_feign_service", return_value=mock_feign_service):
            result = await component.update_build_config(
                build_config=build_config, field_value=None, field_name="quality_model_config", action="load_models"
            )

        # Should return original config on error
        assert result["quality_model_config"]["value"] == []

    def test_process_data_pass_through(self, sample_data):
        """Test process_data returns input data unchanged (pass-through)."""
        component = ETLQualityModelComponent()
        component.data_input = sample_data

        result = component.process_data()

        assert len(result) == 3
        assert result == sample_data

    def test_process_data_missing_input(self):
        """Test process_data raises error when data input is missing."""
        component = ETLQualityModelComponent()
        component.data_input = None

        with pytest.raises(ValueError):
            component.process_data()

    @pytest.mark.asyncio
    async def test_evaluate_quality_reserved_feature(self, sample_data):
        """Test evaluate_quality returns placeholder result (reserved feature)."""
        component = ETLQualityModelComponent()
        component.data_input = sample_data
        component.quality_model_config = [
            {"model_id": 1, "model_name": "Model A", "enabled": True},
            {"model_id": 2, "model_name": "Model B", "enabled": False},
        ]

        result = await component.evaluate_quality()

        assert isinstance(result, Data)
        assert result.data["status"] == "reserved"
        assert result.data["total_records"] == 3
        assert "Model A" in result.data["enabled_models"]
        assert "Model B" not in result.data["enabled_models"]

    @pytest.mark.asyncio
    async def test_evaluate_quality_no_enabled_models(self, sample_data):
        """Test evaluate_quality when no models are enabled."""
        component = ETLQualityModelComponent()
        component.data_input = sample_data
        component.quality_model_config = [
            {"model_id": 1, "model_name": "Model A", "enabled": False},
        ]

        result = await component.evaluate_quality()

        assert isinstance(result, Data)
        assert result.data["status"] == "no_models_enabled"

    @pytest.mark.asyncio
    async def test_evaluate_quality_missing_config(self):
        """Test evaluate_quality raises error when config is missing."""
        component = ETLQualityModelComponent()
        component.data_input = None
        component.quality_model_config = None

        with pytest.raises(ValueError):
            await component.evaluate_quality()


class TestQualityModelIntegration:
    """Integration tests for quality model workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_load_and_process(self, mock_feign_service, sample_quality_models, sample_data):
        """Test complete workflow: load models, configure, and process data."""
        component = ETLQualityModelComponent()
        component.data_input = sample_data

        # Step 1: Load models via action button
        build_config = {"quality_model_config": {"value": []}}
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 200, "data": sample_quality_models}
        mock_feign_service.get.return_value = mock_response

        with patch("lfx.services.deps.get_feign_service", return_value=mock_feign_service):
            updated_config = await component.update_build_config(
                build_config=build_config, field_value=None, field_name="quality_model_config", action="load_models"
            )

        # Step 2: Simulate user enabling a model
        component.quality_model_config = updated_config["quality_model_config"]["value"]
        component.quality_model_config[0]["enabled"] = True

        # Step 3: Process data
        result = component.process_data()
        assert len(result) == 3

        # Step 4: Evaluate quality (placeholder)
        quality_result = await component.evaluate_quality()
        assert quality_result.data["status"] == "reserved"
