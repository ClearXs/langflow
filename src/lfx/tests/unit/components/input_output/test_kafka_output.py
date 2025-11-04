"""Unit tests for ETLKafkaOutputComponent."""

from unittest.mock import Mock, patch
import json
import pytest

from lfx.components.input_output.kafka_output import ETLKafkaOutputComponent
from lfx.schema import Data


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        Data(data={"id": "user1", "name": "Alice", "age": 30, "city": "Beijing"}),
        Data(data={"id": "user2", "name": "Bob", "age": 25, "city": "Shanghai"}),
        Data(data={"id": "user3", "name": "Charlie", "age": 35, "city": "Guangzhou"}),
    ]


@pytest.fixture
def basic_component_config():
    """Basic component configuration."""
    return {
        "bootstrap_servers": "localhost:9092",
        "topic": "test-topic",
        "value_serializer": "json",
        "acks": "1",
        "retries": 3,
        "send_as_batch": True,
        "batch_size": 2,
    }


@pytest.fixture
def component_with_auth(basic_component_config):
    """Component configuration with SASL authentication."""
    config = basic_component_config.copy()
    config.update(
        {
            "sasl_username": "testuser",
            "sasl_password": "testpass",
        }
    )
    return config


class TestETLKafkaOutputComponent:
    """Test cases for Kafka output component."""

    def test_component_initialization(self, basic_component_config):
        """Test component initialization with basic config."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        assert component.bootstrap_servers == "localhost:9092"
        assert component.topic == "test-topic"
        assert component.value_serializer == "json"
        assert component.send_as_batch is True
        assert component.batch_size == 2
        assert component._producer is None

    def test_component_initialization_with_auth(self, component_with_auth):
        """Test component initialization with SASL auth."""
        component = ETLKafkaOutputComponent(**component_with_auth)

        assert component.sasl_username == "testuser"
        assert component.sasl_password == "testpass"

    def test_component_initialization_with_headers(self, basic_component_config):
        """Test component initialization with custom headers."""
        config = basic_component_config.copy()
        config["headers"] = [
            {"key": "source", "value": "test"},
            {"key": "version", "value": "1.0"},
        ]

        component = ETLKafkaOutputComponent(**config)
        assert len(component.headers) == 2

    @patch("confluent_kafka.Producer")
    def test_create_producer_basic(self, mock_producer_class, basic_component_config):
        """Test producer creation with basic configuration."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**basic_component_config)
        producer = component._create_producer()

        # Verify producer was created with correct config
        mock_producer_class.assert_called_once()
        call_args = mock_producer_class.call_args[1]

        assert call_args["bootstrap.servers"] == "localhost:9092"
        assert call_args["acks"] == "1"
        assert call_args["retries"] == 3
        assert producer == mock_producer

    @patch("confluent_kafka.Producer")
    def test_create_producer_with_auth(self, mock_producer_class, component_with_auth):
        """Test producer creation with SASL authentication."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**component_with_auth)
        component._create_producer()

        # Verify SASL config was added
        call_args = mock_producer_class.call_args[1]
        assert call_args["security.protocol"] == "SASL_PLAINTEXT"
        assert call_args["sasl.mechanism"] == "PLAIN"
        assert call_args["sasl.username"] == "testuser"
        assert call_args["sasl.password"] == "testpass"

    @patch("confluent_kafka.Producer")
    def test_create_producer_with_compression(self, mock_producer_class, basic_component_config):
        """Test producer creation with compression."""
        config = basic_component_config.copy()
        config["compression_type"] = "gzip"

        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**config)
        component._create_producer()

        call_args = mock_producer_class.call_args[1]
        assert call_args["compression.type"] == "gzip"

    def test_serialize_value_json(self, basic_component_config):
        """Test JSON serialization of values."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        # Test dict serialization
        data_dict = {"id": 1, "name": "test"}
        result = component._serialize_value(data_dict)
        expected = json.dumps(data_dict, ensure_ascii=False).encode("utf-8")
        assert result == expected

        # Test list serialization
        data_list = [1, 2, 3]
        result = component._serialize_value(data_list)
        expected = json.dumps(data_list, ensure_ascii=False).encode("utf-8")
        assert result == expected

        # Test string serialization
        data_str = "simple string"
        result = component._serialize_value(data_str)
        expected = json.dumps({"value": data_str}, ensure_ascii=False).encode("utf-8")
        assert result == expected

    def test_serialize_value_string(self, basic_component_config):
        """Test string serialization of values."""
        config = basic_component_config.copy()
        config["value_serializer"] = "string"
        component = ETLKafkaOutputComponent(**config)

        # Test string value
        data_str = "simple string"
        result = component._serialize_value(data_str)
        expected = data_str.encode("utf-8")
        assert result == expected

        # Test non-string value
        data_int = 123
        result = component._serialize_value(data_int)
        expected = "123".encode("utf-8")
        assert result == expected

    def test_extract_key(self, basic_component_config):
        """Test key extraction from data."""
        config = basic_component_config.copy()
        config["key_field"] = "id"
        component = ETLKafkaOutputComponent(**config)

        # Test with existing key field
        data = {"id": "user123", "name": "test"}
        key = component._extract_key(data)
        assert key == "user123"

        # Test with missing key field
        data = {"name": "test", "age": 30}
        key = component._extract_key(data)
        assert key is None

        # Test with None key value
        data = {"id": None, "name": "test"}
        key = component._extract_key(data)
        assert key is None

    def test_extract_key_no_key_field(self, basic_component_config):
        """Test key extraction when no key field is specified."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        data = {"id": "user123", "name": "test"}
        key = component._extract_key(data)
        assert key is None

    def test_get_partition_with_partition_key(self, basic_component_config):
        """Test partition determination with partition key."""
        config = basic_component_config.copy()
        config["partition_key"] = "region"
        component = ETLKafkaOutputComponent(**config)

        data = {"region": "north", "name": "test"}
        partition = component._get_partition(data)
        assert isinstance(partition, int)
        assert 0 <= partition < 100

    def test_get_partition_with_key_field(self, basic_component_config):
        """Test partition determination using key field."""
        config = basic_component_config.copy()
        config["key_field"] = "user_id"
        component = ETLKafkaOutputComponent(**config)

        data = {"user_id": "user123", "name": "test"}
        partition = component._get_partition(data)
        assert isinstance(partition, int)
        assert 0 <= partition < 100

    def test_get_partition_no_keys(self, basic_component_config):
        """Test partition determination when no keys are specified."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        data = {"name": "test", "age": 30}
        partition = component._get_partition(data)
        assert partition is None

    @patch("confluent_kafka.Producer")
    @pytest.mark.asyncio
    async def test_send_single_message(self, mock_producer_class, basic_component_config):
        """Test sending a single message to Kafka."""
        # Setup mock producer
        mock_producer = Mock()
        mock_producer.poll = Mock()
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**basic_component_config)

        # Test data
        data = {"id": "user123", "name": "test"}
        headers = {"source": "unit-test"}

        # Send message
        await component._send_single_message(mock_producer, data, headers)

        # Verify produce was called
        mock_producer.produce.assert_called_once()
        call_args = mock_producer.produce.call_args[1]

        assert call_args["topic"] == "test-topic"
        assert call_args["key"] == b"user123"  # Using id as key
        assert json.loads(call_args["value"].decode("utf-8")) == {"id": "user123", "name": "test"}
        assert call_args["headers"] == [("source", b"unit-test")]

    @patch("confluent_kafka.Producer")
    @pytest.mark.asyncio
    async def test_send_to_kafka_success_batch(self, mock_producer_class, sample_data, basic_component_config):
        """Test successful batch sending to Kafka."""
        # Setup mock producer
        mock_producer = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock(return_value=0)  # All messages flushed successfully
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**basic_component_config)
        component.data_input = sample_data

        # Send to Kafka
        result = await component.send_to_kafka()

        # Verify result
        assert result.data["success_count"] == 3
        assert result.data["error_count"] == 0
        assert result.data["total_messages"] == 3
        assert result.data["topic"] == "test-topic"
        assert result.data["send_as_batch"] is True

        # Verify flush was called
        mock_producer.flush.assert_called_with(timeout=5)

    @patch("confluent_kafka.Producer")
    @pytest.mark.asyncio
    async def test_send_to_kafka_success_individual(self, mock_producer_class, sample_data, basic_component_config):
        """Test successful individual sending to Kafka."""
        # Setup mock producer
        mock_producer = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock(return_value=0)
        mock_producer_class.return_value = mock_producer

        config = basic_component_config.copy()
        config["send_as_batch"] = False
        component = ETLKafkaOutputComponent(**config)
        component.data_input = sample_data

        # Send to Kafka
        result = await component.send_to_kafka()

        # Verify result
        assert result.data["success_count"] == 3
        assert result.data["error_count"] == 0
        assert result.data["total_messages"] == 3
        assert result.data["send_as_batch"] is False

    @pytest.mark.asyncio
    async def test_send_to_kafka_no_data(self, basic_component_config):
        """Test sending to Kafka with no data."""
        component = ETLKafkaOutputComponent(**basic_component_config)
        component.data_input = []

        with pytest.raises(ValueError, match="No data provided"):
            await component.send_to_kafka()

    @patch("confluent_kafka.Producer")
    def test_test_connection_success(self, mock_producer_class, basic_component_config):
        """Test successful connection test."""
        # Setup mock producer
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.flush = Mock(return_value=0)
        mock_producer.close = Mock()
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**basic_component_config)

        # Test connection
        result = component.test_connection()

        # Verify result
        assert result["success"] is True
        assert "Connection test successful" in result["message"]
        assert result["diagnostic"]["producer_creation"] == "success"
        assert result["diagnostic"]["metadata_test"] == "success"

    def test_test_connection_import_error(self, basic_component_config):
        """Test connection test when confluent-kafka is not installed."""
        with patch("confluent_kafka.Producer", side_effect=ImportError("No module named 'confluent_kafka'")):
            component = ETLKafkaOutputComponent(**basic_component_config)

            result = component.test_connection()

            assert result["success"] is False
            assert "confluent-kafka library is not installed" in result["error"]

    @patch("confluent_kafka.Producer")
    def test_test_connection_producer_creation_failed(self, mock_producer_class, basic_component_config):
        """Test connection test when producer creation fails."""
        mock_producer_class.side_effect = Exception("Connection failed")

        component = ETLKafkaOutputComponent(**basic_component_config)

        result = component.test_connection()

        assert result["success"] is False
        assert "Failed to create producer" in result["error"]
        assert result["diagnostic"]["producer_creation"] == "failed"

    def test_get_connection_recommendations(self, basic_component_config):
        """Test connection recommendations based on diagnostic info."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        # Test with producer creation failure
        diagnostic = {"producer_creation": "failed"}
        recommendations = component._get_connection_recommendations(diagnostic)
        assert any("bootstrap servers" in rec for rec in recommendations)

        # Test with SASL enabled
        diagnostic = {"sasl_enabled": True}
        recommendations = component._get_connection_recommendations(diagnostic)
        assert any("SASL username" in rec for rec in recommendations)

    def test_get_producer_info(self, basic_component_config):
        """Test getting producer information."""
        config = basic_component_config.copy()
        config["headers"] = [{"key": "test", "value": "value"}]
        component = ETLKafkaOutputComponent(**config)

        result = component.get_producer_info()

        assert result.data["bootstrap_servers"] == "localhost:9092"
        assert result.data["topic"] == "test-topic"
        assert result.data["value_serializer"] == "json"
        assert result.data["headers_count"] == 1
        assert result.data["producer_active"] is False  # Producer not created yet

    def test_cleanup_on_deletion(self, basic_component_config):
        """Test that producer is cleaned up when component is deleted."""
        with patch("confluent_kafka.Producer") as mock_producer_class:
            mock_producer = Mock()
            mock_producer.flush = Mock()
            mock_producer_class.return_value = mock_producer

            component = ETLKafkaOutputComponent(**basic_component_config)
            component._producer = mock_producer

            # Delete component
            del component

            # Verify flush was called
            mock_producer.flush.assert_called_with(timeout=5)

    @patch("confluent_kafka.Producer")
    @pytest.mark.asyncio
    async def test_send_batch_partial_failure(self, mock_producer_class, sample_data, basic_component_config):
        """Test batch sending with some failures."""
        # Setup mock producer
        mock_producer = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock(return_value=0)
        mock_producer_class.return_value = mock_producer

        component = ETLKafkaOutputComponent(**basic_component_config)

        # Mock _send_single_message to simulate some failures
        async def mock_send_single(producer, data_item, headers):
            if data_item.get("id") == "user2":  # Simulate failure for this item
                raise Exception("Simulated send failure")

        component._send_single_message = mock_send_single

        # Test data as simple dicts (not Data objects)
        component.data_input = [
            {"id": "user1", "name": "Alice"},
            {"id": "user2", "name": "Bob"},
            {"id": "user3", "name": "Charlie"},
        ]

        # Send to Kafka
        result = await component.send_to_kafka()

        # Verify partial success
        assert result.data["success_count"] == 2
        assert result.data["error_count"] == 1
        assert result.data["total_messages"] == 3

    def test_delivery_report_callback(self, basic_component_config):
        """Test delivery report callback."""
        component = ETLKafkaOutputComponent(**basic_component_config)

        # Mock message object
        mock_msg = Mock()
        mock_msg.topic.return_value = "test-topic"
        mock_msg.partition.return_value = 0
        mock_msg.offset.return_value = 123

        # Test successful delivery
        with patch("lfx.components.input_output.kafka_output.logger") as mock_logger:
            component._delivery_report(None, mock_msg)
            mock_logger.debug.assert_called()

        # Test failed delivery
        with patch("lfx.components.input_output.kafka_output.logger") as mock_logger:
            mock_error = Mock()
            mock_error.__str__ = Mock(return_value="Delivery failed")
            component._delivery_report(mock_error, None)
            mock_logger.error.assert_called()
