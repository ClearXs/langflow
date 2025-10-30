"""Unit tests for ETLDataEncryptionComponent."""

from unittest.mock import AsyncMock, patch

import pytest

from lfx.components.security.data_encryption import ETLDataEncryptionComponent
from lfx.schema import Data


@pytest.fixture
def component():
    """Create ETLDataEncryptionComponent instance."""
    return ETLDataEncryptionComponent()


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return [
        Data(data={"name": "张三", "phone": "13800138000", "id_card": "110101199001011234"}),
        Data(data={"name": "李四", "phone": "13900139000", "id_card": "110101199001015678"}),
        Data(data={"name": "王五", "phone": "13700137000", "id_card": None}),  # Null value test
    ]


@pytest.fixture
def mock_data_security_client():
    """Create mock data security client."""
    client = AsyncMock()
    # Mock batch encryption
    client.test_rule_batch.return_value = ["encrypted_1", "encrypted_2", "encrypted_3"]
    return client


class TestETLDataEncryptionComponent:
    """Test cases for ETLDataEncryptionComponent."""

    @pytest.mark.asyncio
    async def test_process_encryption_single_field(self, component, sample_data, mock_data_security_client):
        """Test encryption of a single field."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        # Mock the client
        mock_data_security_client.test_rule_batch.return_value = [
            "encrypted_phone_1",
            "encrypted_phone_2",
            "encrypted_phone_3"
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.process_encryption()

        # Verify results
        assert len(result) == 3
        assert result[0].data["phone"] == "encrypted_phone_1"
        assert result[1].data["phone"] == "encrypted_phone_2"
        assert result[2].data["phone"] == "encrypted_phone_3"

        # Other fields should remain unchanged
        assert result[0].data["name"] == "张三"
        assert result[0].data["id_card"] == "110101199001011234"

        # Verify client was called correctly
        mock_data_security_client.test_rule_batch.assert_called_once_with(
            1, ["13800138000", "13900139000", "13700137000"]
        )

    @pytest.mark.asyncio
    async def test_process_encryption_multiple_fields(self, component, sample_data, mock_data_security_client):
        """Test encryption of multiple fields."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [
            {"field": "phone", "rule_id": 1},
            {"field": "id_card", "rule_id": 2}
        ]

        # Setup mock responses for different calls
        mock_data_security_client.test_rule_batch.side_effect = [
            ["encrypted_phone_1", "encrypted_phone_2", "encrypted_phone_3"],  # First call for phone
            ["encrypted_id_1", "encrypted_id_2"]                               # Second call for id_card (skip null)
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.process_encryption()

        # Verify results
        assert len(result) == 3
        assert result[0].data["phone"] == "encrypted_phone_1"
        assert result[0].data["id_card"] == "encrypted_id_1"
        assert result[1].data["phone"] == "encrypted_phone_2"
        assert result[1].data["id_card"] == "encrypted_id_2"
        assert result[2].data["phone"] == "encrypted_phone_3"
        assert result[2].data["id_card"] is None  # Remains null

        # Verify client calls
        assert mock_data_security_client.test_rule_batch.call_count == 2
        mock_data_security_client.test_rule_batch.assert_any_call(1, ["13800138000", "13900139000", "13700137000"])
        mock_data_security_client.test_rule_batch.assert_any_call(2, ["110101199001011234", "110101199001015678"])

    @pytest.mark.asyncio
    async def test_process_encryption_field_not_found(self, component, sample_data, mock_data_security_client):
        """Test handling of field not found in data."""
        # Setup component with non-existent field
        component.data_input = sample_data
        component.field_configs = [{"field": "non_existent_field", "rule_id": 1}]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.process_encryption()

        # Verify data remains unchanged
        assert len(result) == 3
        assert result[0].data == {"name": "张三", "phone": "13800138000", "id_card": "110101199001011234"}

        # Verify client was not called
        mock_data_security_client.test_rule_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_encryption_empty_config(self, component, sample_data):
        """Test handling of empty field configuration."""
        # Setup component with empty configs
        component.data_input = sample_data
        component.field_configs = []

        # Execute and verify exception
        with pytest.raises(ValueError, match="components.security.data_encryption.errors.missing_config"):
            await component.process_encryption()

    @pytest.mark.asyncio
    async def test_process_encryption_missing_data_input(self, component):
        """Test handling of missing data input."""
        # Setup component with no data
        component.data_input = None
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        # Execute and verify exception
        with pytest.raises(ValueError, match="components.security.data_encryption.errors.missing_config"):
            await component.process_encryption()

    @pytest.mark.asyncio
    async def test_process_encryption_service_unavailable(self, component, sample_data):
        """Test handling of unavailable data security service."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        with patch("lfx.services.deps.get_data_security_client", return_value=None):
            # Execute and verify exception
            with pytest.raises(ValueError, match="components.security.data_encryption.errors.service_unavailable"):
                await component.process_encryption()

    @pytest.mark.asyncio
    async def test_process_encryption_rule_api_error(self, component, sample_data, mock_data_security_client):
        """Test handling of rule API error."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        # Setup mock to raise exception
        mock_data_security_client.test_rule_batch.side_effect = Exception("Rule not found")

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute and verify exception
            with pytest.raises(ValueError, match="Field 'phone' encryption failed \\(rule_id=1\\): Rule not found"):
                await component.process_encryption()

    @pytest.mark.asyncio
    async def test_process_encryption_response_length_mismatch(self, component, sample_data, mock_data_security_client):
        """Test handling of response length mismatch."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        # Setup mock to return different number of results
        mock_data_security_client.test_rule_batch.return_value = ["encrypted_1"]  # Only 1 result for 3 inputs

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute and verify exception
            with pytest.raises(ValueError, match="Field 'phone' encryption failed \\(rule_id=1\\): "
                                 "Encryption service returned 1 values but expected 3"):
                await component.process_encryption()

    @pytest.mark.asyncio
    async def test_process_encryption_skip_null_values(self, component, mock_data_security_client):
        """Test that null values are skipped during encryption."""
        # Setup data with null values
        data_with_nulls = [
            Data(data={"field1": "value1", "field2": None}),
            Data(data={"field1": None, "field2": "value2"}),
            Data(data={"field1": "value3", "field2": "value3"}),
        ]
        component.data_input = data_with_nulls
        component.field_configs = [{"field": "field1", "rule_id": 1}]

        # Setup mock - should only receive non-null values
        mock_data_security_client.test_rule_batch.return_value = ["encrypted_1", "encrypted_3"]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            result = await component.process_encryption()

        # Verify only non-null values were sent
        mock_data_security_client.test_rule_batch.assert_called_once_with(1, ["value1", "value3"])

        # Verify results - nulls should remain null
        assert result[0].data["field1"] == "encrypted_1"
        assert result[0].data["field2"] is None
        assert result[1].data["field1"] is None
        assert result[1].data["field2"] == "value2"
        assert result[2].data["field1"] == "encrypted_3"
        assert result[2].data["field2"] == "value3"

    def test_get_encryption_stats_success(self, component, sample_data, mock_data_security_client):
        """Test successful statistics generation."""
        # Setup component
        component.data_input = sample_data
        component.field_configs = [
            {"field": "phone", "rule_id": 1},
            {"field": "id_card", "rule_id": 2}
        ]

        # Mock the encryption process
        mock_data_security_client.test_rule_batch.return_value = ["encrypted_phone"]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            stats_data = component.get_encryption_stats()

        # Verify stats
        stats = stats_data.data
        assert stats["total_records"] == 3
        assert stats["processed_records"] == 3  # Will be calculated by process_encryption
        assert len(stats["field_configs"]) == 2
        assert stats["field_configs"][0]["field"] == "phone"
        assert stats["field_configs"][0]["rule_id"] == 1
        assert stats["total_fields_processed"] == 2

    def test_get_encryption_stats_with_error(self, component):
        """Test statistics generation with error."""
        # Setup component with missing data
        component.data_input = None
        component.field_configs = [{"field": "phone", "rule_id": 1}]

        # Execute
        stats_data = component.get_encryption_stats()

        # Verify error stats
        stats = stats_data.data
        assert stats["total_records"] == 0
        assert stats["processed_records"] == 0
        assert stats["field_configs"] == []
        assert stats["total_fields_processed"] == 0
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_load_encryption_rules_success(self, component, mock_data_security_client):
        """Test successful loading of encryption rules."""
        # Setup mock response
        mock_data_security_client.get_protection_rules.return_value = [
            {"id": 1, "ruleName": "AES128加密"},
            {"id": 2, "ruleName": "MD5哈希"},
        ]

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            rules = await component._load_encryption_rules()

        # Verify results
        assert len(rules) == 2
        assert rules[0]["id"] == 1
        assert rules[0]["ruleName"] == "AES128加密"
        assert rules[1]["id"] == 2
        assert rules[1]["ruleName"] == "MD5哈希"

        # Verify client call
        mock_data_security_client.get_protection_rules.assert_called_once_with(rule_type="ENCRYPTION")

    @pytest.mark.asyncio
    async def test_load_encryption_rules_service_unavailable(self, component):
        """Test loading encryption rules when service is unavailable."""
        with patch("lfx.services.deps.get_data_security_client", return_value=None):
            # Execute
            rules = await component._load_encryption_rules()

        # Verify empty result
        assert rules == []

    @pytest.mark.asyncio
    async def test_load_encryption_rules_api_error(self, component, mock_data_security_client):
        """Test loading encryption rules with API error."""
        # Setup mock to raise exception
        mock_data_security_client.get_protection_rules.side_effect = Exception("Service error")

        with patch("lfx.services.deps.get_data_security_client", return_value=mock_data_security_client):
            # Execute
            rules = await component._load_encryption_rules()

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
