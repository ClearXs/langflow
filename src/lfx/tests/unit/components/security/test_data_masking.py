"""Unit tests for ETLDataMaskingComponent."""

from unittest.mock import AsyncMock, patch

import pytest

from lfx.components.security.data_masking import ETLDataMaskingComponent
from lfx.schema import Data


@pytest.fixture
def component():
    """Create ETLDataMaskingComponent instance."""
    return ETLDataMaskingComponent()


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return [
        Data(data={"name": "张三", "phone": "13800138000", "email": "zhang@example.com"}),
        Data(data={"name": "李四", "phone": "13900139000", "email": "li@example.com"}),
        Data(data={"name": "王五", "phone": "13700137000", "email": None}),  # Null value test
    ]


@pytest.fixture
def mock_data_security_client():
    """Create mock data security client."""
    client = AsyncMock()
    # Mock batch masking
    client.test_rule_batch.return_value = ["masked_1", "masked_2", "masked_3"]
    return client


class TestETLDataMaskingComponent:
    """Test cases for ETLDataMaskingComponent."""

    @pytest.mark.asyncio
    async def test_mask_data_single_field(self, component, sample_data, mock_data_security_client):
        """Test masking of a single field."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        # Mock the client
        mock_data_security_client.test_rule_batch.return_value = [
            "138****8000",
            "139****9000",
            "137****7000"
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify results
        assert len(result) == 3
        assert result[0].data["phone"] == "138****8000"
        assert result[1].data["phone"] == "139****9000"
        assert result[2].data["phone"] == "137****7000"

        # Other fields should remain unchanged
        assert result[0].data["name"] == "张三"
        assert result[0].data["email"] == "zhang@example.com"

        # Verify client was called correctly
        mock_data_security_client.test_rule_batch.assert_called_once_with(
            10, ["13800138000", "13900139000", "13700137000"]
        )

    @pytest.mark.asyncio
    async def test_mask_data_multiple_fields(self, component, sample_data, mock_data_security_client):
        """Test masking of multiple fields."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [
            {"field": "phone", "rule_id": 10},
            {"field": "email", "rule_id": 11}
        ]

        # Setup mock responses for different calls
        mock_data_security_client.test_rule_batch.side_effect = [
            ["138****8000", "139****9000", "137****7000"],  # First call for phone
            ["zh***@example.com", "li***@example.com"]       # Second call for email (skip null)
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify results
        assert len(result) == 3
        assert result[0].data["phone"] == "138****8000"
        assert result[0].data["email"] == "zh***@example.com"
        assert result[1].data["phone"] == "139****9000"
        assert result[1].data["email"] == "li***@example.com"
        assert result[2].data["phone"] == "137****7000"
        assert result[2].data["email"] is None  # Remains null

        # Verify client calls
        assert mock_data_security_client.test_rule_batch.call_count == 2
        mock_data_security_client.test_rule_batch.assert_any_call(10, ["13800138000", "13900139000", "13700137000"])
        mock_data_security_client.test_rule_batch.assert_any_call(11, ["zhang@example.com", "li@example.com"])

    @pytest.mark.asyncio
    async def test_mask_data_field_not_found(self, component, sample_data, mock_data_security_client):
        """Test handling of field not found in data."""
        # Setup component with non-existent field
        component.data_input = sample_data
        component.masking_rules = [{"field": "non_existent_field", "rule_id": 10}]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify data remains unchanged
        assert len(result) == 3
        assert result[0].data == {"name": "张三", "phone": "13800138000", "email": "zhang@example.com"}

        # Verify client was not called
        mock_data_security_client.test_rule_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_mask_data_empty_config(self, component, sample_data):
        """Test handling of empty masking configuration."""
        # Setup component with empty rules
        component.data_input = sample_data
        component.masking_rules = []

        # Execute and verify exception
        with pytest.raises(ValueError, match="components.security.data_masking.errors.missing_config"):
            await component.mask_data()

    @pytest.mark.asyncio
    async def test_mask_data_missing_data_input(self, component):
        """Test handling of missing data input."""
        # Setup component with no data
        component.data_input = None
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        # Execute and verify exception
        with pytest.raises(ValueError, match="components.security.data_masking.errors.missing_config"):
            await component.mask_data()

    @pytest.mark.asyncio
    async def test_mask_data_service_unavailable(self, component, sample_data):
        """Test handling of unavailable data security service."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        with patch("lfx.services.deps.get_data_security_client", return_value=None):
            # Execute and verify exception
            with pytest.raises(ValueError, match="components.security.data_masking.errors.service_unavailable"):
                await component.mask_data()

    @pytest.mark.asyncio
    async def test_mask_data_rule_api_error(self, component, sample_data, mock_data_security_client):
        """Test handling of rule API error."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        # Setup mock to raise exception
        mock_data_security_client.test_rule_batch.side_effect = Exception("Rule not found")

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute and verify exception
            with pytest.raises(ValueError, match="Field 'phone' masking failed \\(rule_id=10\\): Rule not found"):
                await component.mask_data()

    @pytest.mark.asyncio
    async def test_mask_data_response_length_mismatch(self, component, sample_data, mock_data_security_client):
        """Test handling of response length mismatch."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        # Setup mock to return different number of results
        mock_data_security_client.test_rule_batch.return_value = ["masked_1"]  # Only 1 result for 3 inputs

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute and verify exception
            with pytest.raises(ValueError, match="Field 'phone' masking failed \\(rule_id=10\\): "
                                 "Masking service returned 1 values but expected 3"):
                await component.mask_data()

    @pytest.mark.asyncio
    async def test_mask_data_skip_null_values(self, component, mock_data_security_client):
        """Test that null values are skipped during masking."""
        # Setup data with null values
        data_with_nulls = [
            Data(data={"field1": "value1", "field2": None}),
            Data(data={"field1": None, "field2": "value2"}),
            Data(data={"field1": "value3", "field2": "value3"}),
        ]
        component.data_input = data_with_nulls
        component.masking_rules = [{"field": "field1", "rule_id": 10}]

        # Setup mock - should only receive non-null values
        mock_data_security_client.test_rule_batch.return_value = ["masked_1", "masked_3"]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify only non-null values were sent
        mock_data_security_client.test_rule_batch.assert_called_once_with(10, ["value1", "value3"])

        # Verify results - nulls should remain null
        assert result[0].data["field1"] == "masked_1"
        assert result[0].data["field2"] is None
        assert result[1].data["field1"] is None
        assert result[1].data["field2"] == "value2"
        assert result[2].data["field1"] == "masked_3"
        assert result[2].data["field2"] == "value3"

    def test_get_masking_stats_success(self, component, sample_data, mock_data_security_client):
        """Test successful statistics generation."""
        # Setup component
        component.data_input = sample_data
        component.masking_rules = [
            {"field": "phone", "rule_id": 10},
            {"field": "email", "rule_id": 11}
        ]

        # Mock the masking process
        mock_data_security_client.test_rule_batch.return_value = ["masked_phone"]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            stats_data = component.get_masking_stats()

        # Verify stats
        stats = stats_data.data
        assert stats["total_records"] == 3
        assert stats["masked_records"] == 3  # Will be calculated by mask_data
        assert len(stats["masking_rules"]) == 2
        assert stats["masking_rules"][0]["field"] == "phone"
        assert stats["masking_rules"][0]["rule_id"] == 10
        assert stats["total_fields_masked"] == 2

    def test_get_masking_stats_with_error(self, component):
        """Test statistics generation with error."""
        # Setup component with missing data
        component.data_input = None
        component.masking_rules = [{"field": "phone", "rule_id": 10}]

        # Execute
        stats_data = component.get_masking_stats()

        # Verify error stats
        stats = stats_data.data
        assert stats["total_records"] == 0
        assert stats["masked_records"] == 0
        assert stats["masking_rules"] == []
        assert stats["total_fields_masked"] == 0
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_load_masking_rules_success(self, component, mock_data_security_client):
        """Test successful loading of masking rules."""
        # Setup mock response
        mock_data_security_client.get_protection_rules.return_value = [
            {"id": 10, "ruleName": "手机号脱敏"},
            {"id": 11, "ruleName": "邮箱脱敏"},
            {"id": 12, "ruleName": "身份证脱敏"},
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            rules = await component._load_masking_rules()

        # Verify results
        assert len(rules) == 3
        assert rules[0]["id"] == 10
        assert rules[0]["ruleName"] == "手机号脱敏"
        assert rules[1]["id"] == 11
        assert rules[1]["ruleName"] == "邮箱脱敏"
        assert rules[2]["id"] == 12
        assert rules[2]["ruleName"] == "身份证脱敏"

        # Verify client call
        mock_data_security_client.get_protection_rules.assert_called_once_with(rule_type="MASKING")

    @pytest.mark.asyncio
    async def test_load_masking_rules_service_unavailable(self, component):
        """Test loading masking rules when service is unavailable."""
        with patch("lfx.services.deps.get_data_security_client", return_value=None):
            # Execute
            rules = await component._load_masking_rules()

        # Verify empty result
        assert rules == []

    @pytest.mark.asyncio
    async def test_load_masking_rules_api_error(self, component, mock_data_security_client):
        """Test loading masking rules with API error."""
        # Setup mock to raise exception
        mock_data_security_client.get_protection_rules.side_effect = Exception("Service error")

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            rules = await component._load_masking_rules()

        # Verify empty result
        assert rules == []

    def test_extract_field_names_success(self, component):
        """Test successful field name extraction."""
        # Create sample data
        data_list = [
            Data(data={"field1": "value1", "field2": "value2"}),
            Data(data={"field1": "value3", "field2": "value4"}),
        ]

        # Execute
        field_names = component._extract_field_names(data_list)

        # Verify results
        assert field_names == ["field1", "field2"]

    def test_extract_field_names_empty_data(self, component):
        """Test field name extraction with empty data."""
        # Execute
        field_names = component._extract_field_names([])

        # Verify results
        assert field_names == []

    def test_extract_field_names_invalid_data(self, component):
        """Test field name extraction with invalid data."""
        # Create invalid data
        data_list = [
            "invalid_string",
            123,
            None,
        ]

        # Execute
        field_names = component._extract_field_names(data_list)

        # Verify results
        assert field_names == []

    @pytest.mark.asyncio
    async def test_mask_data_skip_empty_rule(self, component, sample_data, mock_data_security_client):
        """Test that empty rules are skipped."""
        # Setup component with invalid rule
        component.data_input = sample_data
        component.masking_rules = [
            {"field": "", "rule_id": 10},  # Empty field name
            {"field": "phone", "rule_id": None},  # Empty rule_id
            {"field": "email", "rule_id": 11},  # Valid rule
        ]

        # Setup mock response
        mock_data_security_client.test_rule_batch.return_value = ["masked_email1", "masked_email2"]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify only valid rule was processed
        assert len(result) == 3
        assert result[0].data["phone"] == "13800138000"  # Not processed (invalid rule)
        assert result[0].data["email"] == "masked_email1"  # Processed

        # Verify client was called only once for the valid rule
        mock_data_security_client.test_rule_batch.assert_called_once_with(11, ["zhang@example.com", "li@example.com"])

    @pytest.mark.asyncio
    async def test_mask_data_no_values_to_mask(self, component, mock_data_security_client):
        """Test handling when no values need masking (all nulls)."""
        # Setup data with all null values in target field
        data_all_nulls = [
            Data(data={"field1": None, "field2": "value1"}),
            Data(data={"field1": None, "field2": "value2"}),
        ]
        component.data_input = data_all_nulls
        component.masking_rules = [{"field": "field1", "rule_id": 10}]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.mask_data()

        # Verify client was not called (no values to mask)
        mock_data_security_client.test_rule_batch.assert_not_called()

        # Verify data remains unchanged
        assert len(result) == 2
        assert result[0].data["field1"] is None
        assert result[1].data["field1"] is None
