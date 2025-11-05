"""Data source management module."""

import json
import os
from datetime import datetime
from urllib.parse import quote_plus

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool


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
            print(f"Using cached datasources (cached at {self._last_cache_time})")
            return self._cache

        print("Fetching fresh datasources from storage")
        enterprise_sources = await self.fetch_enterprise_datasources()
        custom_sources = await self.get_custom_datasources()

        result = {"enterprise": enterprise_sources, "custom": custom_sources}

        # Update cache
        self._cache = result
        self._last_cache_time = datetime.now()
        print(f"Datasources cached at {self._last_cache_time}, total custom: {len(custom_sources)}")

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
            print(f"Error fetching enterprise datasources: {e}")

        return []

    async def get_custom_datasources(self) -> list[dict]:
        """Get custom data sources from database.

        Returns:
            List of custom data sources
        """
        try:
            # Import here to avoid circular dependencies
            import httpx

            # Get datasources from the API
            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{api_url}/api/v1/datasources")

                if response.status_code == 200:
                    datasources = response.json()
                    # Format for UI - add custom prefix and source field
                    return [
                        {
                            "id": f"custom_{ds.get('id')}",
                            "name": ds.get("name"),
                            "type": ds.get("type", "mysql").lower(),
                            "source": "custom",
                            "host": ds.get("host"),
                            "port": ds.get("port"),
                            "database": ds.get("database"),
                            "username": ds.get("username"),
                            # Note: password is not returned from API for security
                            "status": ds.get("status", "inactive"),
                            "metadata": {
                                "created_at": ds.get("created_at"),
                                "updated_at": ds.get("updated_at"),
                                "status": ds.get("status", "inactive"),
                            },
                        }
                        for ds in datasources
                    ]
        except Exception as e:
            print(f"Error fetching custom datasources from database: {e}")
            # Fallback to file-based storage if database is unavailable
            return await self._get_custom_datasources_from_file()

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
                print(f"Error loading custom datasources from file: {e}")

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
        print(f"Clearing cache after creating datasource {datasource['id']}")
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
            print(f"Testing connection with params: {connection_info}")

            db_type = connection_info.get("type", "").lower()

            # Neo4j requires special handling with native driver
            if db_type == "neo4j":
                from neo4j import GraphDatabase

                host = connection_info.get("host", "localhost")
                port = connection_info.get("port", 7687)
                username = connection_info.get("username", "")
                password = connection_info.get("password", "")

                # Build Neo4j bolt URI
                uri = f"bolt://{host}:{port}"

                # Create driver and test connection
                driver = GraphDatabase.driver(uri, auth=(username, password) if username else None)
                try:
                    # Verify connectivity
                    driver.verify_connectivity()
                    return {"status": "success", "message": "Connection successful"}
                finally:
                    driver.close()

            # For other databases, use SQLAlchemy
            if connection_info.get("connection_string"):
                conn_str = connection_info["connection_string"]
            else:
                conn_str = self._build_connection_string(connection_info)

            print("Connection string built successfully")

            engine = create_engine(conn_str, poolclass=NullPool)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return {"status": "success", "message": "Connection successful"}
        except Exception as e:
            print(f"Connection test failed: {e!s}")
            return {"status": "failed", "message": str(e)}

    async def get_tables(self, datasource_id: str) -> list[str]:
        """Get list of tables for a data source.

        Args:
            datasource_id: Data source ID

        Returns:
            List of table names
        """
        try:
            datasource = await self._get_datasource_by_id(datasource_id)
            if not datasource:
                return []

            # If datasource from database (custom), use API endpoint
            if datasource.get("source") == "custom" and datasource_id.startswith("custom_"):
                db_id = datasource_id.replace("custom_", "", 1)
                return await self._get_tables_from_api(db_id)

            # Otherwise use direct connection (for enterprise datasources)
            conn_str = datasource.get("connection_string")
            if not conn_str:
                conn_str = self._build_connection_string(datasource)

            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            return sorted(tables)
        except Exception as e:
            print(f"Error getting tables: {e}")
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
            print(f"Error getting tables from API: {e}")

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
            print(f"Error getting columns: {e}")
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
            print(f"Error getting columns from API: {e}")

        return []

    async def get_tables_from_connection(self, connection_info: dict) -> list[str]:
        """Get list of tables from a connection info dict.

        Args:
            connection_info: Connection parameters

        Returns:
            List of table names
        """
        try:
            conn_str = self._build_connection_string(connection_info)
            engine = create_engine(conn_str, poolclass=NullPool)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            return sorted(tables)
        except Exception as e:
            print(f"Error getting tables: {e}")
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
            print(f"Error getting columns: {e}")
            return []

    def _build_connection_string(self, datasource: dict) -> str:
        """Build connection string from datasource config."""
        db_type = datasource.get("type") or "mysql"
        host = datasource.get("host") or "localhost"
        port = datasource.get("port") or 3306
        database = datasource.get("database") or ""
        username = datasource.get("username") or ""
        password = datasource.get("password") or ""

        # URL encode username and password to handle special characters
        username_encoded = quote_plus(username) if username else ""
        password_encoded = quote_plus(password) if password else ""

        if db_type == "mysql":
            return f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if db_type == "postgresql":
            return f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
        if db_type == "hive":
            # Hive connection string - use PyHive SQLAlchemy format
            # Default port for Hive is 10000, database is 'default'
            hive_port = port if port != 3306 else 10000
            hive_database = database or "default"

            # Build Hive connection string for SQLAlchemy + PyHive
            # Format: hive://[user[:password]@]host:port/database
            if username and password:
                # With authentication (LDAP mode)
                return f"hive://{username_encoded}:{password_encoded}@{host}:{hive_port}/{hive_database}"
            if username:
                # Username only (no password)
                return f"hive://{username_encoded}@{host}:{hive_port}/{hive_database}"
            # No authentication (NOSASL mode)
            return f"hive://{host}:{hive_port}/{hive_database}"
        if db_type == "neo4j":
            # Neo4j connection string - use bolt protocol (native driver)
            # Default port for Neo4j is 7687
            neo4j_port = port if port != 3306 else 7687
            # Neo4j uses bolt:// protocol for native driver, not neo4j://
            if username and password:
                return f"bolt://{username_encoded}:{password_encoded}@{host}:{neo4j_port}"
            return f"bolt://{host}:{neo4j_port}"

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
            print(f"Error fetching datasource {datasource_id}: {e}")

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
        print(f"Clearing cache after updating datasource {datasource_id}")
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
        print(f"Clearing cache after deleting datasource {datasource_id}")
        self._cache = {}
        self._last_cache_time = None
