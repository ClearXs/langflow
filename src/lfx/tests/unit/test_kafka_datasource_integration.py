"""Unit tests for Kafka Input and Output components with datasource integration.
Tests the removal of bootstrap_servers and support for public datasources.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestKafkaInputDatasourceIntegration:
    """Test Kafka Input component datasource integration."""

    @pytest.fixture
    def kafka_input_component(self):
        """Create a Kafka Input component instance."""
        from lfx.components.input_output.kafka_input import ETLKafkaInputComponent

        component = ETLKafkaInputComponent()
        component.datasource_selector = "test-datasource-id"
        component.topics = "test-topic"
        component.group_id = "test-group"
        return component

    def test_datasource_required(self, kafka_input_component):
        """Test that datasource_selector is required."""
        # Clear datasource
        kafka_input_component.datasource_selector = None

        # Should raise ValueError
        with pytest.raises(ValueError, match="Datasource selector is required"):
            kafka_input_component._create_consumer()

    def test_find_datasource_info_builtin(self, kafka_input_component):
        """Test finding builtin datasource info."""
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "test-datasource-id",
                        "name": "Test Datasource",
                        "type": "kafka",
                        "source": "builtin",
                        "display_name": "Test Datasource (Kafka) [自定义]",
                    }
                ]
            }
        }

        result = kafka_input_component._find_datasource_info("test-datasource-id")

        assert result is not None
        assert result["id"] == "test-datasource-id"
        assert result["source"] == "builtin"
        assert result["type"] == "kafka"

    def test_find_datasource_info_public(self, kafka_input_component):
        """Test finding public datasource info."""
        public_raw_data = {
            "id": 123,
            "name": "Public Kafka",
            "dataSourceParam": {"type": "kafka", "host": "kafka-public:9092"},
        }

        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "123",
                        "name": "Public Kafka",
                        "type": "kafka",
                        "source": "public",
                        "display_name": "Public Kafka (Kafka) [公共]",
                        "raw_data": public_raw_data,
                    }
                ]
            }
        }

        result = kafka_input_component._find_datasource_info("123")

        assert result is not None
        assert result["id"] == "123"
        assert result["source"] == "public"
        assert result["raw_data"] == public_raw_data

    @patch("httpx.Client")
    def test_get_kafka_config_from_builtin_datasource(self, mock_client, kafka_input_component):
        """Test getting Kafka config from builtin datasource."""
        # Mock datasource info
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "test-datasource-id",
                        "source": "builtin",
                    }
                ]
            }
        }

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "host": "kafka1:9092,kafka2:9092",
            "advanced_config": json.dumps({
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_username": "admin",
                "sasl_password": "password",
            }),
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        config = kafka_input_component._get_kafka_config_from_datasource()

        assert config["bootstrap.servers"] == "kafka1:9092,kafka2:9092"
        assert config["security.protocol"] == "SASL_PLAINTEXT"
        assert config["sasl.mechanism"] == "PLAIN"
        assert config["sasl.username"] == "admin"
        assert config["sasl.password"] == "password"

    def test_get_kafka_config_from_public_datasource(self, kafka_input_component):
        """Test getting Kafka config from public datasource."""
        public_raw_data = {
            "id": 123,
            "name": "Public Kafka",
            "dataSourceParam": {
                "type": "kafka",
                "host": "kafka-prod1:9092,kafka-prod2:9092",
                "sasl_username": "svc_account",
                "sasl_password": "encrypted_password",
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "SCRAM-SHA-256",
            },
        }

        kafka_input_component.datasource_selector = "123"
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "123",
                        "name": "Public Kafka",
                        "type": "kafka",
                        "source": "public",
                        "display_name": "Public Kafka (Kafka) [公共]",
                        "raw_data": public_raw_data,
                    }
                ]
            }
        }

        config = kafka_input_component._get_kafka_config_from_datasource()

        assert config["bootstrap.servers"] == "kafka-prod1:9092,kafka-prod2:9092"
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanism"] == "SCRAM-SHA-256"
        assert config["sasl.username"] == "svc_account"
        assert config["sasl.password"] == "encrypted_password"

    def test_get_kafka_config_public_datasource_defaults(self, kafka_input_component):
        """Test public datasource with default SASL config."""
        public_raw_data = {
            "id": 123,
            "name": "Public Kafka Simple Auth",
            "dataSourceParam": {
                "type": "kafka",
                "host": "kafka-simple:9092",
                "sasl_username": "user",
                "sasl_password": "pass",
                # No security_protocol or sasl_mechanism specified
            },
        }

        kafka_input_component.datasource_selector = "123"
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "123",
                        "name": "Public Kafka Simple Auth",
                        "type": "kafka",
                        "source": "public",
                        "display_name": "Public Kafka Simple Auth (Kafka) [公共]",
                        "raw_data": public_raw_data,
                    }
                ]
            }
        }

        config = kafka_input_component._get_kafka_config_from_datasource()

        # Should default to SASL_PLAINTEXT and PLAIN
        assert config["security.protocol"] == "SASL_PLAINTEXT"
        assert config["sasl.mechanism"] == "PLAIN"

    @patch("asyncio.run")
    @patch("httpx.Client")
    def test_load_kafka_datasources_merges_builtin_and_public(self, mock_client, mock_async_run, kafka_input_component):
        """Test that _load_kafka_datasources merges both builtin and public datasources."""
        # Mock public datasources
        mock_async_run.return_value = [
            {
                "id": 456,
                "name": "Public Kafka Prod",
                "dataSourceParam": {"type": "kafka", "host": "kafka-prod:9092"},
            }
        ]

        # Mock builtin datasources
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "builtin-123", "name": "Builtin Kafka", "type": "kafka"}
        ]
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        datasources = kafka_input_component._load_kafka_datasources()

        # Should have both builtin and public
        assert len(datasources) == 2

        # Check builtin
        builtin_ds = next(ds for ds in datasources if ds["source"] == "builtin")
        assert builtin_ds["name"] == "Builtin Kafka"
        assert "[自定义]" in builtin_ds["display_name"]

        # Check public
        public_ds = next(ds for ds in datasources if ds["source"] == "public")
        assert public_ds["name"] == "Public Kafka Prod"
        assert "[公共]" in public_ds["display_name"]
        assert "raw_data" in public_ds

    def test_find_datasource_from_vertex_template(self, kafka_input_component):
        """Test finding datasource info from vertex.data template (runtime persistence)."""
        # Simulate runtime scenario: _build_config is not available
        if hasattr(kafka_input_component, "_build_config"):
            delattr(kafka_input_component, "_build_config")

        # Mock vertex with template data (simulating runtime persistence)
        mock_vertex = MagicMock()
        mock_vertex.data = {
            "node": {
                "template": {
                    "datasource_selector": {
                        "options_metadata": [
                            {
                                "id": "vertex-datasource-id",
                                "name": "Vertex Kafka",
                                "type": "kafka",
                                "source": "builtin",
                                "display_name": "Vertex Kafka (Kafka) [自定义]",
                            }
                        ]
                    }
                }
            }
        }
        kafka_input_component._vertex = mock_vertex

        result = kafka_input_component._find_datasource_info("vertex-datasource-id")

        assert result is not None
        assert result["id"] == "vertex-datasource-id"
        assert result["source"] == "builtin"
        assert result["type"] == "kafka"

    def test_find_datasource_fallback_priority(self, kafka_input_component):
        """Test that _build_config has priority over vertex.data."""
        # Set up _build_config with one datasource
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "build-config-id",
                        "name": "Build Config Kafka",
                        "type": "kafka",
                        "source": "builtin",
                        "display_name": "Build Config (Kafka)",
                    }
                ]
            }
        }

        # Set up vertex with different datasource
        mock_vertex = MagicMock()
        mock_vertex.data = {
            "node": {
                "template": {
                    "datasource_selector": {
                        "options_metadata": [
                            {
                                "id": "vertex-id",
                                "name": "Vertex Kafka",
                                "type": "kafka",
                                "source": "builtin",
                                "display_name": "Vertex (Kafka)",
                            }
                        ]
                    }
                }
            }
        }
        kafka_input_component._vertex = mock_vertex

        # Should find from _build_config first
        result = kafka_input_component._find_datasource_info("build-config-id")
        assert result is not None
        assert result["id"] == "build-config-id"

        # Should fallback to vertex when not in _build_config
        result = kafka_input_component._find_datasource_info("vertex-id")
        assert result is not None
        assert result["id"] == "vertex-id"

    def test_get_kafka_config_with_bootstrap_servers_field(self, kafka_input_component):
        """Test getting Kafka config from public datasource with bootstrapServers field."""
        public_raw_data = {
            "id": "1987773600610652161",
            "name": "kafka",
            "dataSourceParam": {
                "bootstrapServers": "192.110.100.120:9092",
                "pool": {"minIdle": 1, "maxIdle": 2, "maxTotal": 5, "properties": []},
                "type": "kafka",
            },
        }

        kafka_input_component.datasource_selector = "1987773600610652161"
        kafka_input_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "1987773600610652161",
                        "name": "kafka",
                        "type": "kafka",
                        "source": "public",
                        "display_name": "kafka (Kafka) [公共]",
                        "raw_data": public_raw_data,
                    }
                ]
            }
        }

        config = kafka_input_component._get_kafka_config_from_datasource()

        assert config["bootstrap.servers"] == "192.110.100.120:9092"


class TestKafkaOutputDatasourceIntegration:
    """Test Kafka Output component datasource integration."""

    @pytest.fixture
    def kafka_output_component(self):
        """Create a Kafka Output component instance."""
        from lfx.components.input_output.kafka_output import ETLKafkaOutputComponent

        component = ETLKafkaOutputComponent()
        component.datasource_selector = "test-datasource-id"
        component.topic = "test-topic"
        return component

    def test_datasource_required(self, kafka_output_component):
        """Test that datasource_selector is required."""
        # Clear datasource
        kafka_output_component.datasource_selector = None

        # Should raise ValueError
        with pytest.raises(ValueError, match="Datasource selector is required"):
            kafka_output_component._create_producer()

    @patch("httpx.Client")
    def test_get_kafka_config_from_builtin_datasource(self, mock_client, kafka_output_component):
        """Test getting Kafka config from builtin datasource."""
        # Mock datasource info
        kafka_output_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "test-datasource-id",
                        "source": "builtin",
                    }
                ]
            }
        }

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "host": "kafka1:9092",
            "advanced_config": json.dumps({
                "compression_type": "gzip",
                "acks": "all",
            }),
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        config = kafka_output_component._get_kafka_config_from_datasource()

        assert config["bootstrap.servers"] == "kafka1:9092"
        assert config["compression.type"] == "gzip"
        assert config["acks"] == "all"

    def test_get_kafka_config_from_public_datasource(self, kafka_output_component):
        """Test getting Kafka config from public datasource."""
        public_raw_data = {
            "id": 789,
            "name": "Public Kafka Output",
            "dataSourceParam": {
                "type": "kafka",
                "host": "kafka-output:9092",
                "compression_type": "snappy",
                "batch_size": 32768,
                "linger_ms": 20,
            },
        }

        kafka_output_component.datasource_selector = "789"
        kafka_output_component._build_config = {
            "datasource_selector": {
                "options_metadata": [
                    {
                        "id": "789",
                        "name": "Public Kafka Output",
                        "type": "kafka",
                        "source": "public",
                        "display_name": "Public Kafka Output (Kafka) [公共]",
                        "raw_data": public_raw_data,
                    }
                ]
            }
        }

        config = kafka_output_component._get_kafka_config_from_datasource()

        assert config["bootstrap.servers"] == "kafka-output:9092"
        assert config["compression.type"] == "snappy"
        assert config["batch.size"] == 32768
        assert config["linger.ms"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
