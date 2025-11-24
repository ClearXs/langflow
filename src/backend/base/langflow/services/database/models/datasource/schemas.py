"""JSON Schema definitions for datasource advanced configurations."""

# MySQL Advanced Configuration Schema
MYSQL_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "connect_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "read_timeout": {"type": "integer", "minimum": 1, "maximum": 3600, "description": "Read timeout in seconds"},
        "write_timeout": {"type": "integer", "minimum": 1, "maximum": 3600, "description": "Write timeout in seconds"},
        "charset": {"type": "string", "enum": ["utf8", "utf8mb4", "latin1", "ascii"], "description": "Character set"},
        "ssl_ca": {"type": "string", "description": "Path to SSL CA certificate"},
        "ssl_cert": {"type": "string", "description": "Path to SSL client certificate"},
        "ssl_key": {"type": "string", "description": "Path to SSL client key"},
        "ssl_disabled": {"type": "boolean", "description": "Disable SSL connection"},
    },
    "additionalProperties": False,
}

# PostgreSQL Advanced Configuration Schema
POSTGRESQL_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "connect_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "statement_timeout": {
            "type": "integer",
            "minimum": 0,
            "maximum": 2147483647,
            "description": "SQL statement timeout in milliseconds (0 = no limit)",
        },
        "sslmode": {
            "type": "string",
            "enum": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
            "description": "SSL mode",
        },
        "sslcert": {"type": "string", "description": "Path to SSL client certificate"},
        "sslkey": {"type": "string", "description": "Path to SSL client key"},
        "sslrootcert": {"type": "string", "description": "Path to SSL root certificate"},
        "application_name": {
            "type": "string",
            "maxLength": 64,
            "description": "Application name for connection tracking",
        },
    },
    "additionalProperties": False,
}

# Hive Advanced Configuration Schema
HIVE_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "transport_mode": {"type": "string", "enum": ["binary", "http"], "description": "Transport mode"},
        "http_path": {"type": "string", "description": "HTTP transport path (only for http mode)"},
        "auth_mechanism": {
            "type": "string",
            "enum": ["NONE", "KERBEROS", "LDAP", "PAM"],
            "description": "Authentication mechanism",
        },
        "kerberos_principal": {"type": "string", "description": "Kerberos principal"},
        "sasl_qop": {
            "type": "string",
            "enum": ["auth", "auth-int", "auth-conf"],
            "description": "SASL quality of protection",
        },
        "ssl_enabled": {"type": "boolean", "description": "Enable SSL"},
        "ssl_truststore": {"type": "string", "description": "Path to SSL truststore file"},
        "truststore_password": {"type": "string", "description": "Truststore password"},
        "zookeeper_discovery": {"type": "boolean", "description": "Use ZooKeeper service discovery"},
        "zookeeper_namespace": {"type": "string", "description": "ZooKeeper namespace"},
    },
    "additionalProperties": False,
}

# Neo4j Advanced Configuration Schema
NEO4J_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "max_connection_pool_size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "description": "Maximum connection pool size",
        },
        "max_connection_lifetime": {
            "type": "integer",
            "minimum": 1,
            "maximum": 86400,
            "description": "Maximum connection lifetime in seconds",
        },
        "connection_acquisition_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 600,
            "description": "Connection acquisition timeout in seconds",
        },
        "connection_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "encrypted": {"type": "boolean", "description": "Enable encrypted connection"},
        "trust": {
            "type": "string",
            "enum": ["TRUST_ALL_CERTIFICATES", "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"],
            "description": "Certificate trust strategy",
        },
        "max_retry_time": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Maximum retry time in seconds",
        },
    },
    "additionalProperties": False,
}

# Kafka Advanced Configuration Schema
KAFKA_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "sasl_mechanism": {
            "type": "string",
            "enum": ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512", "GSSAPI"],
            "description": "SASL authentication mechanism",
        },
        "security_protocol": {
            "type": "string",
            "enum": ["PLAINTEXT", "SASL_PLAINTEXT", "SSL", "SASL_SSL"],
            "description": "Security protocol",
        },
        "sasl_username": {"type": "string", "description": "SASL username"},
        "sasl_password": {"type": "string", "description": "SASL password"},
        "compression_type": {
            "type": "string",
            "enum": ["none", "gzip", "snappy", "lz4", "zstd"],
            "description": "Compression type",
        },
        "batch_size": {"type": "integer", "minimum": 1, "maximum": 10485760, "description": "Batch size in bytes"},
        "linger_ms": {"type": "integer", "minimum": 0, "maximum": 60000, "description": "Linger time in milliseconds"},
        "acks": {"type": "string", "enum": ["0", "1", "all"], "description": "Acknowledgment level"},
        "max_in_flight_requests": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Maximum in-flight requests per connection",
        },
        "request_timeout_ms": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 300000,
            "description": "Request timeout in milliseconds",
        },
        "session_timeout_ms": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 300000,
            "description": "Session timeout in milliseconds",
        },
        "heartbeat_interval_ms": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 60000,
            "description": "Heartbeat interval in milliseconds",
        },
        "enable_auto_commit": {"type": "boolean", "description": "Enable auto commit of offsets"},
        "auto_offset_reset": {
            "type": "string",
            "enum": ["earliest", "latest", "none"],
            "description": "Auto offset reset strategy",
        },
    },
    "additionalProperties": False,
}

# Flink Advanced Configuration Schema
FLINK_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "rest_port": {"type": "integer", "minimum": 1, "maximum": 65535, "description": "REST API port"},
        "connection_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "request_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 600,
            "description": "Request timeout in seconds",
        },
        "ssl_enabled": {"type": "boolean", "description": "Enable SSL"},
        "ssl_verify_cert": {"type": "boolean", "description": "Verify SSL certificate"},
    },
    "additionalProperties": False,
}

# MongoDB Advanced Configuration Schema
MONGODB_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "serverSelectionTimeoutMS": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 300000,
            "description": "Server selection timeout in milliseconds",
        },
        "connectTimeoutMS": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 300000,
            "description": "Connection timeout in milliseconds",
        },
        "maxPoolSize": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "description": "Maximum connection pool size",
        },
        "tls": {"type": "boolean", "description": "Enable TLS/SSL connection"},
        "authSource": {"type": "string", "maxLength": 64, "description": "Authentication database name"},
    },
    "additionalProperties": False,
}

# ClickHouse Advanced Configuration Schema
CLICKHOUSE_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "connect_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "send_receive_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3600,
            "description": "Send/receive timeout in seconds",
        },
        "compress": {"type": "boolean", "description": "Enable compression"},
        "secure": {"type": "boolean", "description": "Use HTTPS protocol"},
        "verify": {"type": "boolean", "description": "Verify SSL certificate"},
    },
    "additionalProperties": False,
}

# Doris Advanced Configuration Schema
DORIS_ADVANCED_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "connect_timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Connection timeout in seconds",
        },
        "read_timeout": {"type": "integer", "minimum": 1, "maximum": 3600, "description": "Read timeout in seconds"},
        "write_timeout": {"type": "integer", "minimum": 1, "maximum": 3600, "description": "Write timeout in seconds"},
        "charset": {"type": "string", "enum": ["utf8", "utf8mb4"], "description": "Character set"},
        "ssl_enabled": {"type": "boolean", "description": "Enable SSL connection"},
    },
    "additionalProperties": False,
}

# Map datasource type to schema
DATASOURCE_SCHEMA_MAP = {
    "mysql": MYSQL_ADVANCED_CONFIG_SCHEMA,
    "postgresql": POSTGRESQL_ADVANCED_CONFIG_SCHEMA,
    "hive": HIVE_ADVANCED_CONFIG_SCHEMA,
    "neo4j": NEO4J_ADVANCED_CONFIG_SCHEMA,
    "kafka": KAFKA_ADVANCED_CONFIG_SCHEMA,
    "flink": FLINK_ADVANCED_CONFIG_SCHEMA,
    "mongodb": MONGODB_ADVANCED_CONFIG_SCHEMA,
    "clickhouse": CLICKHOUSE_ADVANCED_CONFIG_SCHEMA,
    "doris": DORIS_ADVANCED_CONFIG_SCHEMA,
}


def get_schema_for_type(datasource_type: str) -> dict | None:
    """Get JSON schema for a given datasource type."""
    return DATASOURCE_SCHEMA_MAP.get(datasource_type.lower())


def validate_advanced_config(datasource_type: str, config: dict) -> tuple[bool, list[str]]:
    """Validate advanced configuration against schema.

    Args:
        datasource_type: Type of datasource (mysql, postgresql, etc.)
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        from jsonschema import Draft7Validator, ValidationError

        schema = get_schema_for_type(datasource_type)
        if not schema:
            return False, [f"Unknown datasource type: {datasource_type}"]

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(config))

        if errors:
            error_messages = [f"{error.json_path}: {error.message}" for error in errors]
            return False, error_messages

        return True, []
    except ImportError:
        # If jsonschema is not installed, skip validation
        return True, []
    except Exception as e:
        return False, [f"Validation error: {e!s}"]
