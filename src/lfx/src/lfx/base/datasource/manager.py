"""Data source management module."""

import json
import os
from datetime import datetime
from urllib.parse import quote_plus

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from lfx.log.logger import logger


class DataSourceManager:
    """Manage data sources for ETL operations."""

    def __init__(self):
        """Initialize data source manager."""
        self.encryption_key = os.getenv("DATASOURCE_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a key for development (in production, use environment variable)
            self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

        # Cache for data sources
        self._cache = {}
        self._cache_expiry = 300  # 5 minutes
        self._last_cache_time = None

    async def get_datasources(self) -> dict[str, list[dict]]:
        """Get all available data sources.

        Returns:
            Dictionary with 'enterprise' and 'custom' data sources
        """
        # Check cache
        if self._use_cache():
            logger.debug(f"[DataSourceManager] Using cached datasources (cached at {self._last_cache_time})")
            logger.debug(
                f"[DataSourceManager] Cache contains: enterprise={len(self._cache.get('enterprise', []))}, custom={len(self._cache.get('custom', []))}"
            )
            return self._cache

        logger.info("[DataSourceManager] Fetching fresh datasources from storage")
        enterprise_sources = await self.fetch_enterprise_datasources()
        logger.info(f"[DataSourceManager] Fetched {len(enterprise_sources)} enterprise datasources")

        custom_sources = await self.get_custom_datasources()
        logger.info(f"[DataSourceManager] Fetched {len(custom_sources)} custom datasources")

        result = {"enterprise": enterprise_sources, "custom": custom_sources}

        # Update cache
        self._cache = result
        self._last_cache_time = datetime.now()
        logger.debug(f"[DataSourceManager] Datasources cached at {self._last_cache_time}")
        logger.debug(
            f"[DataSourceManager] Cache now contains: enterprise={len(enterprise_sources)}, custom={len(custom_sources)}"
        )

        return result

    async def fetch_enterprise_datasources(self) -> list[dict]:
        """Fetch enterprise data sources from Nacos Feign.

        Returns:
            List of enterprise data sources
        """
        try:
            nacos_url = os.getenv("NACOS_FEIGN_URL", "http://localhost:8080")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{nacos_url}/feign/client/data-construction/datasource-manage/getDatasourceList"
                )

                if response.status_code == 200:
                    sources = response.json()
                    # Format for UI
                    return [
                        {
                            "id": f"enterprise_{source.get('id')}",
                            "name": source.get("name"),
                            "type": source.get("type", "mysql").lower(),
                            "source": "enterprise",
                            "connection_string": self._build_connection_string(source),
                            "metadata": {"created_at": source.get("createTime"), "status": "active"},
                        }
                        for source in sources
                    ]
        except Exception as e:
            logger.error(f"[DataSourceManager] Error fetching enterprise datasources: {e}")

        return []

    async def get_custom_datasources(self) -> list[dict]:
        """Get custom data sources from database.

        Returns:
            List of custom data sources
        """
        try:
            # Import here to avoid circular dependencies
            from langflow.services.database.models.datasource import DataSource
            from langflow.services.deps import session_scope
            from sqlmodel import select

            logger.info("[DataSourceManager] Fetching custom datasources from database directly")

            # Get database session using async context manager
            async with session_scope() as session:
                # Query all datasources
                statement = select(DataSource)
                result = await session.exec(statement)
                datasources = result.all()

                logger.info(f"[DataSourceManager] Found {len(datasources)} datasources in database")
                if datasources:
                    logger.debug(f"[DataSourceManager] Sample datasource IDs: {[str(ds.id) for ds in datasources[:3]]}")

                # Format for UI - don't add prefix, use raw UUID
                result_list = [
                    {
                        "id": str(ds.id),  # Use raw UUID without prefix
                        "name": ds.name,
                        "type": ds.type.lower(),
                        "source": "custom",
                        "host": ds.host,
                        "port": ds.port,
                        "database": ds.database,
                        "username": ds.username,
                        # Note: password is not included for security
                        "status": ds.status or "inactive",
                        "metadata": {
                            "created_at": ds.created_at.isoformat() if ds.created_at else None,
                            "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
                            "status": ds.status or "inactive",
                        },
                    }
                    for ds in datasources
                ]
                logger.debug(f"[DataSourceManager] Formatted {len(result_list)} custom datasources")
                return result_list

        except Exception as e:
            logger.error(f"[DataSourceManager] Error fetching custom datasources from database: {e}")
            import traceback

            logger.error(f"[DataSourceManager] Traceback: {traceback.format_exc()}")
            # Fallback to file-based storage if database is unavailable
            return await self._get_custom_datasources_from_file()

        logger.warning("[DataSourceManager] Returning empty list (no datasources found)")
        return []

    async def _get_custom_datasources_from_file(self) -> list[dict]:
        """Fallback method: Get custom data sources from local storage file.

        Returns:
            List of custom data sources
        """
        custom_sources_file = os.path.join(os.path.dirname(__file__), "custom_datasources.json")

        if os.path.exists(custom_sources_file):
            try:
                with open(custom_sources_file) as f:
                    sources = json.load(f)
                    # Decrypt passwords
                    for source in sources:
                        if "encrypted_password" in source:
                            source["password"] = self._decrypt(source["encrypted_password"])
                    return sources
            except Exception as e:
                logger.error(f"[DataSourceManager] Error loading custom datasources from file: {e}")

        return []

    async def create_custom_datasource(self, datasource: dict) -> dict:
        """Create a new custom data source.

        Args:
            datasource: Data source configuration

        Returns:
            Created data source with ID
        """
        # Generate ID
        datasource["id"] = f"custom_{datetime.now().timestamp()}"
        datasource["source"] = "custom"
        datasource["metadata"] = {"created_at": datetime.now().isoformat(), "status": "active"}

        # Encrypt password
        if "password" in datasource:
            datasource["encrypted_password"] = self._encrypt(datasource["password"])
            del datasource["password"]

        # Save to storage
        await self._save_custom_datasource(datasource)

        # Clear cache to force reload
        logger.debug(f"[DataSourceManager] Clearing cache after creating datasource {datasource['id']}")
        self._cache = {}
        self._last_cache_time = None

        return datasource

    async def test_connection(self, connection_info: dict) -> dict:
        """Test database connection.

        Args:
            connection_info: Connection parameters

        Returns:
            Test result with status
        """
        try:
            logger.debug(f"[DataSourceManager] Testing connection with params: {connection_info}")

            db_type = connection_info.get("type", "").lower()

            # Kafka requires special handling
            if db_type == "kafka":
                return await self._test_kafka_connection(connection_info)

            # Flink requires special handling
            if db_type == "flink":
                return await self._test_flink_connection(connection_info)

            # Neo4j requires special handling with native driver
            if db_type == "neo4j":
                return await self._test_neo4j_connection(connection_info)

            # MongoDB requires special handling with pymongo
            if db_type == "mongodb":
                return await self._test_mongodb_connection(connection_info)

            # ClickHouse requires special handling with clickhouse-connect
            if db_type == "clickhouse":
                return await self._test_clickhouse_connection(connection_info)

            # Doris uses pymysql directly (not SQLAlchemy)
            if db_type == "doris":
                return await self._test_doris_connection(connection_info)

            # For other databases (MySQL, PostgreSQL, Hive), use SQLAlchemy
            if connection_info.get("connection_string"):
                conn_str = connection_info["connection_string"]
            else:
                conn_str = self._build_connection_string(connection_info)

            logger.debug("[DataSourceManager] Connection string built successfully")

            engine = create_engine(conn_str, poolclass=NullPool)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return {"status": "success", "message": "Connection successful"}
        except Exception as e:
            logger.error(f"[DataSourceManager] Connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def get_tables(self, datasource_id: str) -> list[str]:
        """Get list of tables for a data source.

        Args:
            datasource_id: Data source ID

        Returns:
            List of table names (or collections for MongoDB, labels for Neo4j)
        """
        try:
            datasource = await self._get_datasource_by_id(datasource_id)
            if not datasource:
                return []

            # If datasource from database (custom), use API endpoint
            if datasource.get("source") == "custom" and datasource_id.startswith("custom_"):
                db_id = datasource_id.replace("custom_", "", 1)
                return await self._get_tables_from_api(db_id)

            # Get database type
            db_type = datasource.get("type", "").lower()

            # MongoDB requires special handling with pymongo
            if db_type == "mongodb":
                return await self._get_mongodb_collections(datasource)

            # Neo4j requires special handling with neo4j driver
            if db_type == "neo4j":
                return await self._get_neo4j_labels(datasource)

            # ClickHouse requires special handling
            if db_type == "clickhouse":
                return await self._get_clickhouse_tables(datasource)

            # Doris requires special handling
            if db_type == "doris":
                return await self._get_doris_tables(datasource)

            # For other databases (MySQL, PostgreSQL, Hive), use SQLAlchemy
            conn_str = datasource.get("connection_string")
            if not conn_str:
                conn_str = self._build_connection_string(datasource)

            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            return sorted(tables)
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting tables: {e}")
            return []

    async def _get_tables_from_api(self, datasource_id: str) -> list[str]:
        """Get tables using the datasource API endpoint."""
        try:
            import httpx

            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{api_url}/api/v1/datasources/{datasource_id}/tables")

                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting tables from API: {e}")

        return []

    async def get_columns(self, datasource_id: str, table_name: str) -> list[dict]:
        """Get list of columns for a table.

        Args:
            datasource_id: Data source ID
            table_name: Table name

        Returns:
            List of column information
        """
        try:
            datasource = await self._get_datasource_by_id(datasource_id)
            if not datasource:
                return []

            # If datasource from database (custom), use API endpoint
            if datasource.get("source") == "custom" and datasource_id.startswith("custom_"):
                db_id = datasource_id.replace("custom_", "", 1)
                return await self._get_columns_from_api(db_id, table_name)

            # Otherwise use direct connection (for enterprise datasources)
            conn_str = datasource.get("connection_string")
            if not conn_str:
                conn_str = self._build_connection_string(datasource)

            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)

            return [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                    "primary_key": col.get("primary_key", False),
                }
                for col in columns
            ]
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting columns: {e}")
            return []

    async def _get_columns_from_api(self, datasource_id: str, table_name: str) -> list[dict]:
        """Get columns using the datasource API endpoint."""
        try:
            import httpx

            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{api_url}/api/v1/datasources/{datasource_id}/tables/{table_name}/columns")

                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting columns from API: {e}")

        return []

    async def get_tables_from_connection(self, connection_info: dict) -> list[str]:
        """Get list of tables from a connection info dict.

        Args:
            connection_info: Connection parameters

        Returns:
            List of table names (or collections for MongoDB, labels for Neo4j)
        """
        try:
            # Get database type
            db_type = connection_info.get("type", "").lower()

            # MongoDB requires special handling with pymongo
            if db_type == "mongodb":
                return await self._get_mongodb_collections(connection_info)

            # Neo4j requires special handling with neo4j driver
            if db_type == "neo4j":
                return await self._get_neo4j_labels(connection_info)

            # ClickHouse requires special handling
            if db_type == "clickhouse":
                return await self._get_clickhouse_tables(connection_info)

            # Doris requires special handling
            if db_type == "doris":
                return await self._get_doris_tables(connection_info)

            # For other databases (MySQL, PostgreSQL, Hive), use SQLAlchemy
            conn_str = self._build_connection_string(connection_info)
            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            return sorted(tables)
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting tables: {e}")
            return []

    async def get_columns_from_connection(self, connection_info: dict, table_name: str) -> list[dict]:
        """Get list of columns from a connection info dict.

        Args:
            connection_info: Connection parameters
            table_name: Table name

        Returns:
            List of column information
        """
        try:
            conn_str = self._build_connection_string(connection_info)
            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)

            return [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                    "primary_key": col.get("primary_key", False),
                }
                for col in columns
            ]
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting columns: {e}")
            return []

    def _build_connection_string(self, datasource: dict) -> str:
        """Build connection string from datasource config with advanced_config support."""
        db_type = datasource.get("type") or "mysql"
        host = datasource.get("host") or "localhost"
        port = datasource.get("port") or 3306
        database = datasource.get("database") or ""
        username = datasource.get("username") or ""
        password = datasource.get("password") or ""
        advanced_config = datasource.get("advanced_config", {})

        # Parse advanced_config if it's a JSON string
        if isinstance(advanced_config, str):
            try:
                advanced_config = json.loads(advanced_config)
            except (json.JSONDecodeError, TypeError):
                advanced_config = {}

        # URL encode username and password to handle special characters
        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if db_type == "mysql":
            base_url = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
            # Add advanced config parameters
            params = []
            if advanced_config.get("connect_timeout"):
                params.append(f"connect_timeout={advanced_config['connect_timeout']}")
            if advanced_config.get("read_timeout"):
                params.append(f"read_timeout={advanced_config['read_timeout']}")
            if advanced_config.get("write_timeout"):
                params.append(f"write_timeout={advanced_config['write_timeout']}")
            if advanced_config.get("charset"):
                params.append(f"charset={advanced_config['charset']}")
            if advanced_config.get("ssl_ca"):
                params.append(f"ssl_ca={quote_plus(advanced_config['ssl_ca'])}")
            if advanced_config.get("ssl_cert"):
                params.append(f"ssl_cert={quote_plus(advanced_config['ssl_cert'])}")
            if advanced_config.get("ssl_key"):
                params.append(f"ssl_key={quote_plus(advanced_config['ssl_key'])}")
            if advanced_config.get("ssl_disabled"):
                params.append("ssl_disabled=true")
            return base_url + ("?" + "&".join(params) if params else "")

        if db_type == "postgresql":
            base_url = f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
            # Add advanced config parameters
            params = []
            if advanced_config.get("connect_timeout"):
                params.append(f"connect_timeout={advanced_config['connect_timeout']}")
            if advanced_config.get("statement_timeout"):
                params.append(f"options=-c%20statement_timeout%3D{advanced_config['statement_timeout']}")
            if advanced_config.get("sslmode"):
                params.append(f"sslmode={advanced_config['sslmode']}")
            if advanced_config.get("sslcert"):
                params.append(f"sslcert={quote_plus(advanced_config['sslcert'])}")
            if advanced_config.get("sslkey"):
                params.append(f"sslkey={quote_plus(advanced_config['sslkey'])}")
            if advanced_config.get("sslrootcert"):
                params.append(f"sslrootcert={quote_plus(advanced_config['sslrootcert'])}")
            if advanced_config.get("application_name"):
                params.append(f"application_name={quote_plus(advanced_config['application_name'])}")
            return base_url + ("?" + "&".join(params) if params else "")

        if db_type == "hive":
            # Hive connection string - use PyHive SQLAlchemy format
            # Default port for Hive is 10000, database is 'default'
            hive_port = port if port != 3306 else 10000
            hive_database = database or "default"

            # Build base Hive connection string for SQLAlchemy + PyHive
            # Format: hive://[user[:password]@]host:port/database[;param=value;...]
            if username and password:
                base_url = f"hive://{username_encoded}:{password_encoded}@{host}:{hive_port}/{hive_database}"
            elif username:
                base_url = f"hive://{username_encoded}@{host}:{hive_port}/{hive_database}"
            else:
                base_url = f"hive://{host}:{hive_port}/{hive_database}"

            # Add advanced config parameters
            params = []
            if advanced_config.get("auth_mechanism"):
                params.append(f"auth={advanced_config['auth_mechanism']}")
            if advanced_config.get("transport_mode"):
                params.append(f"transportMode={advanced_config['transport_mode']}")
            if advanced_config.get("http_path"):
                params.append(f"httpPath={advanced_config['http_path']}")
            if advanced_config.get("kerberos_principal"):
                params.append(f"kerberos_service_name={advanced_config['kerberos_principal']}")
            if advanced_config.get("sasl_qop"):
                params.append(f"sasl_qop={advanced_config['sasl_qop']}")

            return base_url + (";" + ";".join(params) if params else "")

        if db_type == "neo4j":
            # Neo4j connection string - use bolt protocol (native driver)
            # Default port for Neo4j is 7687
            neo4j_port = port if port != 3306 else 7687
            # Neo4j uses bolt:// protocol for native driver, not neo4j://
            # Note: Neo4j advanced config is handled in _test_neo4j_connection via driver config
            if username and password:
                return f"bolt://{username_encoded}:{password_encoded}@{host}:{neo4j_port}"
            return f"bolt://{host}:{neo4j_port}"

        if db_type == "kafka":
            # Kafka doesn't use a connection string like SQL databases
            # Return bootstrap servers for reference
            return f"kafka://{host}"

        if db_type == "flink":
            # Flink doesn't use a traditional connection string
            # Return REST API endpoint for reference
            rest_port = advanced_config.get("rest_port", 8081)
            ssl_enabled = advanced_config.get("ssl_enabled", False)
            protocol = "https" if ssl_enabled else "http"
            return f"{protocol}://{host}:{rest_port}"

        if db_type == "mongodb":
            # MongoDB connection string
            # Default port for MongoDB is 27017
            mongo_port = port if port != 3306 else 27017

            # Build base MongoDB connection string
            if username and password:
                base_url = f"mongodb://{username_encoded}:{password_encoded}@{host}:{mongo_port}/{database}"
            else:
                base_url = f"mongodb://{host}:{mongo_port}/{database}"

            # Add advanced config parameters
            params = []
            if advanced_config.get("serverSelectionTimeoutMS"):
                params.append(f"serverSelectionTimeoutMS={advanced_config['serverSelectionTimeoutMS']}")
            if advanced_config.get("connectTimeoutMS"):
                params.append(f"connectTimeoutMS={advanced_config['connectTimeoutMS']}")
            if advanced_config.get("maxPoolSize"):
                params.append(f"maxPoolSize={advanced_config['maxPoolSize']}")
            if advanced_config.get("tls"):
                params.append(f"tls={'true' if advanced_config['tls'] else 'false'}")
            if advanced_config.get("authSource"):
                params.append(f"authSource={advanced_config['authSource']}")

            return base_url + ("?" + "&".join(params) if params else "")

        if db_type == "clickhouse":
            # ClickHouse connection string using clickhouse-connect driver
            # Default port for ClickHouse HTTP interface is 8123
            ch_port = port if port != 3306 else 8123

            # Build base ClickHouse connection string for clickhouse-connect
            base_url = f"clickhouse+connect://{username_encoded}:{password_encoded}@{host}:{ch_port}/{database}"

            # Add advanced config parameters
            params = []
            if advanced_config.get("connect_timeout"):
                params.append(f"connect_timeout={advanced_config['connect_timeout']}")
            if advanced_config.get("send_receive_timeout"):
                params.append(f"send_receive_timeout={advanced_config['send_receive_timeout']}")
            if advanced_config.get("compress"):
                params.append(f"compress={'true' if advanced_config['compress'] else 'false'}")
            if advanced_config.get("secure"):
                params.append(f"secure={'true' if advanced_config['secure'] else 'false'}")
            if advanced_config.get("verify"):
                params.append(f"verify={'true' if advanced_config['verify'] else 'false'}")

            return base_url + ("?" + "&".join(params) if params else "")

        if db_type == "doris":
            # Apache Doris connection string using MySQL protocol (pymysql)
            # Default port for Doris is 9030
            doris_port = port if port != 3306 else 9030

            # Build base Doris connection string (uses MySQL protocol)
            base_url = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{doris_port}/{database}"

            # Add advanced config parameters
            params = []
            if advanced_config.get("connect_timeout"):
                params.append(f"connect_timeout={advanced_config['connect_timeout']}")
            if advanced_config.get("read_timeout"):
                params.append(f"read_timeout={advanced_config['read_timeout']}")
            if advanced_config.get("write_timeout"):
                params.append(f"write_timeout={advanced_config['write_timeout']}")
            if advanced_config.get("charset"):
                params.append(f"charset={advanced_config['charset']}")
            if advanced_config.get("ssl_enabled"):
                params.append("ssl=true")

            return base_url + ("?" + "&".join(params) if params else "")

        raise ValueError(f"Unsupported database type: {db_type}")

    def _encrypt(self, text: str) -> str:
        """Encrypt sensitive text."""
        return self.cipher.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt sensitive text."""
        return self.cipher.decrypt(encrypted_text.encode()).decode()

    def _use_cache(self) -> bool:
        """Check if cache is valid."""
        if not self._last_cache_time:
            return False

        elapsed = (datetime.now() - self._last_cache_time).total_seconds()
        return elapsed < self._cache_expiry

    async def _get_datasource_by_id(self, datasource_id: str) -> dict | None:
        """Get datasource by ID with password for connection."""
        all_sources = await self.get_datasources()

        # Search in enterprise sources
        for source in all_sources.get("enterprise", []):
            if source["id"] == datasource_id:
                return source

        # Search in custom sources
        for source in all_sources.get("custom", []):
            if source["id"] == datasource_id:
                # For custom sources from database, we need to fetch with password
                if source["source"] == "custom" and datasource_id.startswith("custom_"):
                    # Extract the actual database ID (remove 'custom_' prefix)
                    db_id = datasource_id.replace("custom_", "", 1)
                    return await self._get_custom_datasource_with_password(db_id)
                return source

        return None

    async def _get_custom_datasource_with_password(self, datasource_id: str) -> dict | None:
        """Fetch a custom datasource from database with connection string.

        Args:
            datasource_id: The actual database ID (without 'custom_' prefix)

        Returns:
            Datasource dict with connection_string included
        """
        try:
            import httpx

            # Get datasource info
            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get basic info
                response = await client.get(f"{api_url}/api/v1/datasources/{datasource_id}")

                if response.status_code == 200:
                    ds = response.json()

                    # Get connection string (includes password internally)
                    conn_response = await client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                    connection_string = None
                    if conn_response.status_code == 200:
                        connection_string = conn_response.json().get("connection_string")

                    return {
                        "id": f"custom_{ds.get('id')}",
                        "name": ds.get("name"),
                        "type": ds.get("type", "mysql").lower(),
                        "source": "custom",
                        "host": ds.get("host"),
                        "port": ds.get("port"),
                        "database": ds.get("database"),
                        "username": ds.get("username"),
                        "connection_string": connection_string,  # Include connection string
                        "status": ds.get("status", "inactive"),
                        "metadata": {
                            "created_at": ds.get("created_at"),
                            "updated_at": ds.get("updated_at"),
                            "status": ds.get("status", "inactive"),
                        },
                    }
        except Exception as e:
            logger.error(f"[DataSourceManager] Error fetching datasource {datasource_id}: {e}")

        return None

    async def _save_custom_datasource(self, datasource: dict):
        """Save custom datasource to storage."""
        custom_sources = await self.get_custom_datasources()
        custom_sources.append(datasource)

        # Save to file (in production, save to database)
        custom_sources_file = os.path.join(os.path.dirname(__file__), "custom_datasources.json")

        # Remove passwords before saving
        save_sources = []
        for source in custom_sources:
            save_source = source.copy()
            if "password" in save_source:
                del save_source["password"]
            save_sources.append(save_source)

        with open(custom_sources_file, "w") as f:
            json.dump(save_sources, f, indent=2)

    async def _update_custom_datasource(self, datasource_id: str, updates: dict):
        """Update an existing custom datasource."""
        custom_sources = await self.get_custom_datasources()

        # Find and update the datasource
        updated = False
        for i, source in enumerate(custom_sources):
            if source["id"] == datasource_id:
                # Update fields
                for key, value in updates.items():
                    if key == "password":
                        # Encrypt password
                        source["encrypted_password"] = self._encrypt(value)
                    elif key != "id":  # Don't allow ID updates
                        source[key] = value

                # Update metadata
                if "metadata" not in source:
                    source["metadata"] = {}
                source["metadata"]["updated_at"] = datetime.now().isoformat()

                custom_sources[i] = source
                updated = True
                break

        if not updated:
            raise ValueError(f"Datasource with ID {datasource_id} not found")

        # Save to file
        custom_sources_file = os.path.join(os.path.dirname(__file__), "custom_datasources.json")

        # Remove passwords before saving
        save_sources = []
        for source in custom_sources:
            save_source = source.copy()
            if "password" in save_source:
                del save_source["password"]
            save_sources.append(save_source)

        with open(custom_sources_file, "w") as f:
            json.dump(save_sources, f, indent=2)

        # Clear cache to force reload
        logger.debug(f"[DataSourceManager] Clearing cache after updating datasource {datasource_id}")
        self._cache = {}
        self._last_cache_time = None

        return custom_sources[i] if updated else None

    async def _delete_custom_datasource(self, datasource_id: str):
        """Delete a custom datasource."""
        custom_sources = await self.get_custom_datasources()

        # Filter out the datasource to delete
        filtered_sources = [ds for ds in custom_sources if ds["id"] != datasource_id]

        if len(filtered_sources) == len(custom_sources):
            raise ValueError(f"Datasource with ID {datasource_id} not found")

        # Save to file
        custom_sources_file = os.path.join(os.path.dirname(__file__), "custom_datasources.json")

        # Remove passwords before saving
        save_sources = []
        for source in filtered_sources:
            save_source = source.copy()
            if "password" in save_source:
                del save_source["password"]
            save_sources.append(save_source)

        with open(custom_sources_file, "w") as f:
            json.dump(save_sources, f, indent=2)

        # Clear cache to force reload
        logger.debug(f"[DataSourceManager] Clearing cache after deleting datasource {datasource_id}")
        self._cache = {}
        self._last_cache_time = None

    async def _test_kafka_connection(self, connection_info: dict) -> dict:
        """Test Kafka connection.

        Args:
            connection_info: Kafka connection parameters

        Returns:
            Test result with status
        """
        try:
            from confluent_kafka.admin import AdminClient

            # Get connection parameters
            bootstrap_servers = connection_info.get("host", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Build Kafka config
            kafka_config = {
                "bootstrap.servers": bootstrap_servers,
            }

            # Add advanced config parameters
            if advanced_config.get("security_protocol"):
                kafka_config["security.protocol"] = advanced_config["security_protocol"]
            if advanced_config.get("sasl_mechanism"):
                kafka_config["sasl.mechanism"] = advanced_config["sasl_mechanism"]
            if advanced_config.get("sasl_username"):
                kafka_config["sasl.username"] = advanced_config["sasl_username"]
            if advanced_config.get("sasl_password"):
                kafka_config["sasl.password"] = advanced_config["sasl_password"]

            # Create AdminClient and test connection
            admin_client = AdminClient(kafka_config)

            # Get cluster metadata (this will test connection)
            metadata = admin_client.list_topics(timeout=10)

            broker_count = len(metadata.brokers)
            topic_count = len(metadata.topics)

            return {
                "status": "success",
                "message": f"Connection successful. Found {broker_count} brokers and {topic_count} topics.",
                "metadata": {"brokers": broker_count, "topics": topic_count},
            }
        except ImportError:
            return {
                "status": "failed",
                "message": "confluent-kafka library not installed. Please install it with: pip install confluent-kafka",
            }
        except Exception as e:
            logger.error(f"[DataSourceManager] Kafka connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _test_flink_connection(self, connection_info: dict) -> dict:
        """Test Flink JobManager connection via REST API.

        Args:
            connection_info: Flink connection parameters

        Returns:
            Test result with status
        """
        try:
            # Get connection parameters
            jobmanager_address = connection_info.get("host", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Get REST port (default 8081)
            rest_port = advanced_config.get("rest_port", 8081)
            connection_timeout = advanced_config.get("connection_timeout", 30)
            ssl_enabled = advanced_config.get("ssl_enabled", False)
            ssl_verify_cert = advanced_config.get("ssl_verify_cert", True)

            # Parse multiple jobmanager addresses (e.g., "host1:8081,host2:8081")
            addresses = [addr.strip() for addr in jobmanager_address.split(",")]

            # Try to connect to each address
            protocol = "https" if ssl_enabled else "http"
            last_error = None

            for addr in addresses:
                # Parse address (might include port)
                if ":" in addr:
                    host, port = addr.rsplit(":", 1)
                    try:
                        port = int(port)
                    except ValueError:
                        host = addr
                        port = rest_port
                else:
                    host = addr
                    port = rest_port

                url = f"{protocol}://{host}:{port}/v1/overview"

                try:
                    async with httpx.AsyncClient(
                        timeout=connection_timeout, verify=ssl_verify_cert if ssl_enabled else True
                    ) as client:
                        response = await client.get(url)

                        if response.status_code == 200:
                            data = response.json()
                            return {
                                "status": "success",
                                "message": f"Connection successful to {host}:{port}",
                                "metadata": {
                                    "version": data.get("flink-version"),
                                    "taskmanagers": data.get("taskmanagers"),
                                    "slots-total": data.get("slots-total"),
                                    "slots-available": data.get("slots-available"),
                                },
                            }
                except Exception as e:
                    last_error = str(e)
                    continue

            return {"status": "failed", "message": f"Failed to connect to any JobManager. Last error: {last_error}"}
        except Exception as e:
            logger.error(f"[DataSourceManager] Flink connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _test_neo4j_connection(self, connection_info: dict) -> dict:
        """Test Neo4j connection with advanced config support.

        Args:
            connection_info: Neo4j connection parameters

        Returns:
            Test result with status
        """
        try:
            from neo4j import GraphDatabase

            host = connection_info.get("host", "localhost")
            port = connection_info.get("port", 7687)
            username = connection_info.get("username", "")
            password = connection_info.get("password", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Build Neo4j bolt URI
            uri = f"bolt://{host}:{port}"

            # Build driver config from advanced_config
            driver_config = {}
            if advanced_config.get("max_connection_pool_size"):
                driver_config["max_connection_pool_size"] = advanced_config["max_connection_pool_size"]
            if advanced_config.get("max_connection_lifetime"):
                driver_config["max_connection_lifetime"] = advanced_config["max_connection_lifetime"]
            if advanced_config.get("connection_acquisition_timeout"):
                driver_config["connection_acquisition_timeout"] = advanced_config["connection_acquisition_timeout"]
            if advanced_config.get("connection_timeout"):
                driver_config["connection_timeout"] = advanced_config["connection_timeout"]
            if advanced_config.get("encrypted") is not None:
                driver_config["encrypted"] = advanced_config["encrypted"]
            if advanced_config.get("trust"):
                driver_config["trust"] = advanced_config["trust"]
            if advanced_config.get("max_retry_time"):
                driver_config["max_retry_time"] = advanced_config["max_retry_time"]

            # Create driver and test connection
            driver = GraphDatabase.driver(uri, auth=(username, password) if username else None, **driver_config)
            try:
                # Verify connectivity
                driver.verify_connectivity()
                return {"status": "success", "message": "Connection successful"}
            finally:
                driver.close()
        except ImportError:
            return {
                "status": "failed",
                "message": "neo4j library not installed. Please install it with: pip install neo4j",
            }
        except Exception as e:
            logger.error(f"[DataSourceManager] Neo4j connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _test_mongodb_connection(self, connection_info: dict) -> dict:
        """Test MongoDB connection with pymongo.

        Args:
            connection_info: MongoDB connection parameters

        Returns:
            Test result with status
        """
        try:
            from pymongo import MongoClient
            from pymongo.errors import ServerSelectionTimeoutError

            host = connection_info.get("host", "localhost")
            port = connection_info.get("port", 27017)
            database = connection_info.get("database", "admin")
            username = connection_info.get("username", "")
            password = connection_info.get("password", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Build MongoDB connection parameters
            mongo_params = {
                "host": host,
                "port": port,
                "serverSelectionTimeoutMS": advanced_config.get("serverSelectionTimeoutMS", 10000),
                "connectTimeoutMS": advanced_config.get("connectTimeoutMS", 20000),
            }

            if advanced_config.get("maxPoolSize"):
                mongo_params["maxPoolSize"] = advanced_config["maxPoolSize"]
            if advanced_config.get("tls"):
                mongo_params["tls"] = advanced_config["tls"]
            if advanced_config.get("authSource"):
                mongo_params["authSource"] = advanced_config["authSource"]

            # Add authentication if provided
            if username and password:
                mongo_params["username"] = username
                mongo_params["password"] = password

            # Create MongoDB client
            client = MongoClient(**mongo_params)

            try:
                # Test connection by getting server info
                info = client.server_info()
                db_list = client.list_database_names()

                return {
                    "status": "success",
                    "message": f"Connection successful. MongoDB version: {info.get('version')}",
                    "metadata": {
                        "version": info.get("version"),
                        "databases": len(db_list),
                    },
                }
            finally:
                client.close()

        except ServerSelectionTimeoutError:
            return {"status": "failed", "message": "Connection timeout. MongoDB server is not reachable."}
        except ImportError:
            return {
                "status": "failed",
                "message": "pymongo library not installed. Please install it with: pip install pymongo",
            }
        except Exception as e:
            logger.error(f"[DataSourceManager] MongoDB connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _test_clickhouse_connection(self, connection_info: dict) -> dict:
        """Test ClickHouse connection with clickhouse-connect.

        Args:
            connection_info: ClickHouse connection parameters

        Returns:
            Test result with status
        """
        try:
            import clickhouse_connect

            host = connection_info.get("host", "localhost")
            port = connection_info.get("port", 8123)
            database = connection_info.get("database", "default")
            username = connection_info.get("username", "default")
            password = connection_info.get("password", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Build clickhouse-connect client parameters
            client_params = {
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "database": database,
            }

            if advanced_config.get("connect_timeout"):
                client_params["connect_timeout"] = advanced_config["connect_timeout"]
            if advanced_config.get("send_receive_timeout"):
                client_params["send_receive_timeout"] = advanced_config["send_receive_timeout"]
            if advanced_config.get("compress"):
                client_params["compress"] = advanced_config["compress"]
            if advanced_config.get("secure"):
                client_params["secure"] = advanced_config["secure"]
            if advanced_config.get("verify"):
                client_params["verify"] = advanced_config["verify"]

            # Create ClickHouse client
            client = clickhouse_connect.get_client(**client_params)

            try:
                # Test connection with a simple query
                result = client.query("SELECT version()")
                version = result.result_rows[0][0] if result.result_rows else "Unknown"

                # Get database list
                databases_result = client.query("SHOW DATABASES")
                db_count = len(databases_result.result_rows)

                return {
                    "status": "success",
                    "message": f"Connection successful. ClickHouse version: {version}",
                    "metadata": {
                        "version": version,
                        "databases": db_count,
                    },
                }
            finally:
                client.close()

        except ImportError:
            return {
                "status": "failed",
                "message": "clickhouse-connect library not installed. Please install it with: pip install clickhouse-connect",
            }
        except Exception as e:
            logger.error(f"[DataSourceManager] ClickHouse connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _test_doris_connection(self, connection_info: dict) -> dict:
        """Test Apache Doris connection with pymysql.

        Args:
            connection_info: Doris connection parameters

        Returns:
            Test result with status
        """
        try:
            import pymysql

            host = connection_info.get("host", "localhost")
            port = connection_info.get("port", 9030)
            database = connection_info.get("database", "")
            username = connection_info.get("username", "root")
            password = connection_info.get("password", "")
            advanced_config = connection_info.get("advanced_config", {})

            if isinstance(advanced_config, str):
                advanced_config = json.loads(advanced_config)

            # Build pymysql connection parameters
            conn_params = {
                "host": host,
                "port": port,
                "user": username,
                "password": password,
                "database": database,
                "charset": advanced_config.get("charset", "utf8"),
            }

            if advanced_config.get("connect_timeout"):
                conn_params["connect_timeout"] = advanced_config["connect_timeout"]
            if advanced_config.get("read_timeout"):
                conn_params["read_timeout"] = advanced_config["read_timeout"]
            if advanced_config.get("write_timeout"):
                conn_params["write_timeout"] = advanced_config["write_timeout"]

            # SSL configuration
            if advanced_config.get("ssl_enabled"):
                conn_params["ssl"] = {"ssl": True}

            # Create Doris connection
            connection = pymysql.connect(**conn_params)

            try:
                with connection.cursor() as cursor:
                    # Test connection with version query
                    cursor.execute("SELECT VERSION()")
                    version_result = cursor.fetchone()
                    version = version_result[0] if version_result else "Unknown"

                    # Get database list
                    cursor.execute("SHOW DATABASES")
                    db_count = len(cursor.fetchall())

                    return {
                        "status": "success",
                        "message": f"Connection successful. Doris version: {version}",
                        "metadata": {
                            "version": version,
                            "databases": db_count,
                        },
                    }
            finally:
                connection.close()

        except ImportError:
            return {
                "status": "failed",
                "message": "pymysql library not installed. Please install it with: pip install pymysql",
            }
        except Exception as e:
            logger.error(f"[DataSourceManager] Doris connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def _get_mongodb_collections(self, datasource: dict) -> list[str]:
        """Get list of collections from MongoDB database.

        Args:
            datasource: MongoDB datasource configuration

        Returns:
            List of collection names
        """
        try:
            from pymongo import MongoClient
            from pymongo.errors import ServerSelectionTimeoutError

            host = datasource.get("host", "localhost")
            port = datasource.get("port", 27017)
            database = datasource.get("database", "")
            username = datasource.get("username", "")
            password = datasource.get("password", "")
            advanced_config = datasource.get("advanced_config", {})

            # Parse advanced_config if it's a JSON string
            if isinstance(advanced_config, str):
                try:
                    advanced_config = json.loads(advanced_config)
                except (json.JSONDecodeError, TypeError):
                    advanced_config = {}

            # Build MongoDB connection parameters
            mongo_params = {
                "host": host,
                "port": port,
                "serverSelectionTimeoutMS": advanced_config.get("serverSelectionTimeoutMS", 10000),
                "connectTimeoutMS": advanced_config.get("connectTimeoutMS", 20000),
            }

            if advanced_config.get("maxPoolSize"):
                mongo_params["maxPoolSize"] = advanced_config["maxPoolSize"]
            if advanced_config.get("tls"):
                mongo_params["tls"] = advanced_config["tls"]

            # Set authSource from advanced_config or use intelligent defaults
            if advanced_config.get("authSource"):
                mongo_params["authSource"] = advanced_config["authSource"]
                logger.debug(
                    f"[DataSourceManager] Using authSource from advanced_config: {advanced_config['authSource']}"
                )
            elif username and password:
                # If authentication is used but no authSource specified:
                # Default to 'admin' (most common setup in MongoDB)
                # Users can override via advanced_config if their user is in a different database
                mongo_params["authSource"] = "admin"
                logger.debug("[DataSourceManager] Using default authSource='admin' for MongoDB authentication")

            # Add authentication if provided
            if username and password:
                mongo_params["username"] = username
                mongo_params["password"] = password

            # Create MongoDB client
            client = MongoClient(**mongo_params)

            try:
                if not database:
                    logger.warning("[DataSourceManager] No database specified for MongoDB, returning empty list")
                    return []

                # Get collections from the specified database
                db = client[database]
                collections = db.list_collection_names()
                logger.info(
                    f"[DataSourceManager] Found {len(collections)} collections in MongoDB database '{database}'"
                )
                return sorted(collections)
            finally:
                client.close()

        except ServerSelectionTimeoutError:
            logger.error("[DataSourceManager] MongoDB connection timeout")
            return []
        except ImportError:
            logger.error("[DataSourceManager] pymongo library not installed")
            return []
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting MongoDB collections: {e}")
            return []

    async def _get_neo4j_labels(self, datasource: dict) -> list[str]:
        """Get list of node labels from Neo4j database.

        Args:
            datasource: Neo4j datasource configuration

        Returns:
            List of node labels
        """
        try:
            from neo4j import GraphDatabase

            host = datasource.get("host", "localhost")
            port = datasource.get("port", 7687)
            username = datasource.get("username", "")
            password = datasource.get("password", "")

            uri = f"bolt://{host}:{port}"
            driver = GraphDatabase.driver(uri, auth=(username, password))

            try:
                with driver.session() as session:
                    result = session.run("CALL db.labels()")
                    labels = [record["label"] for record in result]
                    logger.info(f"[DataSourceManager] Found {len(labels)} labels in Neo4j database")
                    return sorted(labels)
            finally:
                driver.close()

        except ImportError:
            logger.error("[DataSourceManager] neo4j library not installed")
            return []
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting Neo4j labels: {e}")
            return []

    async def _get_clickhouse_tables(self, datasource: dict) -> list[str]:
        """Get list of tables from ClickHouse database.

        Args:
            datasource: ClickHouse datasource configuration

        Returns:
            List of table names
        """
        try:
            import clickhouse_connect

            host = datasource.get("host", "localhost")
            port = datasource.get("port", 8123)
            database = datasource.get("database", "default")
            username = datasource.get("username", "default")
            password = datasource.get("password", "")
            advanced_config = datasource.get("advanced_config", {})

            # Parse advanced_config if it's a JSON string
            if isinstance(advanced_config, str):
                try:
                    advanced_config = json.loads(advanced_config)
                except (json.JSONDecodeError, TypeError):
                    advanced_config = {}

            # Build clickhouse-connect client parameters
            client_params = {
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "database": database,
            }

            # Add advanced config parameters
            if advanced_config.get("connect_timeout"):
                client_params["connect_timeout"] = advanced_config["connect_timeout"]
            if advanced_config.get("send_receive_timeout"):
                client_params["send_receive_timeout"] = advanced_config["send_receive_timeout"]
            if advanced_config.get("compress"):
                client_params["compress"] = advanced_config["compress"]
            if advanced_config.get("secure"):
                client_params["secure"] = advanced_config["secure"]
            if advanced_config.get("verify"):
                client_params["verify"] = advanced_config["verify"]

            # Create ClickHouse client
            client = clickhouse_connect.get_client(**client_params)

            try:
                # Get tables from current database
                result = client.query("SHOW TABLES")
                tables = [row[0] for row in result.result_rows]
                logger.info(f"[DataSourceManager] Found {len(tables)} tables in ClickHouse database '{database}'")
                return sorted(tables)
            finally:
                client.close()

        except ImportError:
            logger.error("[DataSourceManager] clickhouse-connect library not installed")
            return []
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting ClickHouse tables: {e}")
            return []

    async def _get_doris_tables(self, datasource: dict) -> list[str]:
        """Get list of tables from Doris database.

        Args:
            datasource: Doris datasource configuration

        Returns:
            List of table names
        """
        try:
            import pymysql

            host = datasource.get("host", "localhost")
            port = datasource.get("port", 9030)
            database = datasource.get("database", "")
            username = datasource.get("username", "root")
            password = datasource.get("password", "")
            advanced_config = datasource.get("advanced_config", {})

            # Parse advanced_config if it's a JSON string
            if isinstance(advanced_config, str):
                try:
                    advanced_config = json.loads(advanced_config)
                except (json.JSONDecodeError, TypeError):
                    advanced_config = {}

            # Build pymysql connection parameters
            conn_params = {
                "host": host,
                "port": port,
                "user": username,
                "password": password,
                "database": database,
                "charset": advanced_config.get("charset", "utf8"),
            }

            # Add advanced config parameters
            if advanced_config.get("connect_timeout"):
                conn_params["connect_timeout"] = advanced_config["connect_timeout"]
            else:
                conn_params["connect_timeout"] = 10  # Default timeout

            if advanced_config.get("read_timeout"):
                conn_params["read_timeout"] = advanced_config["read_timeout"]
            if advanced_config.get("write_timeout"):
                conn_params["write_timeout"] = advanced_config["write_timeout"]

            # SSL configuration
            if advanced_config.get("ssl_enabled"):
                conn_params["ssl"] = {"ssl": True}

            # Create Doris connection
            connection = pymysql.connect(**conn_params)

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in cursor.fetchall()]
                    logger.info(f"[DataSourceManager] Found {len(tables)} tables in Doris database '{database}'")
                    return sorted(tables)
            finally:
                connection.close()

        except ImportError:
            logger.error("[DataSourceManager] pymysql library not installed")
            return []
        except Exception as e:
            logger.error(f"[DataSourceManager] Error getting Doris tables: {e}")
            return []
