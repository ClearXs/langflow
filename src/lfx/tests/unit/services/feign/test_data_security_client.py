"""Unit tests for DataSecurityFeignClient."""

from unittest.mock import AsyncMock, Mock

import pytest

from lfx.services.feign.clients.data_security import DataSecurityFeignClient


@pytest.fixture
def mock_feign_service():
    """Create a mock FeignService."""
    return AsyncMock()


@pytest.fixture
def data_security_client(mock_feign_service):
    """Create DataSecurityFeignClient instance."""
    return DataSecurityFeignClient(mock_feign_service)


class TestDataSecurityFeignClient:
    """Test cases for DataSecurityFeignClient."""

    @pytest.mark.asyncio
    async def test_get_protection_rules_encryption_success(self, data_security_client, mock_feign_service):
        """Test successful retrieval of encryption rules."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "ruleName": "AES128加密",
                    "ruleType": "ENCRYPTION",
                    "algorithmType": "AES128",
                    "status": 1,
                    "isReversible": 1,
                },
                {
                    "id": 2,
                    "ruleName": "MD5哈希",
                    "ruleType": "ENCRYPTION",
                    "algorithmType": "MD5",
                    "status": 1,
                    "isReversible": 0,
                },
                {
                    "id": 3,
                    "ruleName": "禁用规则",
                    "ruleType": "ENCRYPTION",
                    "algorithmType": "SHA256",
                    "status": 0,
                    "isReversible": 0,
                },
            ],
        }
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify
        assert len(result) == 2  # Only enabled rules
        assert result[0]["id"] == 1
        assert result[0]["ruleName"] == "AES128加密"
        assert result[1]["id"] == 2
        assert result[1]["ruleName"] == "MD5哈希"

        # Verify service call
        mock_feign_service.get.assert_called_once_with(
            service_name="data-security",
            path="/protection-rule/getList",
            params={"ruleType": "ENCRYPTION"},
        )

    @pytest.mark.asyncio
    async def test_get_protection_rules_masking_success(self, data_security_client, mock_feign_service):
        """Test successful retrieval of masking rules."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": 10,
                    "ruleName": "手机号脱敏",
                    "ruleType": "MASKING",
                    "algorithmType": "PHONE_MASK",
                    "status": 1,
                    "isReversible": 0,
                },
                {
                    "id": 11,
                    "ruleName": "邮箱脱敏",
                    "ruleType": "MASKING",
                    "algorithmType": "EMAIL_MASK",
                    "status": 1,
                    "isReversible": 0,
                },
            ],
        }
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="MASKING")

        # Verify
        assert len(result) == 2
        assert result[0]["id"] == 10
        assert result[0]["ruleName"] == "手机号脱敏"
        assert result[1]["id"] == 11
        assert result[1]["ruleName"] == "邮箱脱敏"

        # Verify service call
        mock_feign_service.get.assert_called_once_with(
            service_name="data-security",
            path="/protection-rule/getList",
            params={"ruleType": "MASKING"},
        )

    @pytest.mark.asyncio
    async def test_get_protection_rules_empty_response(self, data_security_client, mock_feign_service):
        """Test handling of empty response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "data": []}
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_get_protection_rules_service_unavailable(self, data_security_client, mock_feign_service):
        """Test handling of service unavailability."""
        # Setup mock to raise ValueError
        mock_feign_service.get.side_effect = ValueError("No healthy instances found")

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_get_protection_rules_invalid_response_format(self, data_security_client, mock_feign_service):
        """Test handling of invalid response format."""
        # Setup mock response with invalid format
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "format"}
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_get_protection_rules_all_disabled(self, data_security_client, mock_feign_service):
        """Test handling of all disabled rules."""
        # Setup mock response with all disabled rules
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "ruleName": "禁用规则1",
                    "ruleType": "ENCRYPTION",
                    "status": 0,
                },
                {
                    "id": 2,
                    "ruleName": "禁用规则2",
                    "ruleType": "ENCRYPTION",
                    "status": 0,
                },
            ],
        }
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_test_rule_batch_success(self, data_security_client, mock_feign_service):
        """Test successful batch rule testing."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": ["encrypted_1", "encrypted_2", "encrypted_3"],
        }
        mock_feign_service.post.return_value = mock_response

        # Execute
        result = await data_security_client.test_rule_batch(
            rule_id=1, input_values=["value1", "value2", "value3"]
        )

        # Verify
        assert len(result) == 3
        assert result == ["encrypted_1", "encrypted_2", "encrypted_3"]

        # Verify service call
        mock_feign_service.post.assert_called_once_with(
            service_name="data-security",
            path="/protection-rule/testRuleBatch",
            params={"id": 1},
            json=["value1", "value2", "value3"],
        )

    @pytest.mark.asyncio
    async def test_test_rule_batch_empty_input(self, data_security_client, mock_feign_service):
        """Test batch rule testing with empty input."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "data": []}
        mock_feign_service.post.return_value = mock_response

        # Execute
        result = await data_security_client.test_rule_batch(rule_id=1, input_values=[])

        # Verify
        assert result == []

        # Verify service call
        mock_feign_service.post.assert_called_once_with(
            service_name="data-security",
            path="/protection-rule/testRuleBatch",
            params={"id": 1},
            json=[],
        )

    @pytest.mark.asyncio
    async def test_test_rule_batch_service_unavailable(self, data_security_client, mock_feign_service):
        """Test batch rule testing with service unavailable."""
        # Setup mock to raise ValueError
        mock_feign_service.post.side_effect = ValueError("No healthy instances found")

        # Execute and verify exception
        with pytest.raises(ValueError, match="Data security service not available"):
            await data_security_client.test_rule_batch(rule_id=1, input_values=["test"])

    @pytest.mark.asyncio
    async def test_test_rule_batch_invalid_response_format(self, data_security_client, mock_feign_service):
        """Test batch rule testing with invalid response format."""
        # Setup mock response with invalid format
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "format"}
        mock_feign_service.post.return_value = mock_response

        # Execute
        result = await data_security_client.test_rule_batch(
            rule_id=1, input_values=["value1", "value2"]
        )

        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_test_rule_batch_response_length_mismatch(self, data_security_client, mock_feign_service):
        """Test batch rule testing with response length mismatch."""
        # Setup mock response with different length
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "data": ["result1"]}
        mock_feign_service.post.return_value = mock_response

        # Execute
        result = await data_security_client.test_rule_batch(
            rule_id=1, input_values=["value1", "value2", "value3"]
        )

        # Verify - should return whatever service returned, validation happens in component
        assert result == ["result1"]

    @pytest.mark.asyncio
    async def test_test_rule_batch_api_error(self, data_security_client, mock_feign_service):
        """Test batch rule testing with API error."""
        # Setup mock to raise HTTP error
        mock_feign_service.post.side_effect = Exception("HTTP 500: Internal Server Error")

        # Execute and verify exception
        with pytest.raises(ValueError, match="Failed to test rule 1: HTTP 500: Internal Server Error"):
            await data_security_client.test_rule_batch(rule_id=1, input_values=["test"])

    @pytest.mark.asyncio
    async def test_get_protection_rules_direct_list_response(self, data_security_client, mock_feign_service):
        """Test handling of direct list response (no R wrapper)."""
        # Setup mock response with direct list
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "ruleName": "AES128加密",
                "ruleType": "ENCRYPTION",
                "status": 1,
            },
            {
                "id": 2,
                "ruleName": "MD5哈希",
                "ruleType": "ENCRYPTION",
                "status": 0,  # disabled
            },
        ]
        mock_feign_service.get.return_value = mock_response

        # Execute
        result = await data_security_client.get_protection_rules(rule_type="ENCRYPTION")

        # Verify - only enabled rules should be returned
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["ruleName"] == "AES128加密"
